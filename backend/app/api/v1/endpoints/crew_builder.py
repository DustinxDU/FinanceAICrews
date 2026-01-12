"""
Crew Builder API v2 - 完整的 Crew 构建系统 API

支持:
1. Agent/Task/Crew 的 CRUD 操作 (基于数据库)
2. 模板克隆
3. 版本控制
4. 运行时变量提取
5. 预检验证

Entitlements:
- CRUD operations (create/update/delete) require EDIT_CUSTOM_CREW action
- Run endpoint distinguishes between official crew (RUN_OFFICIAL_CREW) and custom crew (RUN_CUSTOM_CREW)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from AICrews.database.models import (AgentDefinition, CrewDefinition,
                                     TaskDefinition, User)
from AICrews.schemas.analysis import JobStatusResponse, RunSummary
from AICrews.schemas.task_definition import (
    TaskDefinitionCreate,
    TaskDefinitionUpdate,
    TaskDefinitionResponse,
)
from AICrews.schemas.crew import (
    AgentDefinitionCreate,
    AgentDefinitionUpdate,
    AgentDefinitionResponse,
    CrewStructureEntry,
    CrewDefinitionCreate,
    CrewDefinitionUpdate,
    CrewDefinitionResponse,
    CrewVersionResponse,
    VariableInfo,
    PreflightResponse,
    CloneRequest,
    SaveVersionRequest,
    RunCrewRequest,
    RunCrewResponse,
)
from AICrews.schemas.entitlements import PolicyAction
from backend.app.security import (get_current_user, get_current_user_optional,
                                  get_db)
from backend.app.api.v1.utils.entitlements_http import require_entitlement

logger = logging.getLogger(__name__)

# Redis 缓存客户端
redis_client: Optional[redis.Redis] = None
REDIS_AVAILABLE: Optional[bool] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Lazy initialize Redis client.

    IMPORTANT: Do not perform external I/O at import time.
    """
    global redis_client, REDIS_AVAILABLE
    if REDIS_AVAILABLE is False:
        return None
    if redis_client is not None:
        return redis_client
    try:
        client = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        client.ping()
        redis_client = client
        REDIS_AVAILABLE = True
        logger.info("Redis cache connected")
        return redis_client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        REDIS_AVAILABLE = False
        logger.warning(f"Redis not available: {e}. Tool caching disabled.")
        return None

# 缓存配置
CACHE_TTL_SECONDS = 300  # 5分钟缓存
CACHE_PREFIX = "crew_builder:tiered_tools:"


def get_crew_assembler():
    """Lazy import of crew assembler to avoid circular imports"""
    from AICrews.application.crew.assembler import \
        get_crew_assembler as _get_crew_assembler

    return _get_crew_assembler()


def get_preflight_result_class():
    """Lazy import of PreflightResult class"""
    from AICrews.application.crew.preflight import PreflightResult

    return PreflightResult


router = APIRouter(prefix="/crew-builder", tags=["Crew Builder v2"])


# ============================================
# Agent Definition CRUD
# ============================================


