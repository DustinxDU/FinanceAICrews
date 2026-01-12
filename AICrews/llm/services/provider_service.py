"""Provider 服务模块

面向前端/UI 的 Provider 列表服务。
"""

import os
from AICrews.observability.logging import get_logger
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from AICrews.llm.core.config_store import get_config_store
from AICrews.llm.core.config_models import ProviderConfig, ProviderType

logger = get_logger(__name__)


@dataclass
class ProviderInfo:
    """提供商信息（面向前端）。"""
    provider_key: str
    display_name: str
    provider_type: str
    requires_api_key: bool = True
    requires_base_url: bool = False
    requires_custom_model_name: bool = False
    requires_endpoint_config: bool = False
    default_base_url: Optional[str] = None
    is_china_provider: bool = False
    has_env_config: bool = False
    auth_type: str = "bearer"
    env_key: Optional[str] = None
    capabilities: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = {}


class ProviderService:
    """提供商服务。
    
    负责从 ConfigStore 读取 provider spec，生成 UI 需要的字段。
    """
    
    # 中国 API 提供商 keys（明确列出，不依赖 provider_type）
    CHINA_PROVIDER_KEYS = {
        "zhipu_ai", "kimi_moonshot", "qianwen_dashscope", "volcengine", "deepseek"
    }
    
    def __init__(self):
        """初始化提供商服务。"""
        self._config_store = get_config_store()
    
    def list_providers(self) -> List[ProviderInfo]:
        """获取所有提供商信息。
        
        Returns:
            List[ProviderInfo]: 提供商信息列表
        """
        providers = []
        for provider_key, provider_config in self._config_store.providers.providers.items():
            provider_info = self._build_provider_info(provider_key, provider_config)
            providers.append(provider_info)
        
        return providers
    
    def get_provider(self, provider_key: str) -> Optional[ProviderInfo]:
        """获取指定提供商信息。
        
        Args:
            provider_key: 提供商键
            
        Returns:
            ProviderInfo 或 None
        """
        provider_config = self._config_store.get_provider(provider_key)
        if not provider_config:
            return None
        
        return self._build_provider_info(provider_key, provider_config)
    
    def _build_provider_info(
        self, 
        provider_key: str, 
        provider_config: ProviderConfig
    ) -> ProviderInfo:
        """构建提供商信息。
        
        Args:
            provider_key: 提供商键
            provider_config: 提供商配置
            
        Returns:
            ProviderInfo: 提供商信息
        """
        # 判断是否需要 base_url
        requires_base_url = (
            provider_config.endpoints.requires_base_url or
            provider_config.provider_type == ProviderType.OPENAI_COMPATIBLE
        )
        
        # 判断是否为火山引擎特殊类型
        is_volcengine = provider_key == "volcengine"
        
        # 判断是否为中国提供商（仅通过明确的 key 列表判断）
        is_china = provider_key in self.CHINA_PROVIDER_KEYS
        
        # 检查环境变量配置
        env_key = provider_config.auth.api_key_env
        has_env_config = bool(env_key and os.getenv(env_key))
        
        return ProviderInfo(
            provider_key=provider_key,
            display_name=provider_config.display_name,
            provider_type=provider_config.provider_type.value,
            requires_api_key=True,
            requires_base_url=requires_base_url,
            requires_custom_model_name=(
                provider_config.requires_custom_model_name or is_volcengine
            ),
            requires_endpoint_config=(
                provider_config.discovery.enabled == False and
                provider_config.provider_type in [
                    ProviderType.OPENAI_COMPATIBLE,
                    ProviderType.VOLCENGINE
                ]
            ),
            default_base_url=provider_config.endpoints.api_base or None,
            is_china_provider=is_china,
            has_env_config=has_env_config,
            auth_type=provider_config.auth.type.value,
            env_key=env_key or None,
            capabilities={
                "supports_dynamic_models": provider_config.discovery.enabled,
                "supports_model_validation": True,
                "auto_discover_models": provider_config.discovery.enabled,
            },
        )
    
    def list_china_providers(self) -> List[ProviderInfo]:
        """获取中国提供商列表。
        
        Returns:
            List[ProviderInfo]: 中国提供商信息列表
        """
        return [
            p for p in self.list_providers()
            if p.is_china_provider
        ]
    
    def list_international_providers(self) -> List[ProviderInfo]:
        """获取国际提供商列表。
        
        Returns:
            List[ProviderInfo]: 国际提供商信息列表
        """
        return [
            p for p in self.list_providers()
            if not p.is_china_provider
        ]
    
    def get_provider_for_creation(self, provider_key: str) -> Dict[str, Any]:
        """获取用于创建 LLM 配置的提供商信息。
        
        Args:
            provider_key: 提供商键
            
        Returns:
            Dict: 用于前端表单的提供商信息
        """
        provider_info = self.get_provider(provider_key)
        if not provider_info:
            return {}
        
        return {
            "provider_key": provider_info.provider_key,
            "display_name": provider_info.display_name,
            "requires_base_url": provider_info.requires_base_url,
            "requires_custom_model_name": provider_info.requires_custom_model_name,
            "requires_endpoint_config": provider_info.requires_endpoint_config,
            "default_base_url": provider_info.default_base_url,
            "auth_type": provider_info.auth_type,
            "env_key": provider_info.env_key,
        }
    
    def get_model_prefix(self, provider_key: str) -> str:
        """获取提供商的模型前缀。
        
        Args:
            provider_key: 提供商键
            
        Returns:
            str: 模型前缀
        """
        provider_config = self._config_store.get_provider(provider_key)
        if provider_config:
            return provider_config.llm_model_prefix
        return ""
    
    def validate_provider_key(self, provider_key: str) -> bool:
        """验证提供商键是否有效。
        
        Args:
            provider_key: 提供商键
            
        Returns:
            bool: 是否有效
        """
        return provider_key in self._config_store.list_provider_keys()


# 全局服务实例
_provider_service: Optional[ProviderService] = None


def get_provider_service() -> ProviderService:
    """获取全局提供商服务实例。"""
    global _provider_service
    if _provider_service is None:
        _provider_service = ProviderService()
    return _provider_service


def reset_provider_service() -> None:
    """重置提供商服务（主要用于测试）。"""
    global _provider_service
    _provider_service = None
