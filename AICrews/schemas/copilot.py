"""
Copilot Schemas - 全局 AI 助手相关模型

定义 Copilot 对话、历史记录等相关的 Pydantic 模型。
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from AICrews.schemas.common import BaseSchema, BaseResponse


class CopilotChatRequest(BaseSchema):
    """Copilot 对话请求"""
    message: str = Field(..., description="用户消息")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息 (如当前页面 URL, 选中内容等)")
    enable_web_search: bool = Field(True, description="是否启用网络搜索")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "分析一下 AAPL 的近期走势",
                "context": {"current_page": "/market/AAPL"},
                "enable_web_search": True
            }
        }
    )


class CopilotChatResponse(BaseSchema):
    """Copilot 对话响应"""
    reply: str = Field(..., description="AI 回复内容")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="参考来源")
    search_performed: bool = Field(False, description="是否执行了搜索")
    execution_time_ms: int = Field(..., description="执行耗时(ms)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reply": "AAPL 近期走势强劲...",
                "sources": [{"title": "News 1", "url": "..."}],
                "search_performed": True,
                "execution_time_ms": 1200
            }
        }
    )


class CopilotMessage(BaseSchema):
    """Copilot 历史消息"""
    role: str = Field(..., description="角色: user 或 assistant")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[str] = Field(None, description="时间戳")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "user",
                "content": "Hello",
                "timestamp": "2025-12-27T10:00:00Z"
            }
        }
    )


class CopilotHistoryResponse(BaseSchema):
    """Copilot 历史记录响应"""
    messages: List[CopilotMessage] = Field(..., description="消息列表")
    total_count: int = Field(..., description="消息总数")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    {"role": "user", "content": "Hi", "timestamp": "..."}
                ],
                "total_count": 1
            }
        }
    )


class AvailableLLMConfig(BaseSchema):
    """可用的 LLM 配置"""
    id: str = Field(..., description="配置 ID")
    name: str = Field(..., description="配置名称")
    provider_name: str = Field(..., description="提供商名称")
    model_name: str = Field("", description="模型名称")


class UserPreferencesResponse(BaseSchema):
    """用户偏好设置响应"""
    default_llm_config_id: Optional[str] = Field(None, description="默认 LLM 配置 ID (deprecated)")
    default_model_config_id: Optional[int] = Field(None, description="默认模型配置 ID")
    available_llm_configs: List[AvailableLLMConfig] = Field(default_factory=list, description="可用的 LLM 配置列表")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "default_llm_config_id": "1", 
                "default_model_config_id": 123,
                "available_llm_configs": [
                    {"id": "123", "name": "OpenAI GPT-4", "provider_name": "OpenAI", "model_name": "gpt-4"},
                    {"id": "124", "name": "OpenAI GPT-3.5", "provider_name": "OpenAI", "model_name": "gpt-3.5-turbo"}
                ]
            }
        }
    )


class UserPreferencesUpdate(BaseSchema):
    """用户偏好设置更新请求"""
    default_llm_config_id: Optional[str] = Field(None, description="默认 LLM 配置 ID (deprecated)")
    default_model_config_id: Optional[int] = Field(None, description="默认模型配置 ID")
