"""
Agent Schemas - Agent 配置相关模型

定义 Agent 配置相关的 Pydantic 模型。
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from AICrews.schemas.common import BaseSchema
from AICrews.schemas.llm import LLMModelConfig
from AICrews.schemas.tool import ToolConfig


class AgentConfig(BaseSchema):
    """Agent 配置
    
    用于定义 Agent 的角色、目标、背景等。
    """
    id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent 名称", min_length=1, max_length=200)
    role: str = Field(..., description="Agent 角色", min_length=1, max_length=200)
    goal: str = Field(..., description="Agent 目标", min_length=1)
    backstory: str = Field(..., description="Agent 背景故事", min_length=1)
    description: Optional[str] = Field(None, description="Agent 描述")
    
    # 工具配置
    tools: List[str] = Field(default_factory=list, description="工具列表")
    llm_config_id: Optional[str] = Field(None, description="关联的 LLM 配置 ID")
    
    # 执行配置
    verbose: bool = Field(True, description="是否显示详细日志")
    allow_delegation: bool = Field(False, description="是否允许任务委派")
    max_iter: int = Field(3, ge=1, le=10, description="最大迭代次数")
    
    # LLM 参数
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    top_p: float = Field(0.9, ge=0.0, le=1.0, description="Top-P 参数")
    max_tokens: int = Field(2048, ge=1, le=100000, description="最大 token 数")
    
    # 元数据
    is_template: bool = Field(False, description="是否为模板")
    is_active: bool = Field(True, description="是否启用")
    
    # 【新】4-Tier Loadout 配置
    # 格式: {"data_tools": ["data:price"], "quant_tools": ["quant:rsi"], 
    #        "external_tools": ["external:search"], "strategies": ["strategy:123"]}
    loadout_data: Optional[Dict[str, Any]] = Field(
        None,
        description="4-Tier Loadout 配置"
    )
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "agent_fundamental",
                "name": "Fundamental Analyst",
                "role": "Senior Fundamental Analyst",
                "goal": "Analyze company financials and provide investment insights",
                "backstory": "Expert in financial statement analysis with 10 years of experience...",
                "tools": ["get_fundamentals", "get_financial_statements"],
                "llm_config_id": "llm_openai_1",
                "temperature": 0.7,
                "verbose": True,
                "allow_delegation": False,
                "max_iter": 3
            }
        }
    )


class AgentCreate(BaseSchema):
    """Agent 创建请求
    
    用于创建新 Agent。
    """
    name: str = Field(..., min_length=1, max_length=200, description="Agent 名称")
    role: str = Field(..., min_length=1, max_length=200, description="Agent 角色")
    goal: str = Field(..., min_length=1, description="Agent 目标")
    backstory: str = Field(..., min_length=1, description="Agent 背景故事")
    description: Optional[str] = Field(None, description="Agent 描述")
    
    # 工具配置
    tools: List[str] = Field(default_factory=list, description="工具列表")
    llm_config_id: Optional[str] = Field(None, description="关联的 LLM 配置 ID")
    
    # 执行配置
    verbose: bool = Field(True, description="是否显示详细日志")
    allow_delegation: bool = Field(False, description="是否允许任务委派")
    max_iter: int = Field(3, ge=1, le=10, description="最大迭代次数")
    
    # LLM 参数
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    top_p: float = Field(0.9, ge=0.0, le=1.0, description="Top-P 参数")
    max_tokens: int = Field(2048, ge=1, le=100000, description="最大 token 数")
    
    # 元数据
    is_template: bool = Field(False, description="是否为模板")
    
    # 【新】4-Tier Loadout 配置
    loadout_data: Optional[Dict[str, Any]] = Field(
        None,
        description="4-Tier Loadout 配置"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Technical Analyst",
                "role": "Senior Technical Analyst",
                "goal": "Analyze technical indicators and identify trading signals",
                "backstory": "Expert in technical analysis...",
                "tools": ["get_stock_prices", "calculate_rsi"],
                "temperature": 0.7
            }
        }
    )


class AgentUpdate(BaseSchema):
    """Agent 更新请求
    
    用于更新 Agent 配置。
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Agent 名称")
    role: Optional[str] = Field(None, min_length=1, max_length=200, description="Agent 角色")
    goal: Optional[str] = Field(None, min_length=1, description="Agent 目标")
    backstory: Optional[str] = Field(None, min_length=1, description="Agent 背景故事")
    description: Optional[str] = Field(None, description="Agent 描述")
    
    # 工具配置
    tools: Optional[List[str]] = Field(None, description="工具列表")
    llm_config_id: Optional[str] = Field(None, description="关联的 LLM 配置 ID")
    
    # 执行配置
    verbose: Optional[bool] = Field(None, description="是否显示详细日志")
    allow_delegation: Optional[bool] = Field(None, description="是否允许任务委派")
    max_iter: Optional[int] = Field(None, ge=1, le=10, description="最大迭代次数")
    
    # LLM 参数
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="温度参数")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Top-P 参数")
    max_tokens: Optional[int] = Field(None, ge=1, le=100000, description="最大 token 数")
    
    # 元数据
    is_active: Optional[bool] = Field(None, description="是否启用")
    
    # 【新】4-Tier Loadout 配置
    loadout_data: Optional[Dict[str, Any]] = Field(
        None,
        description="4-Tier Loadout 配置"
    )


