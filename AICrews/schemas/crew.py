"""
Crew Schemas - Crew 配置相关模型

定义 Crew、Task 配置相关的 Pydantic 模型。
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from AICrews.schemas.common import BaseSchema
from AICrews.schemas.agent import AgentConfig


class ToolConfig(BaseModel):
    """工具配置"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    category: str = Field(..., description="工具类别")
    is_enabled: bool = Field(True, description="是否启用")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "get_fundamentals",
                "description": "获取基本面数据",
                "category": "data",
                "is_enabled": True
            }
        }
    )


class TaskConfig(BaseSchema):
    """Task 配置"""
    id: str = Field(..., description="Task ID")
    name: str = Field(..., description="Task 名称", min_length=1, max_length=200)
    description: str = Field(..., description="Task 描述", min_length=1)
    expected_output: str = Field(..., description="期望输出", min_length=1)
    agent_id: str = Field(..., description="关联的 Agent ID")
    
    # 依赖关系
    context_task_ids: List[str] = Field(default_factory=list, description="依赖的 Task ID 列表")
    async_execution: bool = Field(False, description="是否异步执行")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "task_fundamental_analysis",
                "name": "Fundamental Analysis",
                "description": "Analyze the fundamental data for {ticker}",
                "expected_output": "A detailed fundamental analysis report",
                "agent_id": "agent_fundamental",
                "context_task_ids": [],
                "async_execution": False
            }
        }
    )


class TaskCreate(BaseSchema):
    """Task 创建请求"""
    name: str = Field(..., min_length=1, max_length=200, description="Task 名称")
    description: str = Field(..., min_length=1, description="Task 描述")
    expected_output: str = Field(..., min_length=1, description="期望输出")
    agent_definition_id: Optional[int] = Field(None, description="关联的 Agent 定义 ID")
    
    # 依赖关系
    context_task_ids: List[int] = Field(default_factory=list, description="依赖的 Task ID 列表")
    async_execution: bool = Field(False, description="是否异步执行")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Technical Analysis",
                "description": "Analyze technical indicators",
                "expected_output": "A detailed technical analysis report",
                "async_execution": False
            }
        }
    )


class TaskResponse(BaseSchema):
    """Task 响应"""
    id: int = Field(..., description="Task ID")
    user_id: Optional[int] = Field(None, description="用户 ID")
    name: str = Field(..., description="Task 名称")
    description: str = Field(..., description="Task 描述")
    expected_output: str = Field(..., description="期望输出")
    agent_definition_id: Optional[int] = Field(None, description="关联的 Agent 定义 ID")
    
    # 依赖关系
    context_task_ids: List[int] = Field(default_factory=list, description="依赖的 Task ID 列表")
    async_execution: bool = Field(..., description="是否异步执行")
    
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 关联信息
    agent_name: Optional[str] = Field(None, description="Agent 名称")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Fundamental Analysis",
                "description": "Analyze fundamental data",
                "expected_output": "A detailed report",
                "agent_definition_id": 1,
                "async_execution": False,
                "created_at": "2025-12-26T00:00:00Z",
                "updated_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class PhaseConfig(BaseModel):
    """阶段配置"""
    name: str = Field(..., description="阶段名称")
    tasks: List[str] = Field(default_factory=list, description="Task ID 列表")
    repeat: int = Field(1, ge=1, description="重复次数")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Research Phase",
                "tasks": ["task_1", "task_2"],
                "repeat": 1
            }
        }
    )


class CrewConfig(BaseSchema):
    """Crew 配置
    
    用于定义 Crew 的结构和配置。
    """
    id: str = Field(..., description="Crew ID")
    name: str = Field(..., description="Crew 名称", min_length=1, max_length=200)
    description: str = Field(..., description="Crew 描述")
    
    # Agents 和 Tasks
    agents: List[Dict[str, Any]] = Field(default_factory=list, description="Agent 配置列表")
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="Task 配置列表")
    phases: List[PhaseConfig] = Field(default_factory=list, description="阶段配置列表")
    
    # 执行配置
    process: str = Field("sequential", description="执行流程: sequential 或 hierarchical")
    memory: bool = Field(False, description="是否启用记忆")
    max_iter: int = Field(3, ge=1, le=10, description="最大迭代次数")
    verbose: bool = Field(True, description="是否显示详细日志")
    
    # 辩论配置
    debate_rounds: int = Field(1, ge=1, le=5, description="辩论轮数")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_template: bool = Field(False, description="是否为模板")
    user_id: Optional[int] = Field(None, description="所有者用户 ID (None 表示系统级模板)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "crew_custom_1",
                "name": "My Custom Crew",
                "description": "A custom analysis crew",
                "process": "sequential",
                "memory": False,
                "max_iter": 3,
                "verbose": True,
                "debate_rounds": 2,
                "is_template": False
            }
        }
    )