@router.get("/agents", summary="列出 Agent 定义")
async def list_agent_definitions(
    include_templates: bool = Query(True, description="是否包含系统模板"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> List[AgentDefinitionResponse]:
    """列出用户的 Agent 定义和系统模板"""
    query = db.query(AgentDefinition).filter(AgentDefinition.is_active == True)

    if current_user:
        if include_templates:
            query = query.filter(
                (AgentDefinition.user_id == current_user.id)
                | (AgentDefinition.is_template == True)
            )
        else:
            query = query.filter(AgentDefinition.user_id == current_user.id)
    else:
        query = query.filter(AgentDefinition.is_template == True)

    agents = query.order_by(AgentDefinition.created_at.desc()).all()
    return [AgentDefinitionResponse.model_validate(a) for a in agents]


@router.post("/agents", summary="创建 Agent 定义")
async def create_agent_definition(
    http_request: Request,
    body: AgentDefinitionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentDefinitionResponse:
    """创建新的 Agent 定义

    Entitlements: Requires EDIT_CUSTOM_CREW action (Pro tier)
    """
    # Entitlements gate
    require_entitlement(
        action=PolicyAction.EDIT_CUSTOM_CREW,
        request=http_request,
        db=db,
        current_user=current_user,
    )

    agent = AgentDefinition(
        user_id=current_user.id,
        name=body.name,
        role=body.role,
        goal=body.goal,
        backstory=body.backstory,
        llm_config=body.llm_config,
        allow_delegation=body.allow_delegation,
        verbose=body.verbose,
        is_template=body.is_template,
        is_active=True,
    )

    # 设置可选字段
    if hasattr(agent, "description"):
        agent.description = body.description
    if hasattr(agent, "tool_ids"):
        agent.tool_ids = body.tool_ids
    if hasattr(agent, "knowledge_source_ids"):
        agent.knowledge_source_ids = body.knowledge_source_ids
    if hasattr(agent, "mcp_server_ids"):
        agent.mcp_server_ids = body.mcp_server_ids

    # 支持直接传入 loadout_data 或从 skill_keys 构建
    if hasattr(agent, "loadout_data"):
        if body.loadout_data:
             # 直接使用前端传入的 loadout_data
             agent.loadout_data = body.loadout_data
        elif hasattr(body, "skill_keys") and body.skill_keys:
             # 从 skill_keys 构建标准 loadout
             # (这里需要 Pydantic 模型支持 skill_keys 字段)
             pass


    db.add(agent)
    db.commit()
    db.refresh(agent)

    return AgentDefinitionResponse.model_validate(agent)


@router.get("/agents/{agent_id}", summary="获取 Agent 定义")
async def get_agent_definition(
    agent_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> AgentDefinitionResponse:
    """获取指定 Agent 定义"""
    agent = db.get(AgentDefinition, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 权限检查
    if not agent.is_template and (not current_user or agent.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return AgentDefinitionResponse.model_validate(agent)


@router.put("/agents/{agent_id}", summary="更新 Agent 定义")
async def update_agent_definition(
    http_request: Request,
    agent_id: int,
    body: AgentDefinitionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentDefinitionResponse:
    """更新 Agent 定义

    Entitlements: Requires EDIT_CUSTOM_CREW action (Pro tier)
    """
    # Entitlements gate
    require_entitlement(
        action=PolicyAction.EDIT_CUSTOM_CREW,
        request=http_request,
        db=db,
        current_user=current_user,
    )

    agent = db.get(AgentDefinition, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # 更新字段
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(agent, key):
            setattr(agent, key, value)

    agent.updated_at = datetime.now()
    db.commit()
    db.refresh(agent)

    return AgentDefinitionResponse.model_validate(agent)


@router.delete("/agents/{agent_id}", summary="删除 Agent 定义")
async def delete_agent_definition(
    http_request: Request,
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """删除 Agent 定义 (软删除)

    Entitlements: Requires EDIT_CUSTOM_CREW action (Pro tier)
    """
    # Entitlements gate
    require_entitlement(
        action=PolicyAction.EDIT_CUSTOM_CREW,
        request=http_request,
        db=db,
        current_user=current_user,
    )

    agent = db.get(AgentDefinition, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    agent.is_active = False
    agent.updated_at = datetime.now()
    db.commit()

    return {"message": f"Agent {agent_id} deleted"}


# ============================================
# Task Definition CRUD
# ============================================


@router.get("/tasks", summary="列出 Task 定义")
async def list_task_definitions(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> List[TaskDefinitionResponse]:
    """列出用户的 Task 定义"""
    if not current_user:
        return []

    tasks = (
        db.query(TaskDefinition)
        .filter(
            TaskDefinition.user_id == current_user.id,
        )
        .order_by(TaskDefinition.created_at.desc())
        .all()
    )

    return [TaskDefinitionResponse.model_validate(t) for t in tasks]


@router.post("/tasks", summary="创建 Task 定义")
async def create_task_definition(
    http_request: Request,
    body: TaskDefinitionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskDefinitionResponse:
    """创建新的 Task 定义

    Entitlements: Requires EDIT_CUSTOM_CREW action (Pro tier)
    """
    # Entitlements gate
    require_entitlement(
        action=PolicyAction.EDIT_CUSTOM_CREW,
        request=http_request,
        db=db,
        current_user=current_user,
    )

    task = TaskDefinition(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        expected_output=body.expected_output,
        agent_definition_id=body.agent_definition_id,
        async_execution=body.async_execution,
        context_task_ids=body.context_task_ids,
        # Output spec fields
        output_mode=body.output_mode,
        output_schema_key=body.output_schema_key,
        guardrail_keys=body.guardrail_keys,
        guardrail_max_retries=body.guardrail_max_retries,
        strict_mode=body.strict_mode,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return TaskDefinitionResponse.model_validate(task)


@router.get("/tasks/{task_id}", summary="获取 Task 定义")
async def get_task_definition(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskDefinitionResponse:
    """获取指定 Task 定义"""
    task = db.get(TaskDefinition, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return TaskDefinitionResponse.model_validate(task)


@router.put("/tasks/{task_id}", summary="更新 Task 定义")
async def update_task_definition(
    http_request: Request,
    task_id: int,
    body: TaskDefinitionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskDefinitionResponse:
    """更新 Task 定义

    Entitlements: Requires EDIT_CUSTOM_CREW action (Pro tier)
    """
    # Entitlements gate
    require_entitlement(
        action=PolicyAction.EDIT_CUSTOM_CREW,
        request=http_request,
        db=db,
        current_user=current_user,
    )

    task = db.get(TaskDefinition, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(task, key):
            setattr(task, key, value)

    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)

    return TaskDefinitionResponse.model_validate(task)


@router.delete("/tasks/{task_id}", summary="删除 Task 定义")
async def delete_task_definition(
    http_request: Request,
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """删除 Task 定义

    Entitlements: Requires EDIT_CUSTOM_CREW action (Pro tier)
    """
    # Entitlements gate
    require_entitlement(
        action=PolicyAction.EDIT_CUSTOM_CREW,
        request=http_request,
        db=db,
        current_user=current_user,
    )

    task = db.get(TaskDefinition, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(task)
    db.commit()

    return {"message": f"Task {task_id} deleted"}


# ============================================
# Crew Definition CRUD
# ============================================


@router.get("/crews", summary="列出 Crew 定义")
async def list_crew_definitions(
    include_templates: bool = Query(True, description="是否包含系统模板"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> List[CrewDefinitionResponse]:
    """列出用户的 Crew 定义和系统模板"""
    query = db.query(CrewDefinition).filter(CrewDefinition.is_active == True)

    if current_user:
        if include_templates:
            query = query.filter(
                (CrewDefinition.user_id == current_user.id)
                | (CrewDefinition.is_template == True)
            )
        else:
            query = query.filter(CrewDefinition.user_id == current_user.id)
    else:
        query = query.filter(CrewDefinition.is_template == True)

    crews = query.order_by(CrewDefinition.created_at.desc()).all()
    return [CrewDefinitionResponse.model_validate(c) for c in crews]


@router.post("/crews", summary="创建 Crew 定义")
async def create_crew_definition(
    http_request: Request,
    body: CrewDefinitionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CrewDefinitionResponse:
    """创建新的 Crew 定义，自动编译 UI 图为可执行结构

    Entitlements: Requires EDIT_CUSTOM_CREW action (Pro tier)
    """
    # Entitlements gate
    require_entitlement(
        action=PolicyAction.EDIT_CUSTOM_CREW,
        request=http_request,
        db=db,
        current_user=current_user,
    )

    # 转换 structure (作为 fallback)
    structure = [entry.model_dump() for entry in body.structure]

    crew = CrewDefinition(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        process=body.process,
        structure=structure,
        ui_state=body.ui_state,
        input_schema=body.input_schema,
        router_config=body.router_config,
        memory_enabled=body.memory_enabled,
        cache_enabled=body.cache_enabled,
        verbose=body.verbose,
        manager_llm_config=body.manager_llm_config,
        is_template=body.is_template,
        is_active=True,
    )

    # 设置可选字段
    if hasattr(crew, "max_iter"):
        crew.max_iter = body.max_iter
    if hasattr(crew, "default_variables"):
        crew.default_variables = body.default_variables

    db.add(crew)
    db.flush()  # 获取 ID 但不提交，以便编译器可以创建关联记录

    # 【图编译器】如果有 ui_state，编译为可执行结构
    if body.ui_state:
        try:
            from AICrews.application.crew.graph_compiler import \
                compile_crew_graph

            compilation = compile_crew_graph(db, current_user.id, crew)

            if compilation.success:
                # 使用编译后的结构覆盖
                crew.structure = compilation.structure
                crew.input_schema = compilation.input_schema
                if compilation.output_config:
                    crew.router_config = {
                        **(crew.router_config or {}),
                        "output_config": compilation.output_config,
                        "router_tasks": compilation.router_tasks,
                    }
                logger.info(f"Graph compiled successfully for crew {crew.name}")
            else:
                logger.warning(
                    f"Graph compilation failed for crew {crew.name}: {', '.join(compilation.errors) if compilation.errors else 'unknown error'}"
                )
                # TODO: 可以在响应中返回警告
        except Exception as e:
            logger.error(
                f"Error compiling graph for crew {crew.name}: {e}", exc_info=True
            )
            # 继续执行，使用 raw structure

    db.commit()
    db.refresh(crew)

    return CrewDefinitionResponse.model_validate(crew)


@router.get("/crews/{crew_id}", summary="获取 Crew 定义")
async def get_crew_definition(
    crew_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> CrewDefinitionResponse:
    """获取指定 Crew 定义"""
    crew = db.get(CrewDefinition, crew_id)

    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")

    if not crew.is_template and (not current_user or crew.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return CrewDefinitionResponse.model_validate(crew)


@router.put("/crews/{crew_id}", summary="更新 Crew 定义")
async def update_crew_definition(
    http_request: Request,
    crew_id: int,
    body: CrewDefinitionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CrewDefinitionResponse:
    """更新 Crew 定义

    Entitlements: Requires EDIT_CUSTOM_CREW action (Pro tier)
    """
    # Entitlements gate
    require_entitlement(
        action=PolicyAction.EDIT_CUSTOM_CREW,
        request=http_request,
        db=db,
        current_user=current_user,
    )

    crew = db.get(CrewDefinition, crew_id)

    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")

    if crew.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # 转换 structure
    update_data = body.model_dump(exclude_unset=True)
    if "structure" in update_data and update_data["structure"]:
        update_data["structure"] = [entry.model_dump() for entry in body.structure]

    # 应用更新
    for key, value in update_data.items():
        if hasattr(crew, key):
            setattr(crew, key, value)

    # 【图编译器】如果有 ui_state 更新，重新编译
    if body.ui_state:
        try:
            from AICrews.application.crew.graph_compiler import \
                compile_crew_graph

            compilation = compile_crew_graph(db, current_user.id, crew)

            if compilation.success:
                crew.structure = compilation.structure
                crew.input_schema = compilation.input_schema
                if compilation.output_config:
                    crew.router_config = {
                        **(crew.router_config or {}),
                        "output_config": compilation.output_config,
                        "router_tasks": compilation.router_tasks,
                    }
                logger.info(f"Graph re-compiled successfully for crew {crew.name}")
        except Exception as e:
            logger.error(
                f"Error re-compiling graph for crew {crew.name}: {e}", exc_info=True
            )

    crew.updated_at = datetime.now()
    db.commit()
    db.refresh(crew)

    return CrewDefinitionResponse.model_validate(crew)


@router.delete("/crews/{crew_id}", summary="删除 Crew 定义")
async def delete_crew_definition(
    http_request: Request,
    crew_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """删除 Crew 定义 (软删除)

    Entitlements: Requires EDIT_CUSTOM_CREW action (Pro tier)
    """
    # Entitlements gate
    require_entitlement(
        action=PolicyAction.EDIT_CUSTOM_CREW,
        request=http_request,
        db=db,
        current_user=current_user,
    )

    crew = db.get(CrewDefinition, crew_id)

    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")

    if crew.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    crew.is_active = False
    crew.updated_at = datetime.now()
    db.commit()

    return {"message": f"Crew {crew_id} deleted"}


# ============================================
# Crew Execution
# ============================================


@router.post(
    "/crews/{crew_id}/run", summary="运行 Crew", response_model=RunCrewResponse
)
async def run_crew_definition(
    http_request: Request,
    crew_id: int,
    body: RunCrewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RunCrewResponse:
    """
    运行指定的 Crew 定义

    提交一个后台任务执行 Crew，返回 job_id 用于查询状态

    Entitlements:
    - Official crews (is_template=True) require RUN_OFFICIAL_CREW action (Starter+ tier)
    - Custom crews require RUN_CUSTOM_CREW action (Pro tier)
    """
    from AICrews.application.crew import get_crew_assembler
    from AICrews.infrastructure.jobs import get_job_manager

    crew = db.get(CrewDefinition, crew_id)

    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")

    if not crew.is_template and crew.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Determine action based on crew type
    if crew.user_id is None or crew.is_template:
        action = PolicyAction.RUN_OFFICIAL_CREW
    else:
        action = PolicyAction.RUN_CUSTOM_CREW

    # Entitlements gate
    decision = require_entitlement(
        action=action,
        request=http_request,
        db=db,
        current_user=current_user,
        requested_mode=body.variables.get("mode") if body.variables else None,
    )

    # Build RunContext (same pattern as analysis.py)
    from AICrews.application.crew.run_context import RunContext, run_context_scope
    run_ctx = RunContext(
        entitlements_decision=decision,
        effective_scope=decision.effective_scope.value,
        byok_allowed=decision.limits.byok_allowed,
        runtime_limits=decision.limits,
    )

    variables = body.variables or {}

    if (not crew.structure) and crew.ui_state:
        try:
            from AICrews.application.crew.graph_compiler import \
                compile_crew_graph

            compilation = compile_crew_graph(db, current_user.id, crew)
            if not compilation.success:
                raise HTTPException(
                    status_code=422,
                    detail=f"Graph compilation failed: {', '.join(compilation.errors) if compilation.errors else 'unknown error'}",
                )
            crew.structure = compilation.structure
            crew.input_schema = compilation.input_schema
            if compilation.output_config:
                crew.router_config = {
                    **(crew.router_config or {}),
                    "output_config": compilation.output_config,
                    "router_tasks": compilation.router_tasks,
                }
            crew.updated_at = datetime.now()
            db.commit()
            db.refresh(crew)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error compiling graph for crew {crew.name} before run: {e}",
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail="Graph compilation failed")

    if not body.skip_preflight:
        try:
            assembler = get_crew_assembler()
            # Keep preflight consistent with execution: run within RunContext scope so
            # policy LLM routing can be validated and template crews don't require per-agent binding.
            with run_context_scope(run_ctx):
                preflight = assembler.preflight_check(
                    crew_id=crew_id, user_id=current_user.id, variables=variables
                )
            if not preflight.success:
                raise HTTPException(
                    status_code=422,
                    detail=f"Preflight failed: {', '.join(preflight.errors)}",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Preflight check error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Preflight check failed")

    # Capture values to avoid closure issues with thread execution
    _crew_id = crew_id
    _variables = dict(variables)
    _user_id = current_user.id
    _crew_name = crew.name
    _run_ctx = run_ctx  # Capture RunContext for thread execution

    def execute_crew(job_id: str = None, **kwargs):
        import time
        import traceback
        from AICrews.application.crew import get_crew_assembler
        from AICrews.application.crew.run_context import run_context_scope
        from AICrews.observability.logging import LogContext
        from AICrews.schemas.llm_policy import LLMKeyProvisioningError
        from AICrews.schemas.stats import AgentActivityEvent
        from AICrews.services.tracking_service import TrackingService
        from AICrews.utils.redaction import truncate_text

        logger.info(
            f"==================== [Job {job_id}] EXECUTION START ===================="
        )

        assembler = get_crew_assembler()
        tracker = TrackingService()

        # Set LogContext for the entire execution so EventBus listeners can access job_id
        # This enables CrewAI tool events and litellm LLM events to be associated with this job
        log_context = LogContext(
            job_id=job_id,
            user_id=str(_user_id) if _user_id else None,
            ticker=_variables.get("ticker"),
        )
        log_context.__enter__()

        def _safe_activity(
            activity_type: str,
            message: str,
            details: dict | None = None,
        ) -> None:
            try:
                tracker.add_activity(
                    job_id,
                    AgentActivityEvent(
                        agent_name="System",
                        activity_type=activity_type,
                        message=message,
                        details=details,
                    ),
                )
            except Exception:
                logger.debug(
                    "[Job %s] Failed to record activity: %s",
                    job_id,
                    activity_type,
                    exc_info=True,
                )

        _safe_activity("phase", "Execution started")

        # Retry configuration for LLM key provisioning
        MAX_PROVISIONING_RETRIES = 6
        MAX_TOTAL_WAIT_SECONDS = 30

        try:
            # Execute within RunContext scope for entitlements + LLM routing
            with run_context_scope(_run_ctx):
                # Retry loop for LLM key provisioning
                crew_obj = None
                pf = None
                total_wait = 0
                last_provisioning_error = None

                for attempt in range(MAX_PROVISIONING_RETRIES):
                    try:
                        _safe_activity(
                            "phase",
                            f"Assembling crew (attempt {attempt + 1}/{MAX_PROVISIONING_RETRIES})",
                            {"crew_id": _crew_id, "crew_name": _crew_name},
                        )

                        crew_obj, pf = assembler.assemble(
                            crew_id=_crew_id, variables=_variables, job_id=job_id, user_id=_user_id
                        )
                        break  # Success, exit retry loop
                    except LLMKeyProvisioningError as e:
                        last_provisioning_error = e
                        retry_after = e.retry_after or 5

                        # Check if we've exceeded max wait time
                        if total_wait + retry_after > MAX_TOTAL_WAIT_SECONDS:
                            logger.warning(
                                f"[Job {job_id}] LLM provisioning timeout after {total_wait}s "
                                f"(max {MAX_TOTAL_WAIT_SECONDS}s). Giving up."
                            )
                            raise

                        logger.info(
                            f"[Job {job_id}] LLM key provisioning in progress, "
                            f"waiting {retry_after}s (attempt {attempt + 1}/{MAX_PROVISIONING_RETRIES})"
                        )
                        _safe_activity(
                            "phase",
                            f"LLM key provisioning in progress; sleeping {retry_after}s",
                            {
                                "attempt": attempt + 1,
                                "max_attempts": MAX_PROVISIONING_RETRIES,
                                "retry_after_seconds": retry_after,
                                "total_wait_seconds": total_wait,
                            },
                        )
                        time.sleep(retry_after)
                        total_wait += retry_after

                # If we exhausted retries without success
                if crew_obj is None:
                    if last_provisioning_error:
                        raise last_provisioning_error
                    raise RuntimeError("Assembly failed: no crew object returned")

                if not pf.success:
                    logger.error(f"[Job {job_id}] Assembly failed: {pf.errors}")
                    _safe_activity(
                        "error",
                        f"Assembly failed: {truncate_text(str(pf.errors), limit=500)}",
                    )
                    raise RuntimeError(f"Assembly failed: {pf.errors}")

                logger.info(
                    f"[Job {job_id}] Crew assembled with {len(crew_obj.agents)} agents, {len(crew_obj.tasks)} tasks. Starting kickoff..."
                )
                _safe_activity(
                    "phase",
                    "Kickoff starting",
                    {
                        "agents": len(getattr(crew_obj, "agents", []) or []),
                        "tasks": len(getattr(crew_obj, "tasks", []) or []),
                    },
                )
                result = crew_obj.kickoff()
                result_str = str(result)
                logger.info(f"[Job {job_id}] Crew kickoff completed successfully")
                _safe_activity("phase", "Kickoff completed")

            # Milestone B3 & B2 & C1: Enhanced archiving with traces, token usage, and versioning
            try:
                from AICrews.services.crew_run_archive_service import archive_crew_run_result

                _safe_activity("phase", "Archiving started")

                archive_crew_run_result(
                    job_id=job_id,
                    crew_id=_crew_id,
                    crew_name=_crew_name,
                    user_id=_user_id,
                    variables=_variables,
                    result=result,
                    result_str=result_str,
                )
                _safe_activity("phase", "Archiving completed")
            except Exception as archive_err:
                logger.error(
                    f"[Job {job_id}] Failed to archive enhanced result: {archive_err}\n{traceback.format_exc()}"
                )
                _safe_activity(
                    "warning",
                    f"Archiving failed: {truncate_text(str(archive_err), limit=500)}",
                )

            logger.info(
                f"==================== [Job {job_id}] EXECUTION FINISHED ===================="
            )
            # Clean up LogContext before returning
            log_context.__exit__(None, None, None)
            return result_str

        except Exception as e:
            error_stack = traceback.format_exc()
            logger.error(f"[Job {job_id}] CRITICAL FAILURE: {e}\n{error_stack}")
            _safe_activity(
                "error",
                f"CRITICAL FAILURE: {truncate_text(str(e), limit=500)}",
                {"stack_preview": truncate_text(error_stack, limit=2000)},
            )
            # 更新 JobManager 中的状态 (如果可能)
            try:
                from AICrews.infrastructure.jobs import get_job_manager
                jm = get_job_manager()
                # 这种手动更新通常由 JobManager.submit 包装层处理，但这里显式打印确保万无一失
            except:
                pass
            # Clean up LogContext before re-raising
            log_context.__exit__(type(e), e, e.__traceback__)
            raise

    try:
        job_manager = get_job_manager()
        job_id = job_manager.submit(
            execute_crew,
            crew_id=crew_id,
            crew_name=crew.name,
            user_id=current_user.id,
        )

        logger.info(
            f"Crew {crew_id} submitted as job {job_id} by user {current_user.id}"
        )

        return RunCrewResponse(
            job_id=job_id,
            message=f"Crew '{crew.name}' submitted for execution",
            status="pending",
        )

    except Exception as e:
        logger.error(f"Failed to submit crew {crew_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit crew execution")


@router.get(
    "/jobs/{job_id}", summary="获取任务状态", response_model=JobStatusResponse
)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> JobStatusResponse:
    """
    获取指定任务的状态和结果
    
    统一的任务状态查询端点，替代分散在各处的状态查询API
    """
    from AICrews.infrastructure.jobs import get_job_manager
    
    try:
        job_manager = get_job_manager()
        job_result = job_manager.get_status(job_id)
        
        if not job_result:
            raise HTTPException(status_code=404, detail="Job not found")
            
        # 权限检查
        if hasattr(job_result, 'user_id') and job_result.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
            
        # 从 TrackingService 获取事件和摘要 (v3)
        from AICrews.services.tracking_service import TrackingService
        tracker = TrackingService()
        events = tracker.get_run_events(job_id)
        stats = tracker.get_stats(job_id)
        
        summary = None
        hints = []
        if stats:
            summary = RunSummary(
                total_duration_ms=stats.total_duration_ms or 0,
                total_tokens=stats.total_tokens,
                prompt_tokens=stats.total_prompt_tokens,
                completion_tokens=stats.total_completion_tokens,
                tool_calls_count=stats.tool_call_count,
                agent_count=len(stats.agent_activities), # 简化处理
                task_count=0, # 待补齐
                status=stats.status
            )
            
            # 自动生成建议动作
            if stats.status == "failed":
                if job_result.error:
                    err_lower = job_result.error.lower()
                    if "api key" in err_lower or "invalid_api_key" in err_lower:
                        hints.append("Check your LLM provider API keys in settings.")
                        if "api.openai.com" in err_lower:
                            hints.append("The request appears to be hitting api.openai.com; if you intended an OpenAI-compatible vendor, verify provider/base_url selection.")
                    elif "timeout" in job_result.error.lower():
                        hints.append("The request timed out. Try a shorter analysis period or check your connection.")
                    elif "mcp" in job_result.error.lower():
                        hints.append("One or more data connectors (MCP) failed. Check their status in MCP settings.")
                
                if not hints:
                    hints.append("Check the detailed execution logs for more information.")
                    hints.append("Try running the preflight check before starting the mission.")
            
        # Extract task_outputs from TASK_OUTPUT events
        from AICrews.schemas.stats import RunEventType
        task_outputs = []
        for event in events:
            if event.event_type == RunEventType.TASK_OUTPUT:
                # Extract summary from payload
                payload = event.payload or {}
                task_summary = payload.get("summary", {})
                diagnostics = payload.get("diagnostics", {})
                task_outputs.append({
                    "task_id": event.task_id,
                    "agent_name": event.agent_name,
                    "raw_preview": task_summary.get("raw_preview"),
                    "validation_passed": task_summary.get("validation_passed", True),
                    "citation_count": diagnostics.get("citation_count", 0),
                    "output_mode": diagnostics.get("output_mode"),
                    "schema_key": diagnostics.get("schema_key"),
                })

        # Use get_result() to recover result from Redis if it was dropped from memory
        actual_result = job_manager.get_result(job_id) if job_result.result is None else job_result.result

        return JobStatusResponse(
            job_id=job_result.job_id,
            status=job_result.status.value if hasattr(job_result.status, 'value') else str(job_result.status),
            progress=job_result.progress or 0,
            progress_message=job_result.progress_message or "",
            result=actual_result,
            error=job_result.error,
            created_at=job_result.created_at.isoformat() if job_result.created_at else None,
            started_at=job_result.started_at.isoformat() if job_result.started_at else None,
            completed_at=job_result.completed_at.isoformat() if job_result.completed_at else None,
            ticker=getattr(job_result, 'ticker', None),
            crew_name=getattr(job_result, 'crew_name', None),
            events=events,
            summary=summary,
            hints=hints,
            task_outputs=task_outputs,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.post(
    "/crews/{crew_id}/preflight", summary="运行前预检"
)
async def preflight_crew(
    http_request: Request,
    crew_id: int,
    request: RunCrewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    运行前预检验证
    
    验证Crew配置、变量、API Key等是否满足执行条件
    前端可在实际运行前调用此接口检查问题
    """
    from AICrews.application.crew import get_crew_assembler
    
    crew = db.get(CrewDefinition, crew_id)
    
    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found")
        
    if not crew.is_template and crew.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    variables = request.variables or {}

    # Entitlements gate + RunContext (keep consistent with run endpoint)
    if crew.user_id is None or crew.is_template:
        action = PolicyAction.RUN_OFFICIAL_CREW
    else:
        action = PolicyAction.RUN_CUSTOM_CREW

    decision = require_entitlement(
        action=action,
        request=http_request,
        db=db,
        current_user=current_user,
        requested_mode=variables.get("mode") if variables else None,
    )

    from AICrews.application.crew.run_context import RunContext, run_context_scope

    run_ctx = RunContext(
        entitlements_decision=decision,
        effective_scope=decision.effective_scope.value,
        byok_allowed=decision.limits.byok_allowed,
        runtime_limits=decision.limits,
    )

    try:
        assembler = get_crew_assembler()
        with run_context_scope(run_ctx):
            preflight = assembler.preflight_check(
                crew_id=crew_id,
                user_id=current_user.id,
                variables=variables
            )

        # Convert UnauthorizedKnowledgeInfo dataclasses to dicts for JSON serialization
        from dataclasses import asdict
        unauthorized_knowledge_dicts = [
            asdict(k) for k in (preflight.unauthorized_knowledge or [])
        ]

        return {
            "success": preflight.success,
            "errors": preflight.errors or [],
            "warnings": getattr(preflight, 'warnings', []),
            "hints": getattr(preflight, 'hints', []),
            "unauthorized_knowledge": unauthorized_knowledge_dicts,
            "crew_name": crew.name,
            "variables_checked": list(variables.keys())
        }
        
    except Exception as e:
        logger.error(f"Preflight check failed for crew {crew_id}: {e}", exc_info=True)
        return {
            "success": False,
            "errors": ["Preflight check failed due to internal error"],
            "warnings": [],
            "crew_name": crew.name,
            "variables_checked": list(variables.keys())
        }
