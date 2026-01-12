"""
Crew Validator - 负责 Crew 组装前的校验
"""
import re
from AICrews.observability.logging import get_logger
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from AICrews.database.models import (
    AgentDefinition,
    TaskDefinition,
    CrewDefinition,
    KnowledgeSource,
    AgentKnowledgeBinding,
    CrewKnowledgeBinding,
    MCPServer,
    UserMCPSubscription,
    UserKnowledgeSubscription,
    UserKnowledgeSource,
    UserModelConfig,
)

logger = get_logger(__name__)


# CrewAI version constraints for Task structured outputs & guardrails
CREWAI_MIN_VERSION = "1.7.1"
CREWAI_MAX_VERSION = "1.8.0"  # exclusive


def check_crewai_version(strict: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Check if the installed CrewAI version is within the supported range.

    Args:
        strict: If True, raise RuntimeError on version mismatch; else return warning.

    Returns:
        (is_ok, warning_message) - warning_message is None if version is OK.
    """
    try:
        import crewai
        from packaging.version import parse as parse_version
    except ImportError as e:
        msg = f"Cannot check CrewAI version: {e}"
        if strict:
            raise RuntimeError(msg)
        return False, msg

    version = getattr(crewai, "__version__", "0.0.0")
    v = parse_version(version)
    min_v = parse_version(CREWAI_MIN_VERSION)
    max_v = parse_version(CREWAI_MAX_VERSION)

    if not (min_v <= v < max_v):
        msg = (
            f"CrewAI version {version} not in supported range "
            f"[{CREWAI_MIN_VERSION}, {CREWAI_MAX_VERSION}). "
            f"Task structured outputs may not work correctly."
        )
        if strict:
            raise RuntimeError(msg)
        return False, msg

    return True, None

@dataclass
class UnauthorizedKnowledgeInfo:
    """未授权知识源信息（用于深度链接和用户操作）"""
    source_key: str
    display_name: str
    tier: str
    price: float

@dataclass
class PreflightResult:
    """扩展版预检结果"""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)  # 新增建议
    missing_variables: List[str] = field(default_factory=list)
    missing_api_keys: List[str] = field(default_factory=list)
    unauthorized_knowledge: List[UnauthorizedKnowledgeInfo] = field(default_factory=list)
    mcp_health: Dict[str, bool] = field(default_factory=dict) # 新增 MCP 健康状态
    version_warning: Optional[str] = None  # CrewAI version check



class CrewValidator:
    """Crew 校验器"""
    
    # 变量模式: {variable_name}
    VARIABLE_PATTERN = re.compile(r'\{(\w+)\}')
    
    def validate(
        self,
        crew_def: CrewDefinition,
        user_id: Optional[int],
        variables: Dict[str, Any],
        session,
    ) -> PreflightResult:
        """
        运行前预检 2.0
        
        检查:
        1. 变量全覆盖与 input_schema 校验
        2. 工具依赖图与启用状态
        3. 知识源可达性与权限
        4. MCP 服务器健康度与认证
        """
        result = PreflightResult(success=True)

        try:
            # 0. CrewAI version check (non-blocking warning)
            version_ok, version_warning = check_crewai_version(strict=False)
            if not version_ok and version_warning:
                result.version_warning = version_warning
                result.warnings.append(version_warning)
                logger.warning(version_warning)

            # 1. 变量全覆盖校验
            required_vars = self._extract_variables(crew_def, session)
            from .variable_defaults import merge_crew_variables

            effective_vars = merge_crew_variables(
                input_schema=crew_def.input_schema,
                default_variables=crew_def.default_variables,
                variables=variables,
            )
            missing_no_defaults = required_vars - set(effective_vars.keys())
            
            if missing_no_defaults:
                result.missing_variables = list(missing_no_defaults)
                result.success = False
                result.errors.append(f"Missing required variables without defaults: {', '.join(missing_no_defaults)}")
                result.hints.append("Please provide values for all required variables in the launch panel.")
            
            # 2. 检查工具启用状态与依赖
            disabled_tools = self._check_agent_tools_status(crew_def, user_id, session)
            if disabled_tools:
                result.success = False
                for agent_name, tools in disabled_tools.items():
                    result.errors.append(f"Agent '{agent_name}' requires disabled tools: {', '.join(tools)}")
                result.hints.append("Enable required tools in the Strategy Studio or remove them from the agent configuration.")

            # 3. 检查 MCP 健康度
            mcp_health = self._check_mcp_health(crew_def, user_id, session)
            result.mcp_health = mcp_health
            for server_name, is_healthy in mcp_health.items():
                if not is_healthy:
                    result.warnings.append(f"MCP Server '{server_name}' appears to be offline or unreachable.")
                    result.hints.append(f"Check the status of MCP Server '{server_name}' in the settings.")

            # 4. 检查知识源权限
            unauthorized = self._check_knowledge_access(crew_def, user_id, session)
            if unauthorized:
                result.unauthorized_knowledge = unauthorized
                result.success = False
                unauthorized_names = [k.display_name for k in unauthorized]
                result.errors.append(f"Unauthorized access to knowledge sources: {', '.join(unauthorized_names)}")
                result.hints.append("Add or subscribe to the required knowledge sources in Tools → Knowledge.")

            # 5. 检查 Skill 可用性（新架构：Task 1.5）
            skill_errors, skill_warnings = self._check_skill_availability(crew_def, session)
            if skill_errors:
                result.success = False
                result.errors.extend(skill_errors)
                result.hints.append("Check Tools→Providers to enable missing capabilities or fix provider health.")
            if skill_warnings:
                result.warnings.extend(skill_warnings)

            # 6. 检查 Agent LLM 配置（避免运行期才 401）
            llm_errors, llm_warnings, llm_hints = self._check_agent_llm_configs(
                crew_def=crew_def, user_id=user_id, session=session
            )
            if llm_warnings:
                result.warnings.extend(llm_warnings)
            if llm_hints:
                result.hints.extend(llm_hints)
            if llm_errors:
                result.success = False
                result.errors.extend(llm_errors)

            # 7. 检查 Task Output Specs（schema_key、output_mode、provider capability）
            output_spec_result = self._validate_task_output_specs(crew_def, session)
            if output_spec_result.get("errors"):
                result.success = False
                result.errors.extend(output_spec_result["errors"])
            if output_spec_result.get("warnings"):
                result.warnings.extend(output_spec_result["warnings"])
            if output_spec_result.get("hints"):
                result.hints.extend(output_spec_result["hints"])
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Preflight internal error: {str(e)}")
            logger.exception("Preflight 2.0 check error")
        
        return result

    def _check_agent_llm_configs(
        self,
        crew_def: CrewDefinition,
        user_id: Optional[int],
        session,
    ) -> tuple[list[str], list[str], list[str]]:
        """检查 Crew 中每个 Agent 的 LLM 绑定是否完整可用。

        LLM 解析优先级：
        1. RunContext policy routing (如果存在)
        2. Agent 的 user_model_config_id (BYOK 用户)
        3. Agent 的 llm_tier + 系统环境变量 (FAIC_LLM_AGENTS_{TIER}_*)
        4. 系统默认 (FAIC_LLM_AGENTS_FAST_*)
        """
        errors: list[str] = []
        warnings: list[str] = []
        hints: list[str] = []

        try:
            from AICrews.llm.core.config_store import get_config_store
            from AICrews.llm.core.config_models import ProviderType

            config_store = get_config_store()
        except Exception as e:
            warnings.append(f"LLM config store load failed: {e}")
            hints.append("Check server logs for LLM config loading errors (providers.yaml).")
            return errors, warnings, hints

        # Check 1: RunContext policy routing
        policy_llm_ok = False
        if user_id is not None:
            try:
                from AICrews.application.crew.run_context import get_current_run_context
                from AICrews.llm.policy_router import LLMPolicyRouter
                from AICrews.schemas.llm_policy import LLMScope

                run_ctx = get_current_run_context()
                if run_ctx is not None:
                    proxy_base_url = os.getenv(
                        "LITELLM_PROXY_BASE_URL", "http://litellm:4000/v1"
                    )
                    encryption_key_str = os.getenv("ENCRYPTION_KEY")
                    if not encryption_key_str:
                        logger.warning(
                            "ENCRYPTION_KEY not set; using default dev key (NOT for production)"
                        )
                    from AICrews.utils.encryption import get_encryption_key_bytes

                    encryption_key = get_encryption_key_bytes()

                    scope = LLMScope(getattr(run_ctx, "effective_scope", "agents_fast"))
                    router = LLMPolicyRouter(
                        proxy_base_url=proxy_base_url, encryption_key=encryption_key
                    )
                    router.resolve_from_policy(
                        scope=scope,
                        user_id=user_id,
                        db=session,
                        byok_allowed=bool(getattr(run_ctx, "byok_allowed", False)),
                        custom_tags=["source:preflight"],
                    )
                    policy_llm_ok = True
            except Exception:
                policy_llm_ok = False

        # Check 2: System default LLM from environment variables
        system_llm_ok = False
        system_llm_tier = "agents_fast"  # Default tier
        try:
            from AICrews.llm.system_config import get_system_llm_config_store
            from AICrews.schemas.llm_policy import LLMScope

            system_store = get_system_llm_config_store()
            # Try to get agents_fast config (default tier)
            system_store.get_config(LLMScope.AGENTS_FAST)
            system_llm_ok = True
        except Exception:
            system_llm_ok = False

        # 去重：一个 Agent 可能在 structure 中出现多次
        agent_ids: set[int] = set()
        for entry in crew_def.structure or []:
            agent_id = entry.get("agent_id")
            if agent_id:
                agent_ids.add(int(agent_id))

        for agent_id in sorted(agent_ids):
            agent_def = session.get(AgentDefinition, agent_id)
            if not agent_def:
                continue

            llm_cfg = agent_def.llm_config or {}
            model_config_id = llm_cfg.get("user_model_config_id")
            llm_tier = llm_cfg.get("llm_tier")

            if not model_config_id:
                # No explicit user_model_config_id binding
                if policy_llm_ok:
                    # RunContext available - will use policy routing
                    continue
                elif system_llm_ok:
                    # System default available - will use FAIC_LLM_AGENTS_{TIER}_*
                    effective_tier = llm_tier or system_llm_tier
                    warnings.append(
                        f"Agent '{agent_def.name}' has no explicit LLM binding; "
                        f"will use system default (tier: {effective_tier})."
                    )
                else:
                    # No fallback available
                    errors.append(
                        f"Agent '{agent_def.name}' missing LLM binding and no system default configured."
                    )
                    hints.append(
                        "Fix: Set FAIC_LLM_AGENTS_FAST_PROVIDER/MODEL/API_KEY environment variables, "
                        "or bind a user model config to each agent."
                    )
                continue

            user_model_config = session.get(UserModelConfig, int(model_config_id))
            if not user_model_config:
                errors.append(
                    f"Agent '{agent_def.name}' references missing UserModelConfig id={model_config_id}."
                )
                continue

            # 所有权校验：非模板运行应绑定当前用户的模型配置
            if user_id and user_model_config.user_id != user_id:
                errors.append(
                    f"Agent '{agent_def.name}' uses a model config not owned by current user "
                    f"(model_config_id={model_config_id})."
                )
                continue

            if not user_model_config.is_available:
                errors.append(
                    f"Agent '{agent_def.name}' uses an unavailable model config (id={model_config_id})."
                )
                continue

            if not user_model_config.is_active:
                warnings.append(
                    f"Agent '{agent_def.name}' uses an inactive model config (id={model_config_id})."
                )
                hints.append(
                    "Enable the selected model config in LLM settings, or rebind the agent to an active model."
                )

            if not user_model_config.llm_config or not user_model_config.llm_config.api_key:
                errors.append(
                    f"Agent '{agent_def.name}' has empty API key in LLM config "
                    f"(model_config_id={model_config_id})."
                )
                continue

            provider = user_model_config.llm_config.provider
            model = user_model_config.model

            provider_key = getattr(provider, "provider_key", None) or "unknown"
            provider_cfg = config_store.get_provider(provider_key)
            provider_type = getattr(provider_cfg, "provider_type", None) if provider_cfg else None

            # base_url 允许为 None（会使用 providers.yaml 的默认 api_base），但对 openai-compatible
            # 或 volcengine 这类必须靠 base_url 路由的提供商，不能两者都为空。
            base_url = user_model_config.llm_config.base_url
            fallback_base = provider_cfg.endpoints.api_base if provider_cfg else ""
            resolved_base = base_url or fallback_base

            if provider_type in (ProviderType.OPENAI_COMPATIBLE, ProviderType.VOLCENGINE):
                if not resolved_base:
                    errors.append(
                        f"Agent '{agent_def.name}' provider '{provider_key}' missing base_url "
                        f"(model_config_id={model_config_id})."
                    )
                    hints.append(
                        "Set a provider base_url in LLM settings, or configure endpoints.api_base in config/llm/providers.yaml."
                    )

            # 软提示：OpenAI provider 使用非 OpenAI key 时，最常见原因是 base_url/provider 选错
            if provider_key == "openai":
                api_key = user_model_config.llm_config.api_key or ""
                if api_key and not api_key.startswith("sk-"):
                    warnings.append(
                        f"Agent '{agent_def.name}' uses OpenAI provider with a non-OpenAI-looking key "
                        f"(model_config_id={model_config_id})."
                    )
                    hints.append(
                        "If you're using an OpenAI-compatible vendor (Volcengine/Kimi/etc), ensure provider_key and base_url match that vendor."
                    )

        return errors, warnings, hints

    def _check_mcp_health(self, crew_def: CrewDefinition, user_id: Optional[int], session) -> Dict[str, bool]:
        """检查 Crew 涉及的 MCP 服务器健康状态"""
        health_map = {}
        
        # 收集所有需要的 MCP Server ID
        server_ids = set()
        for entry in crew_def.structure or []:
            agent_id = entry.get("agent_id")
            if not agent_id: continue
            agent_def = session.get(AgentDefinition, agent_id)
            if agent_def and agent_def.mcp_server_ids:
                server_ids.update(agent_def.mcp_server_ids)
        
        # 简单检查在线状态 (此处可扩展为实际 ping MCP 端点)
        for sid in server_ids:
            server = session.get(MCPServer, sid)
            if server:
                # 暂时以数据库标记为准，未来可加入真实网络探测
                health_map[server.display_name] = server.is_active
                
        return health_map


    def _check_agent_tools_status(
        self,
        crew_def: CrewDefinition,
        user_id: Optional[int],
        session,
    ) -> Dict[str, List[str]]:
        """检查 Agent 绑定的工具是否已启用"""
        from AICrews.tools.registry.tool_registry import ToolRegistry
        registry = ToolRegistry(db=session)
        
        # 获取所有已启用的工具名称
        enabled_tools = registry.get_user_tools(user_id=user_id)
        enabled_tool_names = {getattr(t, "__name__", str(t)) for t in enabled_tools}
        
        disabled_map = {}
        
        for entry in crew_def.structure or []:
            agent_id = entry.get("agent_id")
            if not agent_id:
                continue
            
            agent_def = session.get(AgentDefinition, agent_id)
            if not agent_def:
                continue
            
            # 收集该 Agent 绑定的所有工具 ID
            requested_tool_ids = []
            if agent_def.loadout_data:
                for tier in ['data_tools', 'quant_tools', 'external_tools', 'strategies']:
                    requested_tool_ids.extend(agent_def.loadout_data.get(tier, []))
            elif agent_def.tool_ids:
                requested_tool_ids.extend([str(tid) for tid in agent_def.tool_ids])
            
            if not requested_tool_ids:
                continue
                
            # 检查这些工具是否在已启用列表中
            # 注意：requested_tool_ids 可能是命名空间格式 (data:price)
            agent_disabled = []
            for tid in requested_tool_ids:
                # 简单匹配：如果 tid 包含在已启用工具的某种表示中
                # 实际上 ToolRegistry._get_tool_key 会给工具加前缀
                # 这里我们做个反向检查：如果这个工具 ID 无法通过 registry 加载出任何工具，说明它被禁用了
                loaded = registry.get_tools_by_namespaced_ids([tid], user_id=user_id)
                if not loaded:
                    agent_disabled.append(tid)
            
            if agent_disabled:
                disabled_map[agent_def.name] = agent_disabled
                
        return disabled_map
    
    def _extract_variables(
        self,
        crew_def: CrewDefinition,
        session,
    ) -> Set[str]:
        """提取配置中所有需要的变量"""
        variables = set()
        
        # 从 structure 中提取 agent 和 task
        for entry in crew_def.structure or []:
            agent_id = entry.get("agent_id")
            task_ids = entry.get("tasks", [])
            
            # 检查 Agent
            if agent_id:
                agent_def = session.get(AgentDefinition, agent_id)
                if agent_def:
                    variables.update(self._find_variables_in_text(agent_def.goal))
                    variables.update(self._find_variables_in_text(agent_def.backstory))
            
            # 检查 Tasks
            for task_id in task_ids:
                task_def = session.get(TaskDefinition, task_id)
                if task_def:
                    variables.update(self._find_variables_in_text(task_def.description))
                    variables.update(self._find_variables_in_text(task_def.expected_output))
            
        # 从 input_schema 中提取变量
        if crew_def.input_schema:
            variables.update(self._find_variables_in_json(crew_def.input_schema))
            
        # 从 router_config 中提取变量
        if crew_def.router_config:
            variables.update(self._find_variables_in_json(crew_def.router_config))
        
        return variables

    def _find_variables_in_json(self, data: Any) -> Set[str]:
        """递归从 JSON 数据中提取变量名"""
        variables = set()
        if isinstance(data, str):
            variables.update(self._find_variables_in_text(data))
        elif isinstance(data, list):
            for item in data:
                variables.update(self._find_variables_in_json(item))
        elif isinstance(data, dict):
            for value in data.values():
                variables.update(self._find_variables_in_json(value))
        return variables
    
    def _find_variables_in_text(self, text: str) -> Set[str]:
        """从文本中提取变量名"""
        if not text:
            return set()
        return set(self.VARIABLE_PATTERN.findall(text))
    
    def _check_api_keys(
        self,
        crew_def: CrewDefinition,
        user_id: Optional[int],
        session,
    ) -> List[str]:
        """检查所有需要的 API Keys"""
        missing = []
        
        # 获取用户订阅的 MCP 服务器
        if user_id:
            subscriptions = session.query(UserMCPSubscription).filter(
                UserMCPSubscription.user_id == user_id,
                UserMCPSubscription.is_active == True,
            ).all()
            
            for sub in subscriptions:
                server = session.get(MCPServer, sub.server_id)
                if server and server.requires_auth and not sub.api_key:
                    missing.append(server.display_name)
        
        return missing
    
    def _check_knowledge_access(
        self,
        crew_def: CrewDefinition,
        user_id: Optional[int],
        session,
    ) -> List[UnauthorizedKnowledgeInfo]:
        """检查知识源访问权限。

        Runtime (CrewAssembler) loads knowledge sources from compiled structure:
        `compiled_agent["knowledge_source_ids"]` -> `KnowledgeLoader.load_by_ids(...)`.

        Preflight must validate the same effective IDs to avoid false passes/fails.
        """
        unauthorized: List[UnauthorizedKnowledgeInfo] = []
        seen_source_ids: set[int] = set()  # 避免重复报告同一个source

        def _maybe_require_subscription(*, source: KnowledgeSource) -> None:
            source_id = getattr(source, "id", None)
            if not isinstance(source_id, int):
                return
            if source_id in seen_source_ids:
                return
            if getattr(source, "tier", None) != "premium":
                return

            sub = None
            if user_id is not None:
                sub = session.query(UserKnowledgeSubscription).filter(
                    UserKnowledgeSubscription.user_id == user_id,
                    UserKnowledgeSubscription.source_id == source_id,
                    UserKnowledgeSubscription.is_active == True,
                ).first()

            if sub:
                return

            unauthorized.append(
                UnauthorizedKnowledgeInfo(
                    source_key=str(getattr(source, "source_key", "")),
                    display_name=str(getattr(source, "display_name", "")),
                    tier=str(getattr(source, "tier", "premium")),
                    price=float(getattr(source, "price", 0.0) or 0.0),
                )
            )
            seen_source_ids.add(source_id)

        # 1) Validate runtime-effective IDs (structure.entry.knowledge_source_ids or AgentDefinition.knowledge_source_ids)
        for entry in crew_def.structure or []:
            agent_id = entry.get("agent_id")
            if not agent_id:
                continue

            agent_def = session.get(AgentDefinition, agent_id)
            if not agent_def:
                continue

            effective_ids = entry.get("knowledge_source_ids") or agent_def.knowledge_source_ids or []
            if isinstance(effective_ids, (int, str)):
                effective_ids = [effective_ids]
            if not isinstance(effective_ids, list):
                continue

            for raw_id in effective_ids:
                try:
                    source_id = int(raw_id)
                except Exception:
                    continue

                if source_id in seen_source_ids:
                    continue

                # Same resolution order as KnowledgeLoader.load_by_ids:
                # 1) system KnowledgeSource, 2) user-owned UserKnowledgeSource.
                source = session.get(KnowledgeSource, source_id)
                if source:
                    _maybe_require_subscription(source=source)
                    continue

                user_source = session.get(UserKnowledgeSource, source_id)
                if user_source and user_id is not None:
                    if getattr(user_source, "user_id", None) == user_id and getattr(
                        user_source, "is_active", True
                    ):
                        continue

        # 2) Validate binding-table knowledge sources (legacy behavior still expected by tests)
        for entry in crew_def.structure or []:
            agent_id = entry.get("agent_id")
            if not agent_id:
                continue

            agent_def = session.get(AgentDefinition, agent_id)
            if not agent_def:
                continue

            binding = session.query(AgentKnowledgeBinding).filter(
                AgentKnowledgeBinding.crew_name == crew_def.name,
                AgentKnowledgeBinding.agent_name == agent_def.name,
            ).first()

            for raw_id in (getattr(binding, "source_ids", None) or []):
                try:
                    source_id = int(raw_id)
                except Exception:
                    continue

                if source_id in seen_source_ids:
                    continue

                source = session.get(KnowledgeSource, source_id)
                if source:
                    _maybe_require_subscription(source=source)

        if user_id is not None:
            crew_binding = session.query(CrewKnowledgeBinding).filter(
                CrewKnowledgeBinding.user_id == user_id,
                CrewKnowledgeBinding.crew_name == crew_def.name,
            ).first()

            for raw_id in (getattr(crew_binding, "source_ids", None) or []):
                try:
                    source_id = int(raw_id)
                except Exception:
                    continue

                if source_id in seen_source_ids:
                    continue

                source = session.get(KnowledgeSource, source_id)
                if source:
                    _maybe_require_subscription(source=source)

        return unauthorized

    def _check_skill_availability(
        self,
        crew_def: "CrewDefinition",
        session: Session
    ) -> Tuple[List[str], List[str]]:
        """Check if all skills in crew agents are available.

        Validates that:
        1. All skill_keys exist in SkillCatalog
        2. Required capabilities have enabled + healthy providers

        Returns:
            (errors, warnings) where:
            - errors: Skills that are completely blocked (provider disabled/unhealthy)
            - warnings: Skills with degraded capabilities
        """
        from AICrews.database.models.skill import SkillCatalog
        from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
        from AICrews.database.models.agent import AgentDefinition

        errors = []
        warnings = []

        # Collect all skill_keys from all agents via structure
        all_skill_keys = set()
        for entry in crew_def.structure or []:
            agent_id = entry.get("agent_id")
            if not agent_id:
                continue
            agent_def = session.get(AgentDefinition, agent_id)
            if agent_def and agent_def.loadout_data and "skill_keys" in agent_def.loadout_data:
                skill_keys = agent_def.loadout_data.get("skill_keys", [])
                all_skill_keys.update(skill_keys)

        if not all_skill_keys:
            return errors, warnings

        # Fetch skill definitions from catalog
        skills = session.query(SkillCatalog).filter(
            SkillCatalog.skill_key.in_(all_skill_keys)
        ).all()

        skill_map = {s.skill_key: s for s in skills}

        # Check for missing skills
        missing_skills = all_skill_keys - set(skill_map.keys())
        for skill_key in missing_skills:
            errors.append(f"Skill not found in catalog: {skill_key}")

        # Check capability availability for each skill
        for skill in skills:
            # Note: Each skill has ONE capability_id, not a list
            cap_id = skill.capability_id

            if not cap_id:
                continue

            # Find providers that implement this capability
            mappings = session.query(ProviderCapabilityMapping).filter(
                ProviderCapabilityMapping.capability_id == cap_id
            ).all()

            if not mappings:
                errors.append(f"Skill '{skill.skill_key}' requires capability '{cap_id}' but no provider implements it")
                continue

            # Check if any provider is enabled and healthy
            available = False
            degraded = False

            for mapping in mappings:
                provider = session.get(CapabilityProvider, mapping.provider_id)
                if provider:
                    if provider.enabled and provider.healthy:
                        available = True
                        break
                    elif provider.enabled and not provider.healthy:
                        degraded = True

            if not available:
                if degraded:
                    warnings.append(f"Skill '{skill.skill_key}' capability '{cap_id}' has degraded availability (provider unhealthy)")
                else:
                    errors.append(f"Skill '{skill.skill_key}' requires capability '{cap_id}' but no enabled/healthy provider found")

        return errors, warnings

    def _validate_task_output_specs(
        self,
        crew_def: CrewDefinition,
        session: Session
    ) -> Dict[str, List[str]]:
        """Validate TaskOutputSpec settings for all tasks in crew.

        Checks:
        1. schema_key exists in registry (if specified)
        2. output_mode is a valid value
        3. For native modes, check if provider supports function calling
        4. If degradation is needed and strict_mode=True, error instead of warn

        Returns:
            Dict with "errors", "warnings", "hints" lists
        """
        from AICrews.application.crew.task_output_registry import resolve_output_model
        from AICrews.application.crew.task_runtime_builder import get_provider_capabilities

        errors: List[str] = []
        warnings: List[str] = []
        hints: List[str] = []

        VALID_OUTPUT_MODES = {
            "raw", "native_json", "native_pydantic", "soft_json", "soft_pydantic"
        }

        # Collect all task IDs from structure
        task_ids: Set[int] = set()
        structure_map: Dict[int, int] = {}  # task_id -> agent_id
        for entry in crew_def.structure or []:
            # Handle both formats:
            # 1. Standard: {"agent_id": X, "tasks": [Y, Z]}
            # 2. Simplified (tests): {"task_id": X, "agent_id": Y}
            agent_id = entry.get("agent_id")

            if "tasks" in entry:
                # Standard format with tasks list
                for task_id in entry.get("tasks", []):
                    task_ids.add(int(task_id))
                    structure_map[int(task_id)] = agent_id
            elif "task_id" in entry:
                # Simplified format with single task_id
                task_id = entry.get("task_id")
                if task_id:
                    task_ids.add(int(task_id))
                    structure_map[int(task_id)] = agent_id

        for task_id in sorted(task_ids):
            task_def = session.get(TaskDefinition, task_id)
            if not task_def:
                continue

            task_name = task_def.name
            output_mode = task_def.output_mode or "raw"
            schema_key = task_def.output_schema_key
            strict_mode = task_def.strict_mode

            # Check 1: Validate output_mode value
            if output_mode not in VALID_OUTPUT_MODES:
                warnings.append(
                    f"Task '{task_name}' has invalid output_mode '{output_mode}'. "
                    f"Valid values: {', '.join(VALID_OUTPUT_MODES)}"
                )
                hints.append("Set output_mode to one of: raw, native_json, native_pydantic, soft_json, soft_pydantic")

            # Check 2: Validate schema_key exists in registry
            if schema_key:
                model_class = resolve_output_model(schema_key)
                if model_class is None:
                    warnings.append(
                        f"Task '{task_name}' references unknown output schema '{schema_key}'"
                    )
                    hints.append("Check available schemas at GET /api/v1/task-output-schemas")

            # Check 3: For native modes, verify provider supports both function_calling AND json_schema
            if output_mode in ("native_json", "native_pydantic"):
                agent_id = structure_map.get(task_id)
                if agent_id:
                    agent_def = session.get(AgentDefinition, agent_id)
                    if agent_def:
                        llm_cfg = agent_def.llm_config or {}
                        provider_key = llm_cfg.get("provider_key", "unknown")
                        model_name = llm_cfg.get("model")

                        try:
                            capabilities = get_provider_capabilities(provider_key, model_name)
                            supports_fc = capabilities.get("supports_function_calling", False)
                            supports_json_schema = capabilities.get("supports_json_schema", False)
                            supports_native = supports_fc and supports_json_schema

                            if not supports_native:
                                missing = []
                                if not supports_fc:
                                    missing.append("function_calling")
                                if not supports_json_schema:
                                    missing.append("json_schema")

                                msg = (
                                    f"Task '{task_name}' uses output_mode '{output_mode}' "
                                    f"but agent '{agent_def.name}' provider '{provider_key}' "
                                    f"lacks required capabilities: {', '.join(missing)}. "
                                    f"Will degrade to soft mode."
                                )
                                if strict_mode:
                                    errors.append(
                                        f"Task '{task_name}' strict_mode=True forbids degradation "
                                        f"from '{output_mode}' to soft mode (provider '{provider_key}' "
                                        f"lacks {', '.join(missing)})"
                                    )
                                    hints.append(
                                        f"Either: (1) Set strict_mode=False on task '{task_name}', "
                                        f"(2) Switch to soft_{output_mode.split('_')[1]} mode, or "
                                        f"(3) Use a provider with both function_calling and json_schema support"
                                    )
                                else:
                                    warnings.append(msg)
                                    hints.append(
                                        f"Consider using soft_{output_mode.split('_')[1]} mode explicitly "
                                        f"to avoid runtime degradation overhead"
                                    )
                        except Exception as e:
                            warnings.append(
                                f"Task '{task_name}' provider capability check failed: {e}"
                            )

        return {"errors": errors, "warnings": warnings, "hints": hints}