class CrewCreate(BaseSchema):
    """Crew 创建请求"""
    name: str = Field(..., min_length=1, max_length=200, description="Crew 名称")
    description: str = Field(..., description="Crew 描述")
    
    # 执行配置
    process: str = Field("sequential", description="执行流程: sequential 或 hierarchical")
    memory: bool = Field(False, description="是否启用记忆")
    max_iter: int = Field(3, ge=1, le=10, description="最大迭代次数")
    verbose: bool = Field(True, description="是否显示详细日志")
    
    # 结构配置
    structure: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Crew 结构: [{agent_id, tasks: []}]"
    )
    
    # V1.1 核心补充：前端状态
    ui_state: Optional[Dict[str, Any]] = Field(
        None,
        description="前端状态: { nodes: [], edges: [], viewport: {} }"
    )
    input_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="Start Node Schema"
    )
    router_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Router Node Rules"
    )
    
    # 元数据
    is_template: bool = Field(False, description="是否为模板")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Comprehensive Analysis Crew",
                "description": "A crew that performs comprehensive analysis",
                "process": "sequential",
                "memory": True,
                "max_iter": 3,
                "verbose": True
            }
        }
    )


class CrewResponse(BaseSchema):
    """Crew 响应"""
    id: int = Field(..., description="Crew ID")
    user_id: Optional[int] = Field(None, description="用户 ID")
    name: str = Field(..., description="Crew 名称")
    description: Optional[str] = Field(None, description="Crew 描述")
    
    # 执行配置
    process: str = Field(..., description="执行流程")
    memory: bool = Field(..., description="是否启用记忆")
    cache_enabled: bool = Field(..., description="是否启用缓存")
    verbose: bool = Field(..., description="是否显示详细日志")
    max_iter: Optional[int] = Field(None, description="最大迭代次数")
    
    # 结构配置
    structure: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Crew 结构"
    )
    
    # V1.1 核心补充：前端状态
    ui_state: Optional[Dict[str, Any]] = Field(None, description="前端状态")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="输入 Schema")
    router_config: Optional[Dict[str, Any]] = Field(None, description="路由配置")
    
    # Manager 配置
    manager_llm_config: Optional[Dict[str, Any]] = Field(None, description="Manager LLM 配置")
    default_variables: Optional[Dict[str, Any]] = Field(None, description="默认变量")
    
    # 元数据
    is_template: bool = Field(..., description="是否为模板")
    is_active: bool = Field(..., description="是否启用")
    
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 关联信息
    agents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Agent 列表"
    )
    tasks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Task 列表"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Comprehensive Analysis Crew",
                "description": "A crew that performs comprehensive analysis",
                "process": "sequential",
                "memory": True,
                "verbose": True,
                "max_iter": 3,
                "is_template": False,
                "is_active": True,
                "created_at": "2025-12-26T00:00:00Z",
                "updated_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class CrewVersionResponse(BaseSchema):
    """Crew 版本响应"""
    id: int = Field(..., description="版本 ID")
    crew_id: int = Field(..., description="Crew ID")
    version_number: int = Field(..., description="版本号")
    description: Optional[str] = Field(None, description="版本描述")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "crew_id": 1,
                "version_number": 1,
                "description": "Initial version",
                "created_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class AgentKnowledgeConfig(BaseModel):
    """单个 Agent 的知识配置"""
    source_ids: List[int] = Field(default=[], description="系统知识源 ID")
    user_source_ids: List[int] = Field(default=[], description="用户自定义知识源 ID")
    include_trading_lessons: bool = Field(default=False, description="是否包含历史交易教训")
    max_lessons: int = Field(default=5, description="最大教训数量")


class CreateAgentRequest(BaseModel):
    """创建 Agent 请求"""
    name: str = Field(..., description="Agent 名称")
    role: str = Field(..., description="角色")
    goal: str = Field(..., description="目标")
    backstory: str = Field(..., description="背景故事")
    tools: List[str] = Field(default=[], description="工具列表")
    llm_config_id: Optional[str] = Field(None, description="关联的 LLM 配置 ID")
    llm_type: str = Field("light", description="LLM 类型: deep 或 light")
    verbose: bool = Field(True, description="是否详细输出")
    allow_delegation: bool = Field(False, description="是否允许委托")
    knowledge_config: Optional[AgentKnowledgeConfig] = Field(None, description="知识配置")
    # 进阶参数
    temperature: float = Field(0.7, description="温度参数")
    top_p: float = Field(0.9, description="Top-P 参数")
    max_tokens: int = Field(2048, description="最大 token 数")
    max_iter: int = Field(3, description="最大迭代次数")


