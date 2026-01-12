"""配置模型模块

使用 Pydantic 定义 providers.yaml 和 pricing.yaml 的 schema。
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime


class AuthType(str, Enum):
    """认证类型枚举。"""
    BEARER = "bearer"
    QUERY_PARAM = "query_param"
    BASIC = "basic"
    AWS_CREDENTIALS = "aws_credentials"
    GCP_SERVICE_ACCOUNT = "gcp_service_account"
    API_KEY_HEADER = "api_key_header"


class DiscoveryStrategy(str, Enum):
    """模型发现策略枚举。"""
    OPENAI_MODELS = "openai_models"
    ANTHROPIC_MODELS = "anthropic_models"
    GEMINI_MODELS = "gemini_models"
    OLLAMA_MODELS = "ollama_models"
    HUGGINGFACE_MODELS = "huggingface_models"
    CUSTOM = "custom"
    DISABLED = "disabled"


class ProviderType(str, Enum):
    """提供商类型枚举。"""
    CREWAI_NATIVE = "crewai_native"
    OPENAI_COMPATIBLE = "openai_compatible"
    VOLCENGINE = "volcengine"
    CUSTOM = "custom"


class AuthConfig(BaseModel):
    """认证配置。"""
    type: AuthType = AuthType.BEARER
    api_key_env: str = ""
    query_param_key: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)


class EndpointsConfig(BaseModel):
    """端点配置。"""
    api_base: str = ""
    models_path: str = "/models"
    requires_base_url: bool = False


class DiscoveryConfig(BaseModel):
    """发现配置。"""
    enabled: bool = True
    strategy: DiscoveryStrategy = DiscoveryStrategy.OPENAI_MODELS
    cache_ttl_seconds: int = 3600


class ProviderCapabilities(BaseModel):
    """提供商能力标志。

    用于指示提供商支持哪些特性，影响结构化输出等功能的降级策略。
    """
    supports_function_calling: bool = False
    supports_json_schema: bool = False  # OpenAI Structured Outputs
    supports_json_mode: bool = False    # JSON-only mode / json_object


class ProviderConfig(BaseModel):
    """提供商配置。"""
    display_name: str
    provider_type: ProviderType
    llm_model_prefix: str = ""
    requires_custom_model_name: bool = False
    auth: AuthConfig = Field(default_factory=AuthConfig)
    endpoints: EndpointsConfig = Field(default_factory=EndpointsConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)
    
    @model_validator(mode='after')
    def validate_provider_config(self):
        """验证提供商配置。"""
        if not self.llm_model_prefix and self.provider_type in [
            ProviderType.CREWAI_NATIVE, ProviderType.OPENAI_COMPATIBLE
        ]:
            raise ValueError(
                f"Provider '{self.display_name}' requires llm_model_prefix "
                f"for type {self.provider_type}"
            )
        return self


class ProvidersConfig(BaseModel):
    """提供商配置根模型。"""
    version: str = "4.0"
    updated: str = ""
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    
    @field_validator('updated', mode='before')
    @classmethod
    def parse_updated(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class ModelPricing(BaseModel):
    """模型定价。"""
    input: float = 0.0  # USD / 1M tokens
    output: float = 0.0  # USD / 1M tokens


class ProviderPricing(BaseModel):
    """提供商定价。"""
    models: Dict[str, ModelPricing] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def coerce_provider_pricing(cls, data: Any) -> Any:
        """Support pricing.yaml shape: {provider: {model: {input, output}}}.

        Historically, pricing.yaml stores models directly under provider keys,
        without an explicit "models:" nesting. This validator normalizes that
        input into ProviderPricing(models=...).
        """
        if data is None:
            return {}
        if isinstance(data, dict) and "models" not in data:
            return {"models": data}
        return data


class PricingConfig(BaseModel):
    """定价配置根模型。"""
    version: str = "2025-12"
    updated: str = ""
    pricing: Dict[str, ProviderPricing] = Field(default_factory=dict)
    
    @field_validator('updated', mode='before')
    @classmethod
    def parse_updated(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v
    
    def get_price(
        self, 
        provider_key: str, 
        model_key: str
    ) -> Optional[ModelPricing]:
        """获取指定模型的定价。
        
        Args:
            provider_key: 提供商键
            model_key: 模型键
            
        Returns:
            ModelPricing 或 None
        """
        provider_pricing = self.pricing.get(provider_key)
        if not provider_pricing:
            return None

        # Primary lookup: exact key
        price = provider_pricing.models.get(model_key)
        if price:
            return price

        # Fallback: strip provider prefix when model keys are namespaced
        # e.g. "openai/gpt-4o-mini" -> "gpt-4o-mini"
        prefix = f"{provider_key}/"
        if model_key.startswith(prefix):
            return provider_pricing.models.get(model_key[len(prefix) :])

        return None


class ConfigStatus(BaseModel):
    """配置状态。"""
    providers_path: str
    providers_loaded: bool
    providers_count: int
    pricing_path: str
    pricing_loaded: bool
    last_reload_time: Optional[datetime] = None
    reload_count: int = 0
