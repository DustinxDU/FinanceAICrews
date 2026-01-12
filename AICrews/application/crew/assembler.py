"""
Crew Assembler - 动态 Crew 组装引擎

从数据库读取 JSON 配置并实例化为 Python 对象
支持:
1. 运行前预检 (Pre-flight Check)
2. 运行时动态插值
3. 配置版本控制
4. 工具和知识源自动绑定

Philosophy: Database is Config, Code is Engine
"""

from AICrews.observability.logging import get_logger
import asyncio
import os  # 添加 os 导入
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from crewai import Agent, Crew, Process, Task, LLM

from AICrews.config import get_settings
from AICrews.llm.unified_manager import get_unified_llm_manager
from AICrews.llm.policy_router import LLMPolicyRouter
from AICrews.schemas.llm_policy import LLMKeyProvisioningError
from AICrews.database.db_manager import DBManager
from AICrews.database.models import (
    AgentDefinition,
    TaskDefinition,
    CrewDefinition,
    CrewVersion,
    User,
    KnowledgeSource,
    AgentToolBinding,
    AgentKnowledgeBinding,
    MCPServer,
    UserMCPSubscription,
)
from AICrews.infrastructure.knowledge.knowledge_sources import KnowledgeLoader
from AICrews.utils.citations import CitationParser
from AICrews.utils.redaction import truncate_text
from .preflight import CrewValidator, PreflightResult
from .versioning import CrewVersionManager
from .task_runtime_builder import build_task_kwargs, get_provider_capabilities

logger = get_logger(__name__)


def resolve_llm_call_from_run_context(*, run_context, user_id: int, db):
    """Resolve a proxy LLM call contract from entitlements RunContext.

    This is the single integration point between runtime entitlements and LLM routing.
    """
    from AICrews.schemas.llm_policy import LLMScope

    proxy_base_url = os.getenv("LITELLM_PROXY_BASE_URL", "http://litellm:4000/v1")

    encryption_key_str = os.getenv("ENCRYPTION_KEY")
    if not encryption_key_str:
        logger.warning(
            "ENCRYPTION_KEY not set; using default dev key (NOT for production)"
        )
    from AICrews.utils.encryption import get_encryption_key_bytes

    encryption_key = get_encryption_key_bytes()

    scope = LLMScope(run_context.effective_scope)
    router = LLMPolicyRouter(proxy_base_url=proxy_base_url, encryption_key=encryption_key)
    return router.resolve_from_policy(
        scope=scope,
        user_id=user_id,
        db=db,
        byok_allowed=bool(getattr(run_context, "byok_allowed", False)),
        custom_tags=["source:crew_assembler"],
    )


def create_llm_from_run_context(*, run_context, user_id: int, db) -> LLM:
    resolved_call = resolve_llm_call_from_run_context(
        run_context=run_context, user_id=user_id, db=db
    )
    return LLM(
        provider="openai",
        model=resolved_call.model,
        api_key=resolved_call.api_key,
        base_url=resolved_call.base_url,
        api_base=resolved_call.base_url,
        extra_headers=getattr(resolved_call, "extra_headers", None),
        extra_body=getattr(resolved_call, "extra_body", None),
    )


def check_embedder_availability() -> Tuple[bool, Optional[str]]:
    """Check if the ONNX embedder is available for crew memory.

    Returns:
        Tuple of (is_available, error_message).
        If available, returns (True, None).
        If not available, returns (False, error_description).
    """
    try:
        # Try to import the ONNX embedder from crewai
        from crewai.memory.storage.rag_storage import RAGStorage

        # Try a minimal initialization to verify ONNX runtime is available
        # This catches missing onnxruntime or model download issues
        import importlib.util

        if importlib.util.find_spec("onnxruntime") is None:
            return False, "onnxruntime package not installed"

        # Check if the default ONNX model can be loaded
        # CrewAI uses sentence-transformers with ONNX backend
        if importlib.util.find_spec("chromadb") is None:
            return False, "chromadb package not installed (required for memory)"

        return True, None
    except ImportError as e:
        return False, f"Missing dependency: {e}"
    except Exception as e:
        return False, f"Embedder initialization failed: {e}"


def build_task_output_callback(
    *,
    job_id: str,
    task_id: str,
    agent_name: str,
    task_description: str,
    diagnostics: Dict[str, Any],
):
    """Build a task callback that emits TASK_OUTPUT events.

    This factory creates a callback function that processes CrewAI TaskOutput
    and emits structured TASK_OUTPUT events with 3-layer payload:
    - summary: raw_preview, json_dict preview, pydantic dump, validation status
    - artifact_ref: placeholder for archive path
    - diagnostics: output_mode, schema_key, citations, etc.

    Args:
        job_id: The job/run ID
        task_id: The task ID
        agent_name: Name of the agent executing the task
        task_description: Task description (for logging)
        diagnostics: Diagnostics from task_runtime_builder (_diagnostics)

    Returns:
        A callback function that accepts CrewAI TaskOutput
    """
    from AICrews.services.tracking_service import TrackingService
    from AICrews.schemas.stats import AgentActivityEvent

    def task_output_callback(output):
        tracker = TrackingService()

        # 1. Extract raw, json_dict, pydantic from output
        raw = getattr(output, "raw", "") or ""
        json_dict = getattr(output, "json_dict", None)
        pydantic_obj = getattr(output, "pydantic", None)

        # 2. Parse citations from raw text
        citation_parser = CitationParser()
        citations = citation_parser.extract(raw)
        citation_data = [
            {"source_name": c.source_name, "is_valid": c.is_valid}
            for c in citations
        ]

        # 3. Build summary layer
        summary = {
            "raw_preview": truncate_text(raw, limit=500),
            "validation_passed": True,  # Assume passed if we got here
        }

        if json_dict:
            # Include truncated JSON preview
            import json
            json_preview = json.dumps(json_dict)[:500]
            summary["json_dict_preview"] = json_preview

        if pydantic_obj is not None:
            try:
                pydantic_dump = pydantic_obj.model_dump()
                summary["pydantic_dump"] = pydantic_dump
            except Exception:
                pass  # Ignore if model_dump fails

        # 4. Build artifact_ref layer (placeholder, filled by archive service)
        artifact_ref = {
            "job_id": job_id,
            "task_id": task_id,
            "path": None,  # Will be set by archive service
        }

        # 5. Build diagnostics layer
        diag = {
            "output_mode": diagnostics.get("effective_mode", diagnostics.get("requested_mode", "raw")),
            "schema_key": diagnostics.get("schema_key"),
            "citations": citation_data,
            "citation_count": len(citations),
            "degraded": diagnostics.get("degraded", False),
            "warnings": diagnostics.get("warnings", []),
        }

        # 6. Emit TASK_OUTPUT event
        tracker.add_task_output_event(
            job_id=job_id,
            agent_name=agent_name,
            task_id=task_id,
            payload={
                "summary": summary,
                "artifact_ref": artifact_ref,
                "diagnostics": diag,
            },
        )

        # Also emit activity event for backward compatibility
        tracker.add_activity(
            job_id,
            AgentActivityEvent(
                agent_name=agent_name,
                activity_type="task_completed",
                message=f"Completed task: {task_description[:50]}...",
                timestamp=datetime.now(),
            ),
        )

    return task_output_callback


