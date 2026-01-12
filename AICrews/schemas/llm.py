from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ReloadConfigResponse(BaseModel):
    """重新加载配置响应。"""
    status: str
    providers_count: int
    reload_time: Optional[str] = None
    cache_cleared: bool = True

class SyncModelsRequest(BaseModel):
    """同步模型请求。"""
    provider_key: Optional[str] = Field(None, description="指定提供商键（可选，同步所有）")
    api_key: Optional[str] = Field(None, description="API Key（用于动态发现）")
    base_url: Optional[str] = Field(None, description="自定义 Base URL")

class SyncModelsResponse(BaseModel):
    """同步模型响应。"""
    status: str
    results: Dict[str, Any]

class ConfigStatusResponse(BaseModel):
    """配置状态响应。"""
    providers_path: str
    providers_loaded: bool
    providers_count: int
    pricing_path: str
    pricing_loaded: bool
    model_tags_path: str
    model_tags_loaded: bool
    last_reload_time: Optional[str] = None
    reload_count: int
    cache_stats: Dict[str, Any] = {}

class ProviderInfoResponse(BaseModel):
    """提供商信息响应。"""
    provider_key: str
    display_name: str
    provider_type: str
    requires_api_key: bool = True
    requires_base_url: bool = False
    requires_custom_model_name: bool = False
    default_base_url: Optional[str] = None
    is_china_provider: bool = False
    has_env_config: bool = False

class CreateLLMParamsRequest(BaseModel):
    """创建 LLM 参数请求。"""
    provider_key: str = Field(..., description="提供商键")
    model_key: str = Field(..., description="模型键")
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, description="自定义 Base URL")
    temperature: float = Field(0.7, description="温度")
    max_tokens: Optional[int] = Field(None, description="最大 Token 数")


# ============================================
# Core LLM Schemas (Missing ones restored)
# ============================================

class LLMProviderInfo(BaseModel):
    id: int
    provider_key: str
    display_name: str
    provider_type: str
    requires_api_key: bool
    requires_base_url: bool
    requires_custom_model_name: bool
    default_base_url: Optional[str] = None
    is_active: bool
    sort_order: int
    
    class Config:
        from_attributes = True

class LLMModelInfo(BaseModel):
    id: int
    provider_id: int
    model_key: str
    display_name: str
    context_length: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supports_tools: bool = False
    supports_vision: bool = False
    supports_streaming: bool = False
    cost_per_million_input_tokens: Optional[float] = None
    cost_per_million_output_tokens: Optional[float] = None
    model_category: str = "general"
    recommended_for: Optional[str] = None
    performance_level: Optional[str] = None
    is_thinking: bool = False
    is_active: bool
    
    class Config:
        from_attributes = True

class UserLLMConfigCreate(BaseModel):
    provider_id: int
    config_name: str
    api_key: str
    base_url: Optional[str] = None
    default_temperature: float = 0.7
    default_max_tokens: Optional[int] = None

class UserLLMConfigResponse(BaseModel):
    id: int
    user_id: int
    provider_id: int
    config_name: str
    base_url: Optional[str] = None
    default_temperature: float
    default_max_tokens: Optional[int] = None
    is_active: bool
    is_validated: bool
    last_validated_at: Optional[datetime] = None
    validation_error: Optional[str] = None
    
    class Config:
        from_attributes = True

class LLMModelConfig(BaseModel):
    id: int
    user_id: int
    model_id: int
    config_name: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    
    class Config:
        from_attributes = True

class LLMProviderConfig(BaseModel):
    """LLM Provider Configuration"""
    provider_key: str
    display_name: str
    provider_type: str
    requires_api_key: bool = True
    requires_base_url: bool = False
    requires_custom_model_name: bool = False
    default_base_url: Optional[str] = None

