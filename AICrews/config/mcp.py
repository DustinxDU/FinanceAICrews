"""
MCP Configuration Converter for CrewAI Native MCP Integration

This module converts existing MCP server configurations (YAML/DB) into CrewAI's
native MCPServerConfig objects (MCPServerHTTP, MCPServerSSE, MCPServerStdio).

This replaces the custom MCPManager/MCPService connection management with
CrewAI's built-in on-demand connection handling.

Philosophy: Let CrewAI handle MCP connections, we just provide configurations.
"""

import os
from AICrews.observability.logging import get_logger
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
import threading
import time

import yaml
from sqlalchemy import select
from crewai.mcp import (
    MCPServerHTTP,
    MCPServerSSE,
    MCPServerStdio,
    create_static_tool_filter,
)

logger = get_logger(__name__)


# Type alias for MCP server configs
MCPServerConfig = Union[MCPServerHTTP, MCPServerSSE, MCPServerStdio]


@dataclass
class ToolPolicyLoader:
    """Loads tool policies from YAML configuration with hot reload support."""

    config_path: Optional[Path] = None
    _policies: Dict[str, Any] = field(default_factory=dict)
    _loaded: bool = False
    _last_modified: Optional[float] = None
    _watch_thread: Optional[threading.Thread] = None
    _watching: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        if self.config_path is None:
            # Default path relative to project root
            project_root = Path(__file__).parent.parent.parent
            self.config_path = project_root / "config" / "tools" / "policies.yaml"

    def load(self) -> None:
        """Load tool policies from YAML file."""
        if self._loaded:
            return

        if not self.config_path.exists():
            # Policy file is optional now
            logger.debug(
                f"Tool policies config not found at {self.config_path}, using default (allow all)"
            )
            self._loaded = True
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._policies = yaml.safe_load(f) or {}
            self._loaded = True
            self._last_modified = self.config_path.stat().st_mtime
            logger.info(f"Loaded tool policies from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load tool policies: {e}")
            self._policies = {}
            self._loaded = True

    def start_watching(self, check_interval: float = 1.0) -> None:
        """Start watching the config file for changes."""
        if self._watching:
            return

        self._watching = True
        self._watch_thread = threading.Thread(
            target=self._watch_file_changes, args=(check_interval,), daemon=True
        )
        self._watch_thread.start()
        logger.info(f"Started watching {self.config_path} for changes")

    def stop_watching(self) -> None:
        """Stop watching the config file."""
        self._watching = False
        if self._watch_thread:
            self._watch_thread.join(timeout=1.0)
        logger.info("Stopped watching tool policies file")

    def _watch_file_changes(self, check_interval: float) -> None:
        """Background thread to watch for file changes."""
        while self._watching:
            try:
                if self.config_path.exists():
                    current_mtime = self.config_path.stat().st_mtime
                    if self._last_modified and current_mtime > self._last_modified:
                        logger.info("Tool policies file changed, reloading...")
                        self.reload()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error watching tool policies file: {e}")
                time.sleep(check_interval)

    def get_tool_allowlist(
        self, agent_name: str, server_name: str
    ) -> Optional[List[str]]:
        """Get tool allowlist for a specific agent and server."""
        with self._lock:
            self.load()

            agents = self._policies.get("agents", {})
            agent_config = agents.get(agent_name, {})

            return agent_config.get(server_name)

    def get_agent_categories(self, agent_name: str) -> Set[str]:
        """Get allowed categories for an agent."""
        with self._lock:
            self.load()

            global_config = self._policies.get("global", {})
            agent_filters = global_config.get("agent_tool_filters", {})

            return set(agent_filters.get(agent_name, []))

    def reload(self) -> None:
        """Force reload the configuration."""
        with self._lock:
            self._loaded = False
            self._policies.clear()
            self.load()
            logger.info("Tool policies reloaded")


# Global tool policy loader instance
_tool_policy_loader: Optional[ToolPolicyLoader] = None


