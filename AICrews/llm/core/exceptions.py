"""统一异常模块

定义 LLM 模块相关的异常类型。
"""

from typing import Any, Dict, Optional
from enum import Enum


class LLMModuleError(Exception):
    """LLM 模块基础异常类。"""
    
    def __init__(
        self,
        message: str,
        provider_key: Optional[str] = None,
        model_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.provider_key = provider_key
        self.model_key = model_key
        self.details = details or {}
    
    def __str__(self) -> str:
        return self.message


class ConfigError(LLMModuleError):
    """配置相关错误。"""
    pass


class ConfigFileNotFoundError(ConfigError):
    """配置文件未找到。"""
    pass


class ConfigValidationError(ConfigError):
    """配置校验失败。"""
    pass


class ProviderNotFoundError(LLMModuleError):
    """提供商不存在。"""
    pass


class ProviderConfigError(LLMModuleError):
    """提供商配置错误。"""
    pass


class ModelNotFoundError(LLMModuleError):
    """模型不存在。"""
    pass


class ModelDiscoveryError(LLMModuleError):
    """模型发现失败。"""
    pass


class ValidationError(LLMModuleError):
    """验证失败。"""
    pass


class APIError(LLMModuleError):
    """API 调用错误。"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        provider_key: Optional[str] = None,
        model_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, provider_key, model_key, details)
        self.status_code = status_code


class AuthenticationError(APIError):
    """认证失败。"""
    pass


class RateLimitError(APIError):
    """速率限制错误。"""
    pass


class NetworkError(APIError):
    """网络错误。"""
    pass


class LLMFactoryError(LLMModuleError):
    """LLM 工厂错误。"""
    pass


class DBSyncError(LLMModuleError):
    """数据库同步错误。"""
    pass


class ErrorCode(Enum):
    """错误代码枚举。"""
    
    # 配置错误 (1xxx)
    CONFIG_FILE_NOT_FOUND = "CONFIG_001"
    CONFIG_VERSION_MISMATCH = "CONFIG_002"
    CONFIG_VALIDATION_FAILED = "CONFIG_003"
    
    # 提供商错误 (2xxx)
    PROVIDER_NOT_FOUND = "PROVIDER_001"
    PROVIDER_CONFIG_INVALID = "PROVIDER_002"
    PROVIDER_AUTH_FAILED = "PROVIDER_003"
    
    # 模型错误 (3xxx)
    MODEL_NOT_FOUND = "MODEL_001"
    MODEL_DISCOVERY_FAILED = "MODEL_002"
    MODEL_VALIDATION_FAILED = "MODEL_003"
    
    # API 错误 (4xxx)
    API_REQUEST_FAILED = "API_001"
    API_AUTH_FAILED = "API_002"
    API_RATE_LIMITED = "API_003"
    API_TIMEOUT = "API_004"
    API_NETWORK_ERROR = "API_005"
    
    # 工厂错误 (5xxx)
    FACTORY_CREATE_FAILED = "FACTORY_001"
    FACTORY_INVALID_PARAMS = "FACTORY_002"
    
    # DB 同步错误 (6xxx)
    DB_SYNC_FAILED = "DB_001"
    DB_CONNECTION_FAILED = "DB_002"


def format_error_response(error: Exception) -> Dict[str, Any]:
    """格式化错误响应。
    
    Args:
        error: 异常对象
        
    Returns:
        Dict: 格式化的错误响应
    """
    if isinstance(error, LLMModuleError):
        return {
            "success": False,
            "error": {
                "message": error.message,
                "provider_key": error.provider_key,
                "model_key": error.model_key,
                "details": error.details,
            }
        }
    
    return {
        "success": False,
        "error": {
            "message": str(error),
            "type": type(error).__name__,
        }
    }
