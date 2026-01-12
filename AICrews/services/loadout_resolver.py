"""
LoadoutResolver - Resolves skill_keys to CrewAI tools and MCP configs.

This is the bridge between:
- Frontend: stores skill_keys like ["cap:equity_quote", "cap:web_search"]
- Runtime: needs {"tools": [BaseTool...], "mcps": [MCPConfig...]}

CRITICAL DISTINCTION:
- Builtin tools: Instantiated via ToolsFactory → returned as BaseTool instances
- MCP tools: NOT instantiated → returned as configs for Agent(mcps=[...])

Architecture:
- Resolves skill_keys → capabilities via SkillCatalog
- Resolves capabilities → providers via ProviderCapabilityMapping
- For builtin providers: Creates tools via ToolsFactory
- For MCP providers: Returns configs for CrewAI MCP integration
"""
from AICrews.observability.logging import get_logger
from typing import Any, Dict, List, Optional, Tuple, Protocol, runtime_checkable, TypedDict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
from AICrews.database.models.skill import SkillCatalog, SkillKind
from AICrews.database.models.mcp import MCPServer
from AICrews.tools.factory.tools_factory import ToolsFactory, ToolSpec

logger = get_logger(__name__)


@runtime_checkable
class ToolProtocol(Protocol):
    """Protocol for CrewAI tools."""
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool."""
        ...


class MCPConfig(TypedDict, total=False):
    """Type definition for MCP server configuration."""
    server_key: str
    url: str
    transport: str
    tool_filter: Optional[List[str]]


@dataclass
class ResolvedLoadout:
    """Result of resolving skill_keys to tools and MCP configs."""
    tools: List[ToolProtocol] = field(default_factory=list)  # BaseTool instances
    mcps: List[MCPConfig] = field(default_factory=list)  # MCP server configs for Agent(mcps=[...])
    resolved_capabilities: Dict[str, str] = field(default_factory=dict)  # cap_id -> provider_key
    failed_capabilities: List[str] = field(default_factory=list)


class LoadoutResolver:
    """
    Resolves skill_keys to executable CrewAI tools and MCP configs.

    Skill key formats:
    - cap:{capability_id}     → Resolve via best available provider
    - preset:{preset_key}     → Resolve preset's required capabilities
    - strategy:{strategy_id}  → User-defined strategy (future)
    - workflow:{workflow_id}  → Multi-step workflow (future)

    Returns:
    - tools: List of BaseTool instances (for builtin tools)
    - mcps: List of MCP server configs (for Agent(mcps=[...]))
    """

    def __init__(self, session: Session, user_id: Optional[int] = None):
        """
        Initialize the resolver.

        Args:
            session: SQLAlchemy session for database queries
            user_id: Optional user ID for checking user-configured API credentials
        """
        self.session = session
        self.user_id = user_id
        self.factory = ToolsFactory()
        self._credential_service = None

    @property
    def credential_service(self):
        """Lazy-load credential service only when needed."""
        if self._credential_service is None and self.user_id is not None:
            from AICrews.services.provider_credential_service import ProviderCredentialService
            self._credential_service = ProviderCredentialService(self.session)
        return self._credential_service

    def resolve(self, skill_keys: List[str]) -> ResolvedLoadout:
        """
        Resolve skill_keys to tools and MCP configs.

        Args:
            skill_keys: List of skill keys (e.g., ["cap:equity_quote", "cap:web_search"])

        Returns:
            ResolvedLoadout with tools and mcps separated
        """
        # Early return for empty skill_keys
        if not skill_keys:
            logger.debug("No skill_keys provided to resolve")
            return ResolvedLoadout()

        result = ResolvedLoadout()
        capabilities_to_resolve = []

        # Step 1: Parse skill_keys and collect capabilities
        for skill_key in skill_keys:
            if skill_key.startswith("cap:"):
                capability_id = skill_key[4:]  # Remove "cap:" prefix
                capabilities_to_resolve.append(capability_id)

            elif skill_key.startswith("preset:"):
                preset_key = skill_key[7:]  # Remove "preset:" prefix
                preset_caps = self._get_preset_capabilities(preset_key)
                capabilities_to_resolve.extend(preset_caps)

            elif skill_key.startswith("skillset:"):
                skillset_key = skill_key[9:]  # Remove "skillset:" prefix
                skillset_caps = self._get_skillset_capabilities(skillset_key)
                capabilities_to_resolve.extend(skillset_caps)

            elif skill_key.startswith("strategy:"):
                logger.warning(f"Strategy resolution not yet implemented: {skill_key}")

            elif skill_key.startswith("workflow:"):
                logger.warning(f"Workflow resolution not yet implemented: {skill_key}")

            else:
                logger.warning(f"Unknown skill_key format: {skill_key}")

        # Step 2: Resolve each capability to provider
        # Track MCP servers and their tools to prevent duplicates
        server_tools: Dict[str, Dict[str, Any]] = {}

        for cap_id in capabilities_to_resolve:
            resolved = self._resolve_capability(cap_id)
            if resolved:
                provider, mapping = resolved

                if provider.provider_type == "mcp":
                    # MCP: collect config for Agent(mcps=[...])
                    # Aggregate tool filters for the same server to prevent duplicates
                    mcp_config = self._build_mcp_config(provider, mapping)
                    if mcp_config:
                        server_key = mcp_config["server_key"]

                        # Initialize server entry if not seen before
                        if server_key not in server_tools:
                            server_tools[server_key] = {
                                "config": {
                                    "server_key": server_key,
                                    "url": mcp_config["url"],
                                    "transport": mcp_config["transport"],
                                },
                                "tools": set()
                            }

                        # Add tool to the set if specified
                        if mcp_config.get("tool_filter"):
                            server_tools[server_key]["tools"].update(mcp_config["tool_filter"])

                        result.resolved_capabilities[cap_id] = provider.provider_key
                    else:
                        result.failed_capabilities.append(cap_id)

                elif provider.provider_type.startswith("builtin"):
                    # Check credentials before creating tool
                    if not self._check_provider_credentials(provider):
                        logger.warning(
                            f"Skipping capability '{cap_id}' - provider '{provider.provider_key}' "
                            f"requires credentials that are not configured"
                        )
                        result.failed_capabilities.append(cap_id)
                        continue

                    # Builtin: instantiate tool
                    spec = ToolSpec(
                        provider_key=provider.provider_key,
                        provider_type=provider.provider_type,
                        raw_tool_name=mapping.raw_tool_name,
                        capability_id=cap_id,
                        connection_schema=provider.connection_schema or {},
                    )
                    tool = self.factory.create_tool(spec)
                    if tool:
                        result.tools.append(tool)
                        result.resolved_capabilities[cap_id] = provider.provider_key
                    else:
                        result.failed_capabilities.append(cap_id)

                else:
                    logger.warning(f"Unknown provider type: {provider.provider_type} for capability: {cap_id}")
                    result.failed_capabilities.append(cap_id)
            else:
                result.failed_capabilities.append(cap_id)

        # Step 3: Build final MCP configs with aggregated tool filters
        for server_key, data in server_tools.items():
            config: MCPConfig = {
                "server_key": data["config"]["server_key"],
                "url": data["config"]["url"],
                "transport": data["config"]["transport"],
                "tool_filter": list(data["tools"]) if data["tools"] else None,
            }
            result.mcps.append(config)

        return result

    def _resolve_capability(
        self, capability_id: str
    ) -> Optional[Tuple[CapabilityProvider, ProviderCapabilityMapping]]:
        """
        Find the best provider for a capability.

        Provider selection is based on:
        1. Provider must be enabled and healthy
        2. Sorted by mapping-level priority (ProviderCapabilityMapping.priority)
           - This allows fine-grained control per capability
           - Higher priority = tried first (default: 50, range: 0-100)

        Args:
            capability_id: Capability identifier (e.g., "equity_quote")

        Returns:
            Tuple of (provider, mapping) or None if no healthy provider found
        """
        # Find all healthy providers that offer this capability
        # Sort by mapping-level priority (not provider-level) for per-capability control
        mappings = self.session.execute(
            select(ProviderCapabilityMapping, CapabilityProvider)
            .join(CapabilityProvider, ProviderCapabilityMapping.provider_id == CapabilityProvider.id)
            .where(
                ProviderCapabilityMapping.capability_id == capability_id,
                CapabilityProvider.enabled == True,
                CapabilityProvider.healthy == True,
            )
            .order_by(ProviderCapabilityMapping.priority.desc())  # Mapping-level priority
        ).all()

        if not mappings:
            logger.warning(f"No healthy provider for capability: {capability_id}")
            return None

        # Return highest priority provider
        mapping, provider = mappings[0]
        return (provider, mapping)

    def _check_provider_credentials(self, provider: CapabilityProvider) -> bool:
        """
        Check if provider credentials are available (env var OR user-configured).

        If user-configured credentials are available but env vars are not set,
        this method will INJECT the user's API key into the environment variable
        so that tools can read it via os.getenv().

        Args:
            provider: CapabilityProvider to check

        Returns:
            True if credentials are available, False otherwise
        """
        import os

        connection_schema = provider.connection_schema or {}
        required_env = connection_schema.get("requires_env", [])

        # No credentials required
        if not required_env:
            return True

        # Check 1: Environment variables already set
        if all(os.getenv(var) for var in required_env):
            return True

        # Check 2: User-configured credentials (if user_id is available)
        if self.user_id is not None and self.credential_service:
            api_key = self.credential_service.get_user_api_key(
                self.user_id, provider.provider_key
            )
            if api_key:
                # IMPORTANT: Inject user's API key into environment variable
                # so that tools can read it via os.getenv()
                for env_var in required_env:
                    os.environ[env_var] = api_key
                    logger.info(
                        f"Injected user API key for provider '{provider.provider_key}' "
                        f"into env var '{env_var}'"
                    )
                return True

        # Neither env var nor user credential available
        logger.warning(
            f"Provider '{provider.provider_key}' requires credentials "
            f"(env: {required_env}) but none configured. "
            f"User can configure API key in frontend settings."
        )
        return False

    def _get_preset_capabilities(self, preset_key: str) -> List[str]:
        """
        Get capabilities required by a preset.

        Args:
            preset_key: Preset key (without "preset:" prefix)

        Returns:
            List of capability IDs required by the preset
        """
        preset = self.session.execute(
            select(SkillCatalog).where(
                SkillCatalog.skill_key == f"preset:{preset_key}",
                SkillCatalog.kind == SkillKind.preset,
                SkillCatalog.is_active == True,
            )
        ).scalar_one_or_none()

        if not preset:
            logger.warning(f"Preset not found: {preset_key}")
            return []

        # Extract required_capabilities from invocation field
        invocation = preset.invocation or {}
        required_caps = invocation.get("required_capabilities", [])

        if not required_caps:
            logger.debug(f"Preset {preset_key} has no required_capabilities defined")

        return required_caps

    def _get_skillset_capabilities(self, skillset_key: str) -> List[str]:
        """
        Get capabilities required by a skillset.

        Args:
            skillset_key: Skillset key (without "skillset:" prefix)

        Returns:
            List of capability IDs required by the skillset
        """
        skillset = self.session.execute(
            select(SkillCatalog).where(
                SkillCatalog.skill_key == f"skillset:{skillset_key}",
                SkillCatalog.kind == SkillKind.skillset,
                SkillCatalog.is_active == True,
            )
        ).scalar_one_or_none()

        if not skillset:
            logger.warning(f"Skillset not found: {skillset_key}")
            return []

        # Extract required_capabilities from invocation field
        invocation = skillset.invocation or {}
        required_caps = invocation.get("required_capabilities", [])

        if not required_caps:
            logger.debug(f"Skillset {skillset_key} has no required_capabilities defined")

        return required_caps

    def _build_mcp_config(
        self, provider: CapabilityProvider, mapping: ProviderCapabilityMapping
    ) -> Optional[Dict]:
        """
        Build MCP server config for Agent(mcps=[...]).

        Args:
            provider: The MCP provider
            mapping: The capability mapping for this provider

        Returns:
            MCP config dict or None if server not found
        """
        # Get MCP server details
        server_key = provider.provider_key.replace("mcp:", "")
        mcp_server = self.session.execute(
            select(MCPServer).where(MCPServer.server_key == server_key)
        ).scalar_one_or_none()

        if not mcp_server:
            logger.warning(f"MCP server not found: {server_key}")
            return None

        # Build config for CrewAI MCP integration
        config = {
            "server_key": server_key,
            "url": mcp_server.url,
            "transport": mcp_server.transport_type or "sse",
            "tool_filter": [mapping.raw_tool_name] if mapping.raw_tool_name else None,
        }

        return config

    def get_resolved_loadout(self, skill_keys: List[str]) -> Dict[str, Any]:
        """
        Convenience method returning a dict format.

        Args:
            skill_keys: List of skill keys to resolve

        Returns:
            Dict with keys: tools, mcps, resolved, failed
        """
        result = self.resolve(skill_keys)
        return {
            "tools": result.tools,
            "mcps": result.mcps,
            "resolved": result.resolved_capabilities,
            "failed": result.failed_capabilities,
        }