def get_tool_policy_loader() -> ToolPolicyLoader:
    """Get or create the global tool policy loader."""
    global _tool_policy_loader
    if _tool_policy_loader is None:
        _tool_policy_loader = ToolPolicyLoader()
    return _tool_policy_loader


@dataclass
class AgentToolFilter:
    """Tool filter configuration for an agent type."""

    agent_type: str
    allowed_tools: Set[str] = field(default_factory=set)
    allowed_categories: Set[str] = field(default_factory=set)
    blocked_tools: Set[str] = field(default_factory=set)


@dataclass
class MCPServerDefinition:
    """Parsed MCP server definition from config."""

    name: str
    enabled: bool
    transport: str  # 'http', 'sse', 'stdio'
    url: Optional[str] = None
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    connection_timeout: int = 30
    tool_execution_timeout: int = 120  # Tool execution timeout in seconds
    discovery_timeout: int = 60  # Tool discovery timeout in seconds
    cache_tools_list: bool = True
    tool_filter: Optional[List[str]] = None  # Allowlist of tool names
    tool_mapping: Dict[str, str] = field(
        default_factory=dict
    )  # MCP name -> display name
    ssl_verify: bool = True


class MCPConfigLoader:
    """
    Loads MCP configurations from YAML and converts to CrewAI MCPServerConfig.

    This is the single source of truth for MCP server configurations at runtime.
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default path relative to project root
            project_root = Path(__file__).parent.parent.parent
            self.config_path = project_root / "config" / "mcp_servers.yaml"

        self._raw_config: Dict[str, Any] = {}
        self._servers: Dict[str, MCPServerDefinition] = {}
        self._agent_filters: Dict[str, AgentToolFilter] = {}
        self._loaded = False

    def load(self) -> None:
        """Load and parse the configuration file."""
        if self._loaded:
            return

        # Load YAML if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._raw_config = yaml.safe_load(f) or {}
                self._parse_servers()
            except Exception as e:
                logger.error(f"Error loading MCP config from {self.config_path}: {e}")
        else:
            logger.info(
                f"MCP config not found at {self.config_path}, skipping YAML load"
            )

        self._discover_from_env()  # Discover from env vars
        self._parse_agent_filters()
        self._loaded = True

        logger.info(
            f"Loaded {len(self._servers)} MCP server configs ({len(self._raw_config)} from YAML, others from ENV)"
        )

    def _discover_from_env(self) -> None:
        """Discover MCP servers from environment variables.

        Pattern: MCP_SERVER_{NAME}_URL (for SSE) or MCP_SERVER_{NAME}_CMD (for Stdio)
        """
        # Regex to match MCP_SERVER_{NAME}_{TYPE}
        pattern = re.compile(r"^MCP_SERVER_([A-Z0-9_]+)_(URL|CMD)$")

        discovered = {}  # name -> {url: ..., cmd: ...}

        for key, value in os.environ.items():
            match = pattern.match(key)
            if match:
                server_name = match.group(1).lower()
                config_type = match.group(2)

                if server_name not in discovered:
                    discovered[server_name] = {}

                if config_type == "URL":
                    discovered[server_name]["url"] = value
                elif config_type == "CMD":
                    discovered[server_name]["command"] = value

        # Create server definitions
        for name, config in discovered.items():
            if name in self._servers:
                continue  # YAML config takes precedence

            # Check for args env var: MCP_SERVER_{NAME}_ARGS
            args_str = os.environ.get(f"MCP_SERVER_{name.upper()}_ARGS", "")
            args = args_str.split() if args_str else []

            transport = "sse" if "url" in config else "stdio"
            if transport == "stdio" and "command" not in config:
                continue  # Invalid config

            server_def = MCPServerDefinition(
                name=name,
                enabled=True,
                transport=transport,
                url=config.get("url"),
                command=config.get("command"),
                args=args,
                env={},  # Inherit env?
                connection_timeout=30,
                tool_execution_timeout=120,
                discovery_timeout=60,
                cache_tools_list=True,
            )
            self._servers[name] = server_def
            logger.info(f"Discovered MCP server from env: {name} ({transport})")

    def _parse_servers(self) -> None:
        """Parse server definitions from raw config."""
        # Skip 'global' key which contains global settings
        for name, config in self._raw_config.items():
            if name == "global" or not isinstance(config, dict):
                continue

            enabled = config.get("enabled", False)
            transport = config.get("transport", "http_sse")

            # Normalize transport type
            if transport in ("http_sse", "http", "streamable_http"):
                transport = "http"
            elif transport == "sse":
                transport = "sse"
            elif transport in ("stdio", "process"):
                transport = "stdio"
            elif transport == "websocket":
                # WebSocket not directly supported by CrewAI, treat as SSE if URL available
                transport = "sse"

            # Extract tool mapping (MCP tool name -> display name)
            tool_mapping = config.get("tool_mapping", {})

            server_def = MCPServerDefinition(
                name=name,
                enabled=enabled,
                transport=transport,
                url=config.get("url"),
                command=config.get("command"),
                args=config.get("args", []),
                env=self._resolve_env_vars(config.get("env", {})),
                connection_timeout=config.get("connection_timeout", 30),
                tool_execution_timeout=config.get("tool_execution_timeout", 120),
                discovery_timeout=config.get("discovery_timeout", 60),
                cache_tools_list=config.get("caching", {}).get("enabled", True),
                tool_filter=list(tool_mapping.keys()) if tool_mapping else None,
                tool_mapping=tool_mapping,
                ssl_verify=config.get("ssl_verify", True),
            )

            self._servers[name] = server_def

    def _parse_agent_filters(self) -> None:
        """Parse agent tool filters from global config."""
        global_config = self._raw_config.get("global", {})
        agent_filters = global_config.get("agent_tool_filters", {})

        for agent_type, categories in agent_filters.items():
            self._agent_filters[agent_type] = AgentToolFilter(
                agent_type=agent_type,
                allowed_categories=set(categories) if categories else set(),
            )

    def _resolve_env_vars(self, env_dict: Dict[str, str]) -> Dict[str, str]:
        """Resolve environment variable references like ${VAR_NAME}."""
        resolved = {}
        for key, value in env_dict.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                var_name = value[2:-1]
                resolved[key] = os.environ.get(var_name, "")
            else:
                resolved[key] = str(value)
        return resolved

    def get_enabled_servers(self) -> List[str]:
        """Get list of enabled server names."""
        self.load()
        return [name for name, server in self._servers.items() if server.enabled]

    def get_all_servers(self) -> Dict[str, MCPServerDefinition]:
        """Get all server definitions."""
        self.load()
        return self._servers

    def get_server_definition(self, name: str) -> Optional[MCPServerDefinition]:
        """Get a specific server definition."""
        self.load()
        return self._servers.get(name)

    def get_agent_filter(self, agent_type: str) -> Optional[AgentToolFilter]:
        """Get tool filter for an agent type."""
        self.load()
        return self._agent_filters.get(agent_type)

    def get_server_url(self, service_name: str) -> Optional[str]:
        """获取服务器 URL"""
        server_def = self.get_server_definition(service_name)
        return server_def.url if server_def else None

    def get_server_timeout(self, service_name: str) -> int:
        """获取服务器超时配置"""
        server_def = self.get_server_definition(service_name)
        return getattr(server_def, "connection_timeout", 30)

    def get_server_ssl_verify(self, service_name: str) -> bool:
        """获取 SSL 验证配置 (v1.7.2 企业需求)"""
        server_def = self.get_server_definition(service_name)
        return getattr(server_def, "ssl_verify", True)


class MCPConfigConverter:
    """
    Converts MCP configurations to CrewAI native MCPServerConfig objects.

    This is the bridge between your configuration (YAML/DB) and CrewAI's MCP system.
    """

    def __init__(self, config_loader: Optional[MCPConfigLoader] = None):
        self.loader = config_loader or MCPConfigLoader()

    def get_mcps_for_agent(
        self,
        agent_name: str,
        server_names: Optional[List[str]] = None,
        tool_allowlist: Optional[List[str]] = None,
    ) -> List[MCPServerConfig]:
        """
        Get CrewAI MCP server configs for an agent.

        Args:
            agent_name: Name of the agent (used for filtering)
            server_names: Specific servers to include (None = all enabled)
            tool_allowlist: Explicit tool allowlist (overrides config-based filtering)

        Returns:
            List of CrewAI MCPServerConfig objects ready to pass to Agent(mcps=[...])
        """
        self.loader.load()

        mcps = []

        # Determine which servers to include
        if server_names:
            names_to_process = server_names
        else:
            names_to_process = self.loader.get_enabled_servers()

        for name in names_to_process:
            server_def = self.loader.get_server_definition(name)
            if not server_def or not server_def.enabled:
                continue

            try:
                mcp_config = self._create_mcp_config(
                    server_def,
                    tool_allowlist=tool_allowlist,
                )
                if mcp_config:
                    mcps.append(mcp_config)
                    logger.debug(
                        f"Created MCP config for {name} (transport={server_def.transport})"
                    )
            except Exception as e:
                logger.error(f"Failed to create MCP config for {name}: {e}")

        return mcps

    def _create_mcp_config(
        self,
        server_def: MCPServerDefinition,
        tool_allowlist: Optional[List[str]] = None,
    ) -> Optional[MCPServerConfig]:
        """Create a CrewAI MCPServerConfig from a server definition."""

        # Determine tool filter
        tool_filter = None
        allowed_tools = tool_allowlist or server_def.tool_filter
        if allowed_tools:
            tool_filter = create_static_tool_filter(allowed_tool_names=allowed_tools)

        if server_def.transport == "http":
            if not server_def.url:
                logger.warning(f"HTTP server {server_def.name} has no URL")
                return None

            return MCPServerHTTP(
                url=server_def.url,
                headers=server_def.headers or None,
                streamable=True,  # Use streamable HTTP
                tool_filter=tool_filter,
                cache_tools_list=server_def.cache_tools_list,
            )

        elif server_def.transport == "sse":
            if not server_def.url:
                logger.warning(f"SSE server {server_def.name} has no URL")
                return None

            return MCPServerSSE(
                url=server_def.url,
                headers=server_def.headers or None,
                tool_filter=tool_filter,
                cache_tools_list=server_def.cache_tools_list,
            )

        elif server_def.transport == "stdio":
            if not server_def.command:
                logger.warning(f"Stdio server {server_def.name} has no command")
                return None

            return MCPServerStdio(
                command=server_def.command,
                args=server_def.args,
                env=server_def.env or None,
                tool_filter=tool_filter,
                cache_tools_list=server_def.cache_tools_list,
            )

        else:
            logger.warning(f"Unknown transport type: {server_def.transport}")
            return None

    def create_mcp_for_server(
        self,
        server_name: str,
        tool_allowlist: Optional[List[str]] = None,
    ) -> Optional[MCPServerConfig]:
        """Create a single MCP config for a named server."""
        self.loader.load()
        server_def = self.loader.get_server_definition(server_name)
        if not server_def:
            return None
        return self._create_mcp_config(server_def, tool_allowlist)


def get_tool_allowlist_for_agent(
    agent_name: str,
    server_name: str,
) -> Optional[List[str]]:
    """
    Get the tool allowlist for a specific agent and server combination.

    Args:
        agent_name: Name of the agent (e.g., 'fundamental_analyst')
        server_name: Name of the MCP server (e.g., 'openbb', 'akshare')

    Returns:
        List of allowed tool names, or None if no filtering
    """
    policy_loader = get_tool_policy_loader()
    return policy_loader.get_tool_allowlist(agent_name, server_name)


# =============================================================================
# Global Instance
# =============================================================================

_config_loader: Optional[MCPConfigLoader] = None
_config_converter: Optional[MCPConfigConverter] = None


def get_mcp_config_loader() -> MCPConfigLoader:
    """Get or create the global MCP config loader."""
    global _config_loader
    if _config_loader is None:
        _config_loader = MCPConfigLoader()
    return _config_loader


def get_mcp_config_converter() -> MCPConfigConverter:
    """Get or create the global MCP config converter."""
    global _config_converter
    if _config_converter is None:
        _config_converter = MCPConfigConverter(get_mcp_config_loader())
    return _config_converter


def get_mcps_for_agent(
    agent_name: str,
    server_names: Optional[List[str]] = None,
) -> List[MCPServerConfig]:
    """
    Convenience function to get MCP configs for an agent.

    This is the main entry point for the factory to get MCP configurations.

    Args:
        agent_name: Name of the agent
        server_names: Specific servers to include (None = all enabled)

    Returns:
        List of CrewAI MCPServerConfig objects
    """
    converter = get_mcp_config_converter()

    # If specific servers requested, get allowlists for each
    mcps = []

    if server_names:
        for server_name in server_names:
            allowlist = get_tool_allowlist_for_agent(agent_name, server_name)
            mcp = converter.create_mcp_for_server(server_name, allowlist)
            if mcp:
                mcps.append(mcp)
    else:
        # Get all enabled servers with appropriate allowlists
        for server_name in converter.loader.get_enabled_servers():
            allowlist = get_tool_allowlist_for_agent(agent_name, server_name)
            mcp = converter.create_mcp_for_server(server_name, allowlist)
            if mcp:
                mcps.append(mcp)

    return mcps


# =============================================================================
# CrewAI Native MCP (DB-backed) Loader (v2 migration)
# =============================================================================

_native_mcp_loader: Optional["NativeMCPConfigLoader"] = None


class NativeMCPConfigLoader:
    """DB-backed loader for CrewAI native MCP configs.

    In v2, Agents receive `mcps=[MCPServerSSE/HTTP/Stdio(...)]` directly.
    This loader is intentionally lightweight; it can be extended to query the DB
    for `MCPServer` rows, but tests only require transport detection + singleton.
    """

    def __init__(self):
        self._server_cache: Dict[Any, Any] = {}

    def _get_transport_type(self, server: Any) -> str:
        transport = getattr(server, "transport", None)
        if transport:
            return str(transport).strip().lower()

        url = getattr(server, "url", None)
        if url:
            url_str = str(url)
            if "/sse" in url_str or url_str.endswith("/sse"):
                return "sse"
            return "http"

        command = getattr(server, "command", None)
        if command:
            return "stdio"

        return "sse"

    def _create_from_db_by_keys(
        self,
        server_keys: List[str],
        tool_filter: Optional[List[str]] = None,
    ) -> List[MCPServerConfig]:
        """Create MCP configs by querying database with server_keys.

        Args:
            server_keys: List of server_key strings (e.g., ["akshare", "yfinance"])
            tool_filter: Optional list of tool names to filter

        Returns:
            List of CrewAI MCPServerConfig objects
        """
        from AICrews.database.db_manager import DBManager
        from AICrews.database.models.mcp import MCPServer as MCPServerRow

        db = DBManager()
        out: List[MCPServerConfig] = []

        static_tool_filter = (
            create_static_tool_filter(allowed_tool_names=tool_filter)
            if tool_filter
            else None
        )

        with db.get_session() as session:
            rows = session.execute(
                select(MCPServerRow).where(
                    MCPServerRow.server_key.in_(server_keys),
                    MCPServerRow.is_active == True,
                )
            ).scalars().all()

            if not rows:
                logger.warning(f"No active MCP servers found in DB for keys: {server_keys}")
                return []

            for row in rows:
                transport = str(getattr(row, "transport_type", "sse") or "sse").strip().lower()

                # Handle http_sse as streamable HTTP
                # http_sse means "Streamable HTTP" (HTTP + SSE hybrid protocol)
                # which uses MCPServerHTTP with streamable=True
                if transport == "http_sse":
                    transport = "http"

                if transport == "http":
                    if not getattr(row, "url", None):
                        continue
                    out.append(
                        MCPServerHTTP(
                            url=row.url,
                            headers=None,
                            streamable=True,
                            tool_filter=static_tool_filter,
                        )
                    )
                    logger.info(f"Created MCPServerHTTP for {row.server_key}: {row.url}")
                    continue

                if transport == "stdio":
                    command = getattr(row, "command", None)
                    if not command:
                        continue

                    raw_args = getattr(row, "args", None)
                    args = None
                    if isinstance(raw_args, list):
                        args = raw_args
                    elif isinstance(raw_args, dict):
                        args = raw_args.get("args") or raw_args.get("argv")

                    out.append(
                        MCPServerStdio(
                            command=command,
                            args=args,
                            env=None,
                            tool_filter=static_tool_filter,
                        )
                    )
                    logger.info(f"Created MCPServerStdio for {row.server_key}: {command}")
                    continue

                # Default to SSE
                if not getattr(row, "url", None):
                    continue
                out.append(
                    MCPServerSSE(
                        url=row.url,
                        headers=None,
                        tool_filter=static_tool_filter,
                    )
                )
                logger.info(f"Created MCPServerSSE for {row.server_key}: {row.url}")

        return out

    def create_for_agent(
        self,
        *,
        server_ids: List[Any],
        tool_filter: Optional[List[str]] = None,
        db_session: Any = None,
    ) -> List[MCPServerConfig]:
        """Create MCP configs for an agent.

        Supports both string server_keys and integer server_ids.
        For string keys, first tries YAML/ENV, then falls back to database.
        """
        if not server_ids:
            return []

        if all(isinstance(s, str) for s in server_ids):
            # First try YAML/ENV converter
            converter = get_mcp_config_converter()
            result = converter.get_mcps_for_agent(
                agent_name="agent",
                server_names=[str(s) for s in server_ids],
                tool_allowlist=tool_filter,
            )

            # If found, return
            if result:
                return result

            # Fallback: query database by server_key
            return self._create_from_db_by_keys(
                server_keys=[str(s) for s in server_ids],
                tool_filter=tool_filter,
            )

        if all(isinstance(s, int) for s in server_ids):
            if db_session is None:
                logger.warning("db_session required for numeric mcp_server_ids")
                return []

            from AICrews.database.models.mcp import MCPServer as MCPServerRow

            rows = (
                db_session.query(MCPServerRow)
                .filter(MCPServerRow.id.in_(server_ids))
                .all()
            )
            if not rows:
                return []

            static_tool_filter = (
                create_static_tool_filter(allowed_tool_names=tool_filter)
                if tool_filter
                else None
            )

            out: List[MCPServerConfig] = []
            for row in rows:
                if not getattr(row, "is_active", True):
                    continue

                transport = str(getattr(row, "transport_type", "sse") or "sse").strip().lower()
                if transport == "http":
                    if not getattr(row, "url", None):
                        continue
                    out.append(
                        MCPServerHTTP(
                            url=row.url,
                            headers=None,
                            streamable=True,
                            tool_filter=static_tool_filter,
                        )
                    )
                    continue

                if transport == "stdio":
                    command = getattr(row, "command", None)
                    if not command:
                        continue

                    raw_args = getattr(row, "args", None)
                    args = None
                    if isinstance(raw_args, list):
                        args = raw_args
                    elif isinstance(raw_args, dict):
                        args = raw_args.get("args") or raw_args.get("argv")

                    out.append(
                        MCPServerStdio(
                            command=command,
                            args=args,
                            env=None,
                            tool_filter=static_tool_filter,
                        )
                    )
                    continue

                # Default to SSE
                if not getattr(row, "url", None):
                    continue
                out.append(
                    MCPServerSSE(
                        url=row.url,
                        headers=None,
                        tool_filter=static_tool_filter,
                    )
                )

            return out

        # Unknown ID types; treat as unsupported to avoid misconfiguration.
        return []


def get_native_mcp_loader() -> NativeMCPConfigLoader:
    """Get global NativeMCPConfigLoader singleton."""
    global _native_mcp_loader
    if _native_mcp_loader is None:
        _native_mcp_loader = NativeMCPConfigLoader()
    return _native_mcp_loader