class AgentResponse(BaseSchema):
    """Agent 响应
    
    用于返回 Agent 信息。
    """
    id: int = Field(..., description="Agent ID")
    user_id: Optional[int] = Field(None, description="用户 ID")
    name: str = Field(..., description="Agent 名称")
    role: str = Field(..., description="Agent 角色")
    goal: str = Field(..., description="Agent 目标")
    backstory: str = Field(..., description="Agent 背景故事")
    description: Optional[str] = Field(None, description="Agent 描述")
    
    # 工具配置
    tools: List[str] = Field(default_factory=list, description="工具列表")
    llm_config: Optional[LLMModelConfig] = Field(None, description="LLM 配置")
    
    # 执行配置
    verbose: bool = Field(..., description="是否显示详细日志")
    allow_delegation: bool = Field(..., description="是否允许任务委派")
    max_iter: int = Field(..., description="最大迭代次数")
    
    # LLM 参数
    temperature: float = Field(..., description="温度参数")
    top_p: float = Field(..., description="Top-P 参数")
    max_tokens: int = Field(..., description="最大 token 数")
    
    # 元数据
    is_template: bool = Field(..., description="是否为模板")
    is_active: bool = Field(..., description="是否启用")
    
    # 【新】4-Tier Loadout 配置
    loadout_data: Optional[Dict[str, Any]] = Field(
        None,
        description="4-Tier Loadout 配置"
    )
    
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 关联的工具详情
    tool_details: List[ToolConfig] = Field(
        default_factory=list,
        description="工具详情列表"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Fundamental Analyst",
                "role": "Senior Fundamental Analyst",
                "goal": "Analyze company financials",
                "backstory": "Expert in financial statement analysis...",
                "tools": ["get_fundamentals"],
                "temperature": 0.7,
                "verbose": True,
                "allow_delegation": False,
                "max_iter": 3,
                "is_template": False,
                "is_active": True,
                "created_at": "2025-12-26T00:00:00Z",
                "updated_at": "2025-12-26T00:00:00Z"
            }
        }
    )


# TaskConfig 是 AgentConfig 的别名（向后兼容）
TaskConfig = AgentConfig


class TaskCreate(BaseSchema):
    """Task 创建请求（向后兼容）
    
    作为 AgentCreate 的别名。
    """
    name: str = Field(..., min_length=1, max_length=200, description="Task 名称")
    role: str = Field(..., min_length=1, max_length=200, description="Task 角色")
    goal: str = Field(..., min_length=1, description="Task 目标")
    backstory: str = Field(..., min_length=1, description="Task 背景故事")
    description: Optional[str] = Field(None, description="Task 描述")
    tools: List[str] = Field(default_factory=list, description="工具列表")
    llm_config_id: Optional[str] = Field(None, description="关联的 LLM 配置 ID")
    verbose: bool = Field(True, description="是否显示详细日志")
    allow_delegation: bool = Field(False, description="是否允许任务委派")
    max_iter: int = Field(3, ge=1, le=10, description="最大迭代次数")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    top_p: float = Field(0.9, ge=0.0, le=1.0, description="Top-P 参数")
    max_tokens: int = Field(2048, ge=1, le=100000, description="最大 token 数")
    is_template: bool = Field(False, description="是否为模板")
    loadout_data: Optional[Dict[str, Any]] = Field(None, description="4-Tier Loadout 配置")


class TaskResponse(BaseSchema):
    """Task 响应（向后兼容）
    
    作为 AgentResponse 的别名。
    """
    id: int = Field(..., description="Task ID")
    user_id: Optional[int] = Field(None, description="用户 ID")
    name: str = Field(..., description="Task 名称")
    role: str = Field(..., description="Task 角色")
    goal: str = Field(..., description="Task 目标")
    backstory: str = Field(..., description="Task 背景故事")
    description: Optional[str] = Field(None, description="Task 描述")
    tools: List[str] = Field(default_factory=list, description="工具列表")
    llm_config: Optional[LLMModelConfig] = Field(None, description="LLM 配置")
    verbose: bool = Field(..., description="是否显示详细日志")
    allow_delegation: bool = Field(..., description="是否允许任务委派")
    max_iter: int = Field(..., description="最大迭代次数")
    temperature: float = Field(..., description="温度参数")
    top_p: float = Field(..., description="Top-P 参数")
    max_tokens: int = Field(..., description="最大 token 数")
    is_template: bool = Field(..., description="是否为模板")
    is_active: bool = Field(..., description="是否启用")
    loadout_data: Optional[Dict[str, Any]] = Field(None, description="4-Tier Loadout 配置")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    tool_details: List[ToolConfig] = Field(default_factory=list, description="工具详情列表")


__all__ = [
    "AgentConfig",
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    # 向后兼容别名
    "TaskConfig",
    "TaskCreate",
    "TaskResponse",
]