@dataclass
class AssemblyContext:
    """组装上下文"""

    crew_id: int
    user_id: Optional[int]
    ticker: str
    date: str
    variables: Dict[str, Any]
    job_id: Optional[str] = None


class CrewAssembler:
    """
    Crew 组装引擎

    负责从数据库配置动态组装 CrewAI 对象
    """

    def __init__(self, db: Optional[DBManager] = None):
        self.db = db or DBManager()
        self.llm_manager = get_unified_llm_manager()

        # 助手组件
        self.validator = CrewValidator()
        self.version_manager = CrewVersionManager()

        from AICrews.infrastructure.cache.redis_manager import get_redis_manager

        self.redis = get_redis_manager()

        from AICrews.infrastructure.cache.layered_cache_manager import LayeredCacheManager
        from AICrews.tools.registry.tool_preregistrar import ToolPreregistrar

        self._cache_manager = LayeredCacheManager(redis_manager=self.redis)
        self._tool_preregistrar = ToolPreregistrar()
        self._memory_cache: Dict[str, Any] = {}

    def _get_cache_key(
        self, crew_id: int, user_id: Optional[int], variables: Dict[str, Any]
    ) -> str:
        """生成编译产物缓存键"""
        import hashlib
        import json

        var_hash = hashlib.md5(
            json.dumps(variables, sort_keys=True).encode()
        ).hexdigest()
        return f"compiled_crew:{crew_id}:{user_id or 0}:{var_hash}"

    def interpolate_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """
        将变量插值到文本中

        支持两种格式的占位符:
        - {{variable_name}} (双花括号, Jinja-style)
        - {variable_name} (单花括号)

        缺失变量保持原样不替换。
        """
        if not text or not variables:
            return text

        import re

        result = str(text)

        # First pass: replace {{var}} (double braces)
        def replace_double(match):
            key = match.group(1).strip()
            return str(variables.get(key, match.group(0)))

        result = re.sub(r"\{\{(\w+)\}\}", replace_double, result)

        # Second pass: replace {var} (single braces, not part of {{ or }})
        # Use negative lookbehind/lookahead to avoid matching braces that were
        # part of unresolved {{missing}} patterns
        def replace_single(match):
            key = match.group(1).strip()
            return str(variables.get(key, match.group(0)))

        result = re.sub(r"(?<!\{)\{(\w+)\}(?!\})", replace_single, result)

        return result

    def _wrap_router_condition(self, description: str, route_label: str) -> str:
        """Wrap task description with router condition guard.

        This is applied at runtime compile time to avoid polluting ui_state.
        The guard instructs the agent to only execute if the router decision
        matches the expected route.

        Args:
            description: Original task description
            route_label: Expected router decision value

        Returns:
            Wrapped description with router condition guard
        """
        from AICrews.application.crew.graph_compiler import _get_graph_config

        graph_config = _get_graph_config()

        prefix_tpl = graph_config.get(
            "router_condition_prefix",
            "CRITICAL INSTRUCTION: Review the output of the previous Router decision task. "
            "IF AND ONLY IF the decision was '{route_label}', then proceed with the following task:\n\n"
            "---\nORIGINAL TASK:\n",
        )
        suffix_tpl = graph_config.get(
            "router_condition_suffix",
            "\n---\nOTHERWISE: Output exactly \"SKIPPED_DUE_TO_ROUTER\" and do nothing else.\n\n"
            "REMEMBER: You must check the Router decision first. "
            "Only execute if the decision matches '{route_label}'.",
        )

        prefix = prefix_tpl.format(route_label=route_label)
        suffix = suffix_tpl.format(route_label=route_label)

        return prefix + description + suffix

    async def get_compiled_crew(
        self, crew_id: int, user_id: Optional[int], variables: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """从缓存获取编译后的 Crew"""
        key = self._get_cache_key(crew_id, user_id, variables)
        try:
            cache_mgr = getattr(self, "_cache_manager", None)
            if cache_mgr is not None and hasattr(cache_mgr, "get_json"):
                return await cache_mgr.get_json(key, layer="redis")
        except Exception:
            logger.debug("Layered cache get_json failed; falling back to redis", exc_info=True)
        return await self.redis.get_json(key)

    async def cache_compiled_crew(
        self,
        crew_id: int,
        user_id: Optional[int],
        variables: Dict[str, Any],
        data: Dict[str, Any],
        ttl: int = 1800,
    ):
        """缓存编译后的 Crew (默认 30 分钟)"""
        key = self._get_cache_key(crew_id, user_id, variables)
        try:
            cache_mgr = getattr(self, "_cache_manager", None)
            if cache_mgr is not None and hasattr(cache_mgr, "set_json"):
                await cache_mgr.set_json(key, data, ttl=ttl, layer="redis")
                return
        except Exception:
            logger.debug("Layered cache set_json failed; falling back to redis", exc_info=True)
        await self.redis.set(key, data, ttl=ttl)

    def compile(
        self,
        crew_id: int,
        user_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        将 Crew 定义编译为可序列化的结构

        执行所有数据库查询、变量插值和工具/知识源解析。
        """
        variables = variables or {}
        session = self.db.get_session()

        try:
            crew_def = session.get(CrewDefinition, crew_id)
            if not crew_def:
                raise ValueError(f"Crew not found: {crew_id}")

            from AICrews.application.crew.variable_defaults import merge_crew_variables
            from AICrews.application.crew.system_context import (
                ensure_system_variables,
                inject_system_context_to_backstory,
            )

            # Step 1: Merge user variables with defaults
            merged_vars = merge_crew_variables(
                input_schema=crew_def.input_schema,
                default_variables=crew_def.default_variables,
                variables=variables,
            )

            # Step 2: Ensure system variables (date, timestamp, year) are present
            merged_vars = ensure_system_variables(merged_vars)

            compiled_agents = []
            compiled_tasks = []

            # 这里的逻辑与 assemble 类似，但返回的是可序列化的字典
            # 为了简化，我们按顺序处理 structure
            for entry in crew_def.structure or []:
                entry_type = entry.get("type")

                if entry_type == "router":
                    # Router 处理逻辑
                    decision_task_id = entry.get("decision_task_id")
                    if decision_task_id:
                        task_def = session.get(TaskDefinition, decision_task_id)
                        if task_def:
                            compiled_tasks.append(
                                {
                                    "type": "router_decision",
                                    "task_id": decision_task_id,
                                    "name": task_def.name,
                                    "description": self.interpolate_variables(
                                        task_def.description, merged_vars
                                    ),
                                    "expected_output": self.interpolate_variables(
                                        task_def.expected_output, merged_vars
                                    ),
                                    "async_execution": task_def.async_execution,
                                }
                            )
                    continue

                if entry_type == "summary":
                    # Summary 处理逻辑
                    summary_task_id = entry.get("task_id")
                    reporter_agent_id = entry.get("reporter_agent_id")

                    # 如果有 Reporter Agent，编译它
                    if reporter_agent_id:
                        reporter_def = session.get(AgentDefinition, reporter_agent_id)
                        if reporter_def:
                            # 检查是否已编译过
                            existing_ids = [a["agent_id"] for a in compiled_agents]
                            if reporter_agent_id not in existing_ids:
                                compiled_agents.append(
                                    {
                                        "agent_id": reporter_agent_id,
                                        "name": reporter_def.name,
                                        "role": reporter_def.role,
                                        "goal": self.interpolate_variables(
                                            reporter_def.goal, merged_vars
                                        ),
                                        "backstory": inject_system_context_to_backstory(
                                            self.interpolate_variables(
                                                reporter_def.backstory, merged_vars
                                            ),
                                            merged_vars,
                                            position="prepend"
                                        ),
                                        "llm_config": reporter_def.llm_config,
                                        "tool_ids": [],
                                        "loadout_data": reporter_def.loadout_data,
                                        "knowledge_source_ids": [],
                                        "verbose": reporter_def.verbose,
                                        "allow_delegation": reporter_def.allow_delegation,
                                        "memory_policy": reporter_def.memory_policy or "run_only",
                                        "mcp_server_ids": [],
                                        "is_reporter": True,  # 标记为 Reporter Agent
                                    }
                                )

                    if summary_task_id:
                        task_def = session.get(TaskDefinition, summary_task_id)
                        if task_def:
                            compiled_tasks.append(
                                {
                                    "type": "summary",
                                    "task_id": summary_task_id,
                                    "agent_id": reporter_agent_id,  # 显式分配 Reporter Agent
                                    "name": task_def.name,
                                    "description": self.interpolate_variables(
                                        task_def.description, merged_vars
                                    ),
                                    "expected_output": self.interpolate_variables(
                                        task_def.expected_output, merged_vars
                                    ),
                                    "context_task_ids": entry.get(
                                        "context_task_ids", []
                                    ),
                                    "async_execution": task_def.async_execution,
                                }
                            )
                    continue

                # 普通 Agent 节点
                agent_id = entry.get("agent_id")
                task_ids = entry.get("tasks", [])

                if not agent_id:
                    continue

                agent_def = session.get(AgentDefinition, agent_id)
                if not agent_def:
                    continue

                # 获取知识源
                ks_ids = (
                    entry.get("knowledge_source_ids") or agent_def.knowledge_source_ids
                )

                # 获取工具配置 (支持新旧两种格式)
                tool_ids = []
                loadout_data = None

                if agent_def.loadout_data:
                    loadout = agent_def.loadout_data
                    # 新格式: skill_keys (Task 1.5)
                    if "skill_keys" in loadout:
                        loadout_data = loadout  # Pass through for WrapperFactory
                    else:
                        # 旧格式: 4-Tier (data_tools, quant_tools, etc.)
                        for tier_key in [
                            "data_tools",
                            "quant_tools",
                            "external_tools",
                            "strategies",
                        ]:
                            tool_ids.extend(loadout.get(tier_key, []))
                elif agent_def.tool_ids:
                    tool_ids.extend([str(t) for t in agent_def.tool_ids])

                compiled_agent = {
                    "agent_id": agent_id,
                    "name": agent_def.name,
                    "role": agent_def.role,
                    "goal": self.interpolate_variables(agent_def.goal, merged_vars),
                    "backstory": inject_system_context_to_backstory(
                        self.interpolate_variables(agent_def.backstory, merged_vars),
                        merged_vars,
                        position="prepend"
                    ),
                    "llm_config": agent_def.llm_config,
                    "tool_ids": tool_ids,
                    "loadout_data": loadout_data,  # New: pass skill_keys loadout
                    "knowledge_source_ids": ks_ids,
                    "verbose": agent_def.verbose,
                    "allow_delegation": agent_def.allow_delegation,
                    "memory_policy": agent_def.memory_policy or "run_only",
                    "mcp_server_ids": agent_def.mcp_server_ids
                    if not agent_def.loadout_data
                    else [],
                }
                compiled_agents.append(compiled_agent)

                # Get router_condition from structure entry (if present)
                router_condition = entry.get("router_condition")

                for tid in task_ids:
                    task_def = session.get(TaskDefinition, tid)
                    if task_def:
                        # Interpolate description
                        description = self.interpolate_variables(
                            task_def.description, merged_vars
                        )

                        # Apply router condition wrapper at runtime (not persisted)
                        if router_condition:
                            description = self._wrap_router_condition(
                                description, router_condition
                            )

                        compiled_tasks.append(
                            {
                                "type": "agent_task",
                                "task_id": tid,
                                "agent_id": agent_id,
                                "name": task_def.name,
                                "description": description,
                                "expected_output": self.interpolate_variables(
                                    task_def.expected_output, merged_vars
                                ),
                                "context_task_ids": task_def.context_task_ids or [],
                                "async_execution": task_def.async_execution,
                                # Task Output Spec fields
                                "output_mode": getattr(task_def, "output_mode", "raw") or "raw",
                                "output_schema_key": getattr(task_def, "output_schema_key", None),
                                "guardrail_keys": getattr(task_def, "guardrail_keys", []) or [],
                                "guardrail_max_retries": getattr(task_def, "guardrail_max_retries", 3) or 3,
                                "strict_mode": getattr(task_def, "strict_mode", False) or False,
                            }
                        )

            return {
                "crew_id": crew_id,
                "name": crew_def.name,
                "process": crew_def.process,
                "memory_enabled": crew_def.memory_enabled,
                "memory_policy": crew_def.memory_policy or "run_only",
                "verbose": crew_def.verbose,
                "cache_enabled": crew_def.cache_enabled,
                "manager_llm_config": crew_def.manager_llm_config,
                "agents": compiled_agents,
                "tasks": compiled_tasks,
                "variables": merged_vars,  # Include merged variables for runtime builder
                "compiled_at": datetime.now().isoformat(),
            }

        finally:
            session.close()

    def instantiate(
        self,
        compiled_data: Dict[str, Any],
        job_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Crew:
        """
        从编译后的数据实例化 CrewAI 对象
        """
        # 🔧 清理可能导致 LLM 调用失败的环境变量
        # 只允许使用用户数据库中的配置，不依赖任何环境变量
        env_vars_to_clean = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_GEMINI_API_KEY",
            "DEEPSEEK_API_KEY",
            "QIANWEN_API_KEY",
            "VOLCENGINE_API_KEY",
        ]
        for var in env_vars_to_clean:
            if os.getenv(var):
                logger.debug(f"Cleaning environment variable: {var}")
                os.environ.pop(var, None)

        agents_map = {}
        agents_list = []
        tasks_list = []
        task_map = {}

        session = self.db.get_session()
        knowledge_loader = KnowledgeLoader(session, user_id=user_id)

        from AICrews.application.crew.run_context import get_current_run_context

        run_context = get_current_run_context()
        runtime_limits = (
            getattr(run_context, "runtime_limits", None) if run_context else None
        )

        policy_llm = None
        if user_id is not None:
            try:
                if run_context is not None:
                    policy_llm = create_llm_from_run_context(
                        run_context=run_context, user_id=user_id, db=session
                    )
            except LLMKeyProvisioningError:
                # Re-raise provisioning errors - caller should retry
                raise
            except Exception:
                logger.warning(
                    "Failed to resolve policy LLM; falling back to per-agent LLM configs",
                    exc_info=True,
                )

        memory_enabled = bool(compiled_data.get("memory_enabled"))
        embedder_config = {"provider": "onnx", "config": {}} if memory_enabled else None

        # Track all provider keys used by agents for memory gate check
        agent_provider_keys: List[str] = []

        try:
            # 1. 实例化 Agents
            for a_data in compiled_data["agents"]:
                # 获取 LLM
                llm_cfg = a_data["llm_config"] or {}

                if policy_llm is not None:
                    llm = policy_llm
                    llm_resolved = None
                    # System LLM: admin-configured, no capability check needed
                    # provider_key is only used for BYOK capability checks
                    provider_key = None
                else:
                    # LLM 解析优先级:
                    # 1. user_model_config_id (BYOK 用户显式绑定)
                    # 2. llm_tier + 系统环境变量 (FAIC_LLM_AGENTS_{TIER}_*)
                    # 3. 系统默认 (FAIC_LLM_AGENTS_FAST_*)
                    user_model_config_id = llm_cfg.get("user_model_config_id")

                    if user_model_config_id:
                        # BYOK: 使用用户绑定的模型配置
                        user_model_config = self.llm_manager.get_model_config(
                            session, user_model_config_id
                        )
                        if not user_model_config:
                            raise ValueError(
                                f"User model config {user_model_config_id} not found for agent '{a_data['name']}'."
                            )

                        from AICrews.llm.runtime import get_llm_runtime

                        runtime = get_llm_runtime()
                        llm, llm_resolved = runtime.create_llm(user_model_config)
                        provider_key = (
                            getattr(llm_resolved, "provider_key", None) or "unknown"
                        ).lower()
                    else:
                        # 系统默认: 从环境变量读取 LLM 配置
                        from AICrews.llm.system_config import get_system_llm_config_store
                        from AICrews.schemas.llm_policy import LLMScope
                        from crewai import LLM

                        llm_tier = llm_cfg.get("llm_tier", "agents_fast")
                        tier_scope_map = {
                            "fast": LLMScope.AGENTS_FAST,
                            "agents_fast": LLMScope.AGENTS_FAST,
                            "balanced": LLMScope.AGENTS_BALANCED,
                            "agents_balanced": LLMScope.AGENTS_BALANCED,
                            "best": LLMScope.AGENTS_BEST,
                            "agents_best": LLMScope.AGENTS_BEST,
                        }
                        scope = tier_scope_map.get(llm_tier, LLMScope.AGENTS_FAST)

                        try:
                            system_store = get_system_llm_config_store()
                            sys_cfg = system_store.get_config(scope)

                            llm = LLM(
                                model=sys_cfg.model,
                                api_key=sys_cfg.api_key,
                                base_url=sys_cfg.base_url,
                                temperature=sys_cfg.temperature,
                            )
                            llm_resolved = None
                            provider_key = sys_cfg.provider
                            logger.info(
                                f"Agent '{a_data['name']}' using system LLM: "
                                f"provider={sys_cfg.provider}, model={sys_cfg.model}, tier={scope.value}"
                            )
                        except ValueError as e:
                            raise ValueError(
                                f"Agent '{a_data['name']}' has no LLM binding and system default is not configured. "
                                f"Set FAIC_LLM_AGENTS_FAST_PROVIDER/MODEL/API_KEY environment variables. "
                                f"Error: {e}"
                            )

                # Collect provider key for memory gate check
                if provider_key:
                    agent_provider_keys.append(provider_key)

                # 加载工具 (支持新旧两种格式)
                tools = []
                mcps = []

                # 新格式: 使用 LoadoutResolver (unified resolution)
                if a_data.get("loadout_data") and "skill_keys" in a_data["loadout_data"]:
                    from AICrews.services.loadout_resolver import LoadoutResolver

                    skill_keys = a_data["loadout_data"]["skill_keys"]
                    resolver = LoadoutResolver(session, user_id=user_id)
                    loadout_resolved = resolver.get_resolved_loadout(skill_keys)

                    tools = loadout_resolved["tools"]  # Builtin tools (BaseTool instances)

                    # Convert MCP configs to CrewAI MCP format
                    if loadout_resolved["mcps"]:
                        from AICrews.config.mcp import get_native_mcp_loader
                        loader = get_native_mcp_loader()
                        for mcp_cfg in loadout_resolved["mcps"]:
                            try:
                                # Use create_for_agent with single server
                                mcp_instances = loader.create_for_agent(
                                    server_ids=[mcp_cfg["server_key"]],
                                    tool_filter=mcp_cfg.get("tool_filter"),
                                )
                                if mcp_instances:
                                    mcps.extend(mcp_instances)
                            except Exception as e:
                                logger.warning(f"Failed to create MCP instance for {mcp_cfg['server_key']}: {e}")

                    if loadout_resolved["failed"]:
                        logger.warning(
                            f"Failed to resolve capabilities for agent {a_data['name']}: "
                            f"{loadout_resolved['failed']}"
                        )

                # 旧格式: 使用 ToolRegistry
                elif a_data.get("tool_ids"):
                    from AICrews.tools.registry.tool_registry import ToolRegistry

                    registry = ToolRegistry(db=session)
                    raw_tools = registry.get_tools_by_namespaced_ids(
                        a_data["tool_ids"], user_id=user_id
                    )
                    tools = list(raw_tools or [])
                if tools:
                    from AICrews.llm.services.compatibility_service import (
                        get_compatibility_service,
                    )

                    model_key = (
                        getattr(llm_resolved, "model_key", None)
                        or getattr(llm, "model", None)
                        or llm_cfg.get("model")
                        or "unknown"
                    )
                    provider_key_for_check = (
                        provider_key
                        or getattr(llm_resolved, "provider_key", None)
                        or llm_cfg.get("provider_key")
                        or "unknown"
                    )

                    compat_service = get_compatibility_service()
                    compat_result = compat_service.validate_agent_llm_compatibility(
                        agent_name=a_data.get("name") or a_data.get("role") or "Agent",
                        provider_key=provider_key_for_check,
                        model_key=model_key,
                        has_tools=True,
                        strict_mode=False,
                    )
                    if not compat_result.get("can_proceed", True):
                        raise ValueError(
                            f"Agent '{a_data.get('name')}' LLM compatibility check failed: "
                            f"{'; '.join(compat_result.get('errors') or [])}"
                        )

                    preregistrar = getattr(self, "_tool_preregistrar", None)
                    if preregistrar is not None:
                        tools = preregistrar.preregister(
                            tools,
                            cache_key_prefix=str(a_data.get("name") or "agent"),
                            wrap_tool=lambda t: t,
                        )

                # 加载知识
                knowledge = []
                if a_data["knowledge_source_ids"]:
                    knowledge = knowledge_loader.load_by_ids(
                        a_data["knowledge_source_ids"]
                    )

                # 加载 CrewAI 原生 MCP（v2 迁移 - legacy mcp_server_ids）
                # Note: mcps list is already initialized during LoadoutResolver or legacy tool handling
                if a_data.get("mcp_server_ids"):
                    try:
                        from AICrews.config.mcp import get_native_mcp_loader

                        legacy_mcps = get_native_mcp_loader().create_for_agent(
                            server_ids=a_data["mcp_server_ids"],
                            tool_filter=a_data.get("mcp_tool_filter"),
                            db_session=session,
                        )
                        if legacy_mcps:
                            mcps.extend(legacy_mcps)
                    except Exception as e:
                        logger.warning(f"Failed to load legacy MCP servers: {e}")

                # 设置回调
                step_callback = None
                if job_id:
                    from AICrews.services.tracking_service import TrackingService
                    from AICrews.schemas.stats import AgentActivityEvent

                    agent_name = a_data["name"]

                    def on_step(step, *, _agent_name: str = agent_name):
                        tracker = TrackingService()
                        msg = step.thought if hasattr(step, "thought") else str(step)
                        tracker.add_activity(
                            job_id,
                            AgentActivityEvent(
                                agent_name=_agent_name,
                                activity_type="step",
                                message=msg,
                                timestamp=datetime.now(),
                            ),
                        )
                        # Tool usage is tracked via CrewAI EventBus listeners.
                        # Avoid inferring "success" from step objects (no duration/result/error),
                        # which can distort tool metrics and run summaries.
                        if hasattr(step, "tool"):
                            tracker.add_activity(
                                job_id,
                                AgentActivityEvent(
                                    agent_name=_agent_name,
                                    activity_type="tool_step",
                                    message=f"Tool step: {getattr(step, 'tool', 'unknown')}",
                                    details={"args": getattr(step, "tool_input", None)},
                                    timestamp=datetime.now(),
                                ),
                            )

                    step_callback = on_step

                agent_kwargs = {
                    "role": a_data["role"],
                    "goal": a_data["goal"],
                    "backstory": a_data["backstory"],
                    "tools": tools,
                    "mcps": mcps if mcps else None,
                    "llm": llm,
                    "knowledge_sources": knowledge if knowledge else None,
                    "verbose": a_data["verbose"],
                    "allow_delegation": a_data["allow_delegation"],
                    "memory": a_data.get("memory_policy") != "disabled",
                    "step_callback": step_callback,
                }
                if runtime_limits is not None:
                    agent_kwargs["max_iter"] = runtime_limits.max_iterations
                    agent_kwargs["max_execution_time"] = runtime_limits.timeout_seconds

                agent = Agent(**agent_kwargs)
                agents_map[a_data["agent_id"]] = agent
                agents_list.append(agent)

            # 2. 实例化 Tasks
            # 如果没有 agents 但有 tasks (例如只有 summary 任务的 Crew)，创建一个默认 Reporter agent
            if not agents_list and compiled_data.get("tasks"):
                # 使用 policy_llm，若无则抛出明确错误
                if policy_llm is None:
                    raise ValueError(
                        "No agents configured and no policy LLM available. "
                        "Please configure at least one agent or set a crew-level LLM policy."
                    )

                reporter_kwargs = {
                    "role": "Reporter",
                    "goal": "Generate comprehensive reports",
                    "backstory": "You are an expert report generator.",
                    "llm": policy_llm,
                    "verbose": True,
                    "allow_delegation": False,
                    "memory": False,
                }
                if runtime_limits is not None:
                    reporter_kwargs["max_iter"] = runtime_limits.max_iterations
                    reporter_kwargs["max_execution_time"] = runtime_limits.timeout_seconds

                reporter = Agent(**reporter_kwargs)
                agents_map[None] = reporter
                agents_list.append(reporter)

            for t_data in compiled_data["tasks"]:
                target_agent = None
                if t_data["type"] == "agent_task":
                    target_agent = agents_map.get(t_data["agent_id"])
                elif t_data["type"] == "summary":
                    # Summary Task: 优先使用显式分配的 Reporter Agent
                    reporter_agent_id = t_data.get("agent_id")
                    if reporter_agent_id:
                        target_agent = agents_map.get(reporter_agent_id)
                    else:
                        # 向后兼容: 旧 Crew 使用最后一个 Agent
                        target_agent = agents_list[-1] if agents_list else None
                else:
                    # Router 使用列表最后一个 Agent
                    target_agent = agents_list[-1] if agents_list else None

                if not target_agent:
                    continue

                # 解析依赖
                context = [
                    task_map[tid]
                    for tid in t_data.get("context_task_ids", [])
                    if tid in task_map
                ]

                # Build Task kwargs with output spec (structured output + guardrails)
                compiled_variables = compiled_data.get("variables", {})

                # Get provider capabilities from agent's LLM config
                agent_data = next(
                    (a for a in compiled_data["agents"] if a["agent_id"] == t_data.get("agent_id")),
                    {}
                )
                llm_cfg = agent_data.get("llm_config", {}) or {}
                provider_key = llm_cfg.get("provider_key", "")
                model_name = llm_cfg.get("model", "")
                provider_caps = get_provider_capabilities(provider_key, model_name)

                # Build structured output kwargs
                output_kwargs = build_task_kwargs(
                    t_data=t_data,
                    compiled_variables=compiled_variables,
                    provider_capabilities=provider_caps,
                )

                # Extract diagnostics for tracking (don't pass to Task)
                task_diagnostics = output_kwargs.pop("_diagnostics", {})
                if task_diagnostics.get("degraded"):
                    logger.info(
                        f"Task '{t_data.get('name', t_data['task_id'])}' output mode "
                        f"degraded: {task_diagnostics.get('warnings', [])}"
                    )

                # Build callback with TASK_OUTPUT event emission
                callback = None
                if job_id:
                    callback = build_task_output_callback(
                        job_id=job_id,
                        task_id=str(t_data.get("task_id", "")),
                        agent_name=target_agent.role,
                        task_description=t_data["description"],
                        diagnostics=task_diagnostics,
                    )

                task = Task(
                    description=t_data["description"],
                    expected_output=t_data["expected_output"],
                    agent=target_agent,
                    context=context,
                    async_execution=t_data["async_execution"],
                    callback=callback,
                    **output_kwargs,  # Include guardrails, output_pydantic, etc.
                )
                tasks_list.append(task)
                task_map[t_data["task_id"]] = task

            # 3. 创建 Crew
            process = (
                Process.hierarchical
                if compiled_data["process"] == "hierarchical"
                else Process.sequential
            )

            # Prepare Manager LLM if hierarchical
            manager_llm = None
            if process == Process.hierarchical:
                if policy_llm is not None:
                    manager_llm = policy_llm
                else:
                    mgr_cfg = compiled_data.get("manager_llm_config") or {}
                    user_model_config_id = mgr_cfg.get("user_model_config_id")

                    if user_model_config_id:
                        user_model_config = self.llm_manager.get_model_config(
                            session, user_model_config_id
                        )
                        if user_model_config:
                            from AICrews.llm.runtime import get_llm_runtime

                            runtime = get_llm_runtime()
                            manager_llm, _resolved = runtime.create_llm(user_model_config)

                # Fallback: Use first agent's LLM if no specific manager config
                if not manager_llm and agents_list:
                    logger.info(
                        "No specific Manager LLM configured. Reusing first agent's LLM for Manager."
                    )
                    manager_llm = agents_list[0].llm

                if not manager_llm:
                    raise ValueError(
                        "Hierarchical process requires a Manager LLM, but none could be configured."
                    )

            # Configure Embedder if memory is enabled
            # 使用本地 ONNX embedding，不依赖任何外部 API
            memory_requested = (
                compiled_data["memory_enabled"]
                and compiled_data.get("memory_policy") != "disabled"
            )

            # Safety check: verify embedder availability before enabling memory
            memory_enabled = False
            embedder_config = None
            if memory_requested:
                # Check 1: Embedder availability (onnxruntime, chromadb)
                embedder_available, embedder_error = check_embedder_availability()
                if not embedder_available:
                    # Gracefully degrade: disable memory but continue execution
                    logger.warning(
                        f"Crew memory requested but embedder unavailable: {embedder_error}. "
                        f"Continuing without memory. To enable memory, ensure onnxruntime "
                        f"and chromadb packages are installed."
                    )
                else:
                    # Check 2: Provider json_schema support (for LTM Pydantic models)
                    # CrewAI's long-term memory uses Pydantic models that require json_schema
                    is_system_llm = policy_llm is not None

                    if is_system_llm:
                        # System LLM: admin-configured, trust that it supports json_schema
                        # Skip capability check - admin is responsible for correct configuration
                        memory_enabled = True
                        embedder_config = {"provider": "onnx", "config": {}}
                        logger.info(
                            "Memory enabled for System LLM (admin-configured, skipping capability check)"
                        )
                    else:
                        # BYOK: check all agent providers for json_schema support
                        # Use conservative strategy: ALL providers must support json_schema
                        providers_to_check = list(set(agent_provider_keys)) if agent_provider_keys else []

                        all_support_json_schema = bool(providers_to_check)  # False if empty
                        unsupported_providers = []
                        for pkey in providers_to_check:
                            provider_caps = get_provider_capabilities(pkey)
                            if not provider_caps.get("supports_json_schema", False):
                                all_support_json_schema = False
                                unsupported_providers.append(pkey)

                        # Allow override via environment variable
                        force_memory = os.getenv("FAIC_FORCE_MEMORY_ON_UNSUPPORTED_LLM", "").lower() in (
                            "true", "1", "yes"
                        )

                        if all_support_json_schema or force_memory:
                            memory_enabled = True
                            embedder_config = {"provider": "onnx", "config": {}}
                            if force_memory and not all_support_json_schema:
                                logger.warning(
                                    f"Memory enabled via FAIC_FORCE_MEMORY_ON_UNSUPPORTED_LLM "
                                    f"despite BYOK providers {unsupported_providers} lacking json_schema support. "
                                    f"Long-term memory operations may fail."
                                )
                        else:
                            # BYOK provider doesn't support json_schema - disable memory
                            logger.warning(
                                f"Crew memory disabled: BYOK providers {unsupported_providers or providers_to_check or ['unknown']} "
                                f"do not support json_schema (required for long-term memory). Set "
                                f"FAIC_FORCE_MEMORY_ON_UNSUPPORTED_LLM=true to override."
                            )

            crew_params = {
                "agents": agents_list,
                "tasks": tasks_list,
                "process": process,
                "memory": memory_enabled,
                "verbose": True,
                "cache": compiled_data["cache_enabled"],
                "output_log_file": False,
            }

            if manager_llm:
                crew_params["manager_llm"] = manager_llm

            if embedder_config:
                crew_params["embedder"] = embedder_config

            return Crew(**crew_params)
        finally:
            session.close()

    def assemble(
        self,
        crew_id: int,
        user_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
        skip_preflight: bool = False,
    ) -> Tuple[Crew, PreflightResult]:
        """
        组装 Crew (支持缓存)
        """
        variables = variables or {}

        compiled_data, cache_source, preflight = self._get_or_compile_compiled_data(
            crew_id, user_id, variables, skip_preflight=skip_preflight
        )
        if not preflight.success:
            raise ValueError(f"Preflight check failed: {preflight.errors}")

        if cache_source in {"redis", "memory"}:
            logger.info(
                f"Cache hit for crew {crew_id} (compiled at {compiled_data.get('compiled_at')})"
            )
        else:
            logger.info(f"Cache miss for crew {crew_id}. Compiling...")

        crew = self.instantiate(compiled_data, job_id=job_id, user_id=user_id)
        return crew, preflight

    def _get_executor_mode(self) -> str:
        try:
            settings = get_settings()
            return (getattr(settings, "execution", None).executor_mode or "legacy").strip().lower()  # type: ignore[union-attr]
        except Exception:
            return os.getenv("FAIC_EXECUTOR_MODE", "legacy").strip().lower()

    def _get_or_compile_compiled_data(
        self,
        crew_id: int,
        user_id: Optional[int],
        variables: Dict[str, Any],
        *,
        skip_preflight: bool,
    ) -> Tuple[Dict[str, Any], str, PreflightResult]:
        variables = variables or {}

        if not skip_preflight:
            preflight = self.preflight_check(crew_id, user_id, variables)
            if not preflight.success:
                raise ValueError(f"Preflight check failed: {preflight.errors}")
        else:
            preflight = PreflightResult(success=True)

        key = self._get_cache_key(crew_id, user_id, variables)
        compiled_data = None
        cache_source = "none"

        cache_mgr = getattr(self, "_cache_manager", None)
        try:
            if cache_mgr is not None and hasattr(cache_mgr, "get_json_sync"):
                compiled_data = cache_mgr.get_json_sync(key, layer="redis")
            else:
                compiled_data = self.redis.get_json_sync(key)
            if compiled_data:
                cache_source = "redis"
        except Exception:
            compiled_data = None

        if not compiled_data:
            compiled_data = self._memory_cache.get(key)
            if compiled_data:
                cache_source = "memory"

        if not compiled_data:
            compiled_data = self.compile(crew_id, user_id, variables)
            cached = False
            try:
                if cache_mgr is not None and hasattr(cache_mgr, "set_json_sync"):
                    cached = bool(cache_mgr.set_json_sync(key, compiled_data, ttl=1800, layer="redis"))
                else:
                    cached = bool(self.redis.set_sync(key, compiled_data, ttl=1800, json_encode=True))
            except Exception:
                cached = False
            self._memory_cache[key] = compiled_data
            cache_source = "redis+memory" if cached else "memory-only"

        return compiled_data, cache_source, preflight

    def _build_execution_graph(self, crew_id: int, user_id: Optional[int]) -> Any:
        session = self.db.get_session()
        try:
            crew_def = session.get(CrewDefinition, crew_id)
            if not crew_def:
                raise ValueError(f"Crew not found: {crew_id}")

            router_cfg = crew_def.router_config or {}
            output_cfg = (
                router_cfg.get("output_config") if isinstance(router_cfg, dict) else None
            )
            from AICrews.application.crew.lightweight_compiler import LightweightCompiler

            compiler = LightweightCompiler()
            return compiler.compile_from_compilation_result(
                structure=crew_def.structure or [],
                input_schema=getattr(crew_def, "input_schema", None) or {},
                output_config=output_cfg or {},
                warnings=[],
            )
        finally:
            session.close()

    def run(
        self,
        *,
        crew_id: int,
        user_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
        skip_preflight: bool = False,
    ) -> Tuple[Any, PreflightResult]:
        variables = variables or {}
        if "date" not in variables:
            variables["date"] = datetime.now().strftime("%Y-%m-%d")

        mode = self._get_executor_mode()
        compiled_data, _cache_source, preflight = self._get_or_compile_compiled_data(
            crew_id, user_id, variables, skip_preflight=skip_preflight
        )

        if mode == "runtime_executor":
            from AICrews.execution.runtime_executor import RuntimeExecutor
            import inspect

            graph = self._build_execution_graph(crew_id, user_id)
            executor = RuntimeExecutor()
            result = executor.execute(
                graph,
                variables=variables,
                user_id=user_id,
                crew_id=crew_id,
                job_id=job_id,
                compiled_data=compiled_data,
                instantiate_fn=self.instantiate,
            )
            if inspect.isawaitable(result):
                result = asyncio.run(result)
            return result, preflight

        crew = self.instantiate(compiled_data, job_id=job_id, user_id=user_id)
        return crew.kickoff(), preflight

    def save_version(
        self,
        crew_id: int,
        description: Optional[str] = None,
    ) -> CrewVersion:
        """保存 Crew 配置版本 (委托给 VersionManager)"""
        session = self.db.get_session()
        try:
            return self.version_manager.save_version(session, crew_id, description)
        finally:
            session.close()

    def restore_version(
        self,
        crew_id: int,
        version_number: int,
    ) -> CrewDefinition:
        """恢复到指定版本 (委托给 VersionManager)"""
        session = self.db.get_session()
        try:
            return self.version_manager.restore_version(
                session, crew_id, version_number
            )
        finally:
            session.close()

    def list_versions(self, crew_id: int) -> List[Dict[str, Any]]:
        """列出所有版本 (委托给 VersionManager)"""
        session = self.db.get_session()
        try:
            return self.version_manager.list_versions(session, crew_id)
        finally:
            session.close()

    def clone_crew(
        self,
        crew_id: int,
        user_id: int,
        new_name: Optional[str] = None,
    ) -> CrewDefinition:
        """克隆 Crew 配置 (委托给 VersionManager)"""
        session = self.db.get_session()
        try:
            return self.version_manager.clone_crew(session, crew_id, user_id, new_name)
        finally:
            session.close()

    def preflight_check(
        self,
        crew_id: int,
        user_id: Optional[int],
        variables: Optional[Dict[str, Any]] = None,
    ) -> PreflightResult:
        """
        运行前预检

        Args:
            crew_id: Crew 定义 ID
            user_id: 用户 ID
            variables: 运行时变量

        Returns:
            PreflightResult: 预检结果
        """
        variables = variables or {}
        session = self.db.get_session()

        try:
            crew_def = session.get(CrewDefinition, crew_id)
            if not crew_def:
                return PreflightResult(
                    success=False, errors=[f"Crew not found: {crew_id}"]
                )

            return self.validator.validate(
                crew_def=crew_def, user_id=user_id, variables=variables, session=session
            )
        finally:
            session.close()

    def extract_required_variables(self, crew_id: int) -> List[Dict[str, Any]]:
        """提取 Crew 需要的所有变量 (委托给 Validator)"""
        session = self.db.get_session()
        try:
            crew_def = session.get(CrewDefinition, crew_id)
            if not crew_def:
                return []

            variables = self.validator._extract_variables(crew_def, session)
            from AICrews.application.crew.variable_defaults import merge_crew_variables

            defaults = merge_crew_variables(
                input_schema=crew_def.input_schema,
                default_variables=crew_def.default_variables,
                variables={},
            )

            return [
                {
                    "name": var,
                    "default": defaults.get(var),
                    "required": var not in defaults,
                }
                for var in sorted(variables)
            ]
        finally:
            session.close()


# 单例
_assembler: Optional[CrewAssembler] = None


def get_crew_assembler() -> CrewAssembler:
    """获取 CrewAssembler 单例"""
    global _assembler
    if _assembler is None:
        _assembler = CrewAssembler()
    return _assembler