class CreateTaskRequest(BaseModel):
    """创建 Task 请求"""
    name: str = Field(..., description="任务名称")
    description: str = Field(..., description="任务描述")
    expected_output: str = Field(..., description="期望输出")
    agent_id: str = Field(..., description="执行 Agent ID")
    context_task_ids: List[str] = Field(default=[], description="上下文任务 ID 列表")
    async_execution: bool = Field(False, description="是否异步执行")


class CreateCrewRequest(BaseModel):
    """创建 Crew 请求"""
    name: str = Field(..., description="Crew 名称")
    description: str = Field(..., description="描述")
    agents: List[CreateAgentRequest] = Field(default=[], description="Agent 列表")
    tasks: List[CreateTaskRequest] = Field(default=[], description="Task 列表")
    process: str = Field("sequential", description="执行模式: sequential 或 hierarchical")
    memory: bool = Field(False, description="是否启用记忆")
    max_iter: int = Field(3, description="最大迭代次数")
    verbose: bool = Field(True, description="是否详细输出")
    debate_rounds: int = Field(1, description="辩论轮数")
    is_template: bool = Field(False, description="是否为模板")


class UpdateCrewRequest(BaseModel):
    """更新 Crew 请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    agents: Optional[List[CreateAgentRequest]] = None
    tasks: Optional[List[CreateTaskRequest]] = None
    process: Optional[str] = None
    memory: Optional[bool] = None
    max_iter: Optional[int] = None
    verbose: Optional[bool] = None
    debate_rounds: Optional[int] = None
    is_template: Optional[bool] = None


# ============================================
# Crew Builder API Schemas (from endpoints)
# ============================================


class AgentDefinitionCreate(BaseModel):
    """创建 Agent 定义 (Crew Builder API)"""

    name: str = Field(..., description="Agent 名称")
    role: str = Field(..., description="角色")
    goal: str = Field(..., description="目标 (支持 {ticker} 等变量)")
    backstory: str = Field(..., description="背景故事")
    description: Optional[str] = Field(None, description="简短描述")
    llm_config: Optional[Dict[str, Any]] = Field(None, description="LLM 配置")
    allow_delegation: bool = Field(False, description="是否允许委派")
    verbose: bool = Field(True, description="是否详细输出")
    is_template: bool = Field(False, description="是否为公共模板")
    # 【旧】扁平工具列表 - 向后兼容
    tool_ids: Optional[List[int]] = Field(None, description="绑定的工具 ID (legacy)")
    knowledge_source_ids: Optional[List[int]] = Field(
        None, description="绑定的知识源 ID"
    )
    mcp_server_ids: Optional[List[int]] = Field(
        None, description="绑定的 MCP 服务器 ID"
    )
    # 【新】4-Tier Loadout 配置
    loadout_data: Optional[Dict[str, Any]] = Field(
        None,
        description="4-Tier Loadout: {data_tools: [], quant_tools: [], external_tools: [], strategies: []}",
    )


class AgentDefinitionUpdate(BaseModel):
    """更新 Agent 定义 (Crew Builder API)"""

    name: Optional[str] = None
    role: Optional[str] = None
    goal: Optional[str] = None
    backstory: Optional[str] = None
    description: Optional[str] = None
    llm_config: Optional[Dict[str, Any]] = None
    allow_delegation: Optional[bool] = None
    verbose: Optional[bool] = None
    is_template: Optional[bool] = None
    tool_ids: Optional[List[int]] = None
    knowledge_source_ids: Optional[List[int]] = None
    mcp_server_ids: Optional[List[int]] = None
    loadout_data: Optional[Dict[str, Any]] = None


class AgentDefinitionResponse(BaseModel):
    """Agent 定义响应 (Crew Builder API)"""

    id: int
    user_id: Optional[int]
    name: str
    role: str
    goal: str
    backstory: str
    description: Optional[str]
    llm_config: Optional[Dict[str, Any]]
    allow_delegation: bool
    verbose: bool
    is_template: bool
    is_active: bool
    tool_ids: Optional[List[int]]
    knowledge_source_ids: Optional[List[int]]
    mcp_server_ids: Optional[List[int]]
    loadout_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CrewStructureEntry(BaseModel):
    """Crew 结构条目 (Crew Builder API)"""

    agent_id: int = Field(..., description="Agent 定义 ID")
    tasks: List[int] = Field(default=[], description="Task 定义 ID 列表")


class CrewDefinitionCreate(BaseModel):
    """创建 Crew 定义 (Crew Builder API)"""

    name: str = Field(..., description="Crew 名称")
    description: Optional[str] = Field(None, description="描述")
    process: str = Field(
        "sequential", description="执行模式: sequential 或 hierarchical"
    )
    structure: List[CrewStructureEntry] = Field(
        default=[], description="Agent-Task 编排结构"
    )
    ui_state: Optional[Dict[str, Any]] = Field(
        None, description="前端 UI 状态 (nodes, edges, viewport)"
    )
    input_schema: Optional[Any] = Field(
        None, description="Start Node 输入模式 (Array 或 Dict)"
    )
    router_config: Optional[Any] = Field(
        None, description="Router 节点配置 (Dict 或 List)"
    )
    memory_enabled: bool = Field(True, description="是否启用记忆")
    cache_enabled: bool = Field(True, description="是否启用缓存")
    verbose: bool = Field(True, description="是否详细输出")
    max_iter: int = Field(3, description="最大迭代次数")
    manager_llm_config: Optional[Dict[str, Any]] = Field(
        None, description="管理者 LLM 配置 (层级模式)"
    )
    default_variables: Optional[Dict[str, Any]] = Field(None, description="默认变量值")
    is_template: bool = Field(False, description="是否为公共模板")


class CrewDefinitionUpdate(BaseModel):
    """更新 Crew 定义 (Crew Builder API)"""

    name: Optional[str] = None
    description: Optional[str] = None
    process: Optional[str] = None
    structure: Optional[List[CrewStructureEntry]] = None
    ui_state: Optional[Dict[str, Any]] = None
    input_schema: Optional[Any] = None
    router_config: Optional[Any] = None
    memory_enabled: Optional[bool] = None
    cache_enabled: Optional[bool] = None
    verbose: Optional[bool] = None
    max_iter: Optional[int] = None
    manager_llm_config: Optional[Dict[str, Any]] = None
    default_variables: Optional[Dict[str, Any]] = None
    is_template: Optional[bool] = None


class CrewDefinitionResponse(BaseModel):
    """Crew 定义响应 (Crew Builder API)"""

    id: int
    user_id: Optional[int]
    name: str
    description: Optional[str]
    process: str
    structure: List[Dict[str, Any]]
    ui_state: Optional[Dict[str, Any]]
    input_schema: Optional[Any]
    router_config: Optional[Any]
    memory_enabled: bool
    cache_enabled: bool
    verbose: bool
    max_iter: Optional[int]
    manager_llm_config: Optional[Dict[str, Any]]
    default_variables: Optional[Dict[str, Any]]
    is_template: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VariableInfo(BaseModel):
    """变量信息 (Crew Builder API)"""

    name: str
    default: Optional[Any]
    required: bool


class PreflightResponse(BaseModel):
    """预检响应 (Crew Builder API)"""

    success: bool
    errors: List[str]
    warnings: List[str]
    missing_variables: List[str]
    missing_api_keys: List[str]
    unauthorized_knowledge: List[str]


class CloneRequest(BaseModel):
    """克隆请求 (Crew Builder API)"""

    new_name: Optional[str] = Field(None, description="新名称")


class SaveVersionRequest(BaseModel):
    """保存版本请求 (Crew Builder API)"""

    description: Optional[str] = Field(None, description="版本描述")


class RunCrewRequest(BaseModel):
    """运行 Crew 请求 (Crew Builder API)"""

    variables: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="运行时变量"
    )
    skip_preflight: bool = Field(False, description="是否跳过预检")


class RunCrewResponse(BaseModel):
    """运行 Crew 响应 (Crew Builder API)"""

    job_id: str
    message: str
    status: str


__all__ = [
    # Core Crew Schemas
    "ToolConfig",
    "TaskConfig",
    "TaskCreate",
    "TaskResponse",
    "PhaseConfig",
    "CrewConfig",
    "CrewCreate",
    "CrewResponse",
    "CrewVersionResponse",
    "AgentKnowledgeConfig",
    "CreateAgentRequest",
    "CreateTaskRequest",
    "CreateCrewRequest",
    "UpdateCrewRequest",
    # Crew Builder API Schemas
    "AgentDefinitionCreate",
    "AgentDefinitionUpdate",
    "AgentDefinitionResponse",
    "CrewStructureEntry",
    "CrewDefinitionCreate",
    "CrewDefinitionUpdate",
    "CrewDefinitionResponse",
    "VariableInfo",
    "PreflightResponse",
    "CloneRequest",
    "SaveVersionRequest",
    "RunCrewRequest",
    "RunCrewResponse",
]
