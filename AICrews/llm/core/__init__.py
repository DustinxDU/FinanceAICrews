"""LLM 核心模块

提供配置加载、HTTP 客户端、异常处理等基础功能。
"""

from .config_models import (
    ProvidersConfig,
    PricingConfig,
    ProviderConfig,
    AuthConfig,
    EndpointsConfig,
    DiscoveryConfig,
    ModelPricing,
    AuthType,
    DiscoveryStrategy,
    ProviderType,
    ConfigStatus,
)

from .config_store import ConfigStore, get_config_store, reset_config_store

from .paths import (
    get_repo_root,
    get_config_root,
    get_llm_config_dir,
    get_model_tags_path,
    get_providers_path,
    get_pricing_path,
    clear_path_cache,
)

from .http_client import (
    HTTPClient,
    HTTPClientConfig,
    HTTPResponse,
    get_http_client,
    close_http_client,
)

from .env_redactor import (
    EnvRedactor,
    redact_api_key,
    redact_url,
    redact_headers,
    redact_dict,
    redact_text,
    safe_log_dict,
)

from .exceptions import (
    LLMModuleError,
    ConfigError,
    ConfigFileNotFoundError,
    ConfigValidationError,
    ProviderNotFoundError,
    ProviderConfigError,
    ModelNotFoundError,
    ModelDiscoveryError,
    ValidationError,
    APIError,
    AuthenticationError,
    RateLimitError,
    NetworkError,
    LLMFactoryError,
    DBSyncError,
    ErrorCode,
    format_error_response,
)

__all__ = [
    # Config Models
    'ProvidersConfig',
    'PricingConfig',
    'ProviderConfig',
    'AuthConfig',
    'EndpointsConfig',
    'DiscoveryConfig',
    'ModelPricing',
    'AuthType',
    'DiscoveryStrategy',
    'ProviderType',
    'ConfigStatus',
    
    # Config Store
    'ConfigStore',
    'get_config_store',
    'reset_config_store',
    
    # Paths
    'get_repo_root',
    'get_config_root',
    'get_llm_config_dir',
    'get_model_tags_path',
    'get_providers_path',
    'get_pricing_path',
    'clear_path_cache',
    
    # HTTP Client
    'HTTPClient',
    'HTTPClientConfig',
    'HTTPResponse',
    'get_http_client',
    'close_http_client',
    
    # Env Redactor
    'EnvRedactor',
    'redact_api_key',
    'redact_url',
    'redact_headers',
    'redact_dict',
    'redact_text',
    'safe_log_dict',
    
    # Exceptions
    'LLMModuleError',
    'ConfigError',
    'ConfigFileNotFoundError',
    'ConfigValidationError',
    'ProviderNotFoundError',
    'ProviderConfigError',
    'ModelNotFoundError',
    'ModelDiscoveryError',
    'ValidationError',
    'APIError',
    'AuthenticationError',
    'RateLimitError',
    'NetworkError',
    'LLMFactoryError',
    'DBSyncError',
    'ErrorCode',
    'format_error_response',
]
