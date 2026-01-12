from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field

# 统一的 TradingLesson 默认配置
DEFAULT_INCLUDE_TRADING_LESSONS = True  # Crew 和 Agent 级别统一默认开启
DEFAULT_MAX_LESSONS = 5

class KnowledgeSourceResponse(BaseModel):
    """知识源响应"""
    id: int
    source_key: str
    display_name: str
    description: Optional[str] = None
    source_type: str
    category: str
    knowledge_scope: str = "both"  # crew, agent, both (injection scope)
    scope: str = "system"  # system / user (ownership scope)
    tier: str = "free"  # free / premium / private
    price: int = 0  # 价格(分)
    tags: Optional[List[str]] = None
    icon: Optional[str] = None
    cover_image: Optional[str] = None
    author: Optional[str] = None
    version: str
    is_free: bool
    subscriber_count: int
    usage_count: int
    is_subscribed: bool = False
    is_owned: bool = False  # 用户是否拥有(私有知识)
    access_status: str = "locked"  # owned, subscribed, free, locked

    class Config:
        from_attributes = True

class UserKnowledgeSourceResponse(BaseModel):
    """用户自定义知识源响应"""
    id: int
    source_key: str
    display_name: str
    description: Optional[str] = None
    source_type: str
    category: str
    scope: str = "both"  # crew, agent, both
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CreateUserKnowledgeRequest(BaseModel):
    """创建用户知识源请求"""
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    source_type: str = Field("string", description="file, url, string")
    content: Optional[str] = None
    url: Optional[str] = None
    category: str = Field("custom")
    scope: str = Field("both", description="crew, agent, both")

class CrewKnowledgeBindingRequest(BaseModel):
    """Crew 知识绑定请求"""
    binding_mode: str = Field(default="explicit", description="绑定模式")
    source_ids: Optional[List[int]] = Field(default=[], description="系统知识源 ID")
    user_source_ids: Optional[List[int]] = Field(default=[], description="用户自定义知识源 ID")
    categories: Optional[List[str]] = Field(default=[], description="知识分类")
    excluded_source_ids: Optional[List[int]] = Field(default=[], description="排除的知识源 ID")
    include_trading_lessons: bool = Field(default=DEFAULT_INCLUDE_TRADING_LESSONS, description="是否包含历史交易教训")
    max_lessons: int = Field(default=DEFAULT_MAX_LESSONS, description="最大教训数量")

class AgentKnowledgeBindingRequest(BaseModel):
    """Agent 知识绑定请求"""
    agent_name: str = Field(..., description="Agent 名称")
    source_ids: Optional[List[int]] = Field(default=[], description="系统知识源 ID")
    user_source_ids: Optional[List[int]] = Field(default=[], description="用户自定义知识源 ID")
    include_trading_lessons: bool = Field(default=DEFAULT_INCLUDE_TRADING_LESSONS, description="是否包含历史交易教训")
    max_lessons: int = Field(default=DEFAULT_MAX_LESSONS, description="最大教训数量")

class AgentKnowledgeBindingResponse(BaseModel):
    """Agent 知识绑定响应"""
    agent_name: str
    source_ids: List[int]
    user_source_ids: List[int]
    include_trading_lessons: bool
    max_lessons: int
    created_at: datetime

class CrewKnowledgeBindingResponse(BaseModel):
    """Crew 知识绑定响应"""
    id: Optional[int] = None
    crew_name: str
    binding_mode: str
    source_ids: List[int]
    user_source_ids: List[int]
    categories: List[str]
    excluded_source_ids: List[int]
    include_trading_lessons: bool
    max_lessons: int
    is_default: bool = False

class KnowledgeVersionResponse(BaseModel):
    """知识源版本响应"""
    id: int
    source_id: int
    version: str
    changelog: Optional[str] = None
    is_current: bool
    created_at: datetime
