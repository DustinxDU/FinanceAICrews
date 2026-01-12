"""配置存储模块

加载、校验、缓存 YAML 配置文件，支持热更新。
"""

import os
import yaml
import threading
from AICrews.observability.logging import get_logger
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from pathlib import Path

from .paths import (
    get_providers_path,
    get_pricing_path,
)
from .config_models import (
    ProvidersConfig,
    PricingConfig,
    ConfigStatus,
)
from .exceptions import (
    ConfigError,
    ConfigFileNotFoundError,
    ConfigValidationError,
)

logger = get_logger(__name__)


class ConfigStore:
    """配置存储类。
    
    负责加载、校验、缓存配置文件，提供热更新能力。
    """
    
    def __init__(self, auto_reload: bool = False):
        """初始化配置存储。
        
        Args:
            auto_reload: 是否自动重新加载（基于 mtime）
        """
        self._lock = threading.RLock()
        self._providers_config: Optional[ProvidersConfig] = None
        self._pricing_config: Optional[PricingConfig] = None
        
        # 状态追踪
        self._providers_mtime: Optional[float] = None
        self._pricing_mtime: Optional[float] = None
        
        self._last_reload_time: Optional[datetime] = None
        self._reload_count = 0
        
        self._auto_reload = auto_reload
        self._reload_callbacks: list[Callable] = []
        
        # 初始加载
        self.reload()
    
    def register_reload_callback(self, callback: Callable) -> None:
        """注册重新加载回调。
        
        Args:
            callback: 回调函数
        """
        with self._lock:
            self._reload_callbacks.append(callback)
    
    def reload(self) -> ConfigStatus:
        """重新加载所有配置文件。
        
        Returns:
            ConfigStatus: 配置状态
        """
        with self._lock:
            logger.info("Reloading LLM configuration...")
            
            # 加载 providers.yaml
            providers_path = get_providers_path()
            if providers_path.exists():
                try:
                    self._providers_config = self._load_providers_config(providers_path)
                    self._providers_mtime = providers_path.stat().st_mtime
                    logger.info(f"Loaded providers config from {providers_path}")
                except Exception as e:
                    logger.error(f"Failed to load providers config: {e}")
                    raise
            else:
                raise ConfigFileNotFoundError(
                    f"Providers config file not found: {providers_path}"
                )
            
            # 加载 pricing.yaml
            pricing_path = get_pricing_path()
            if pricing_path.exists():
                try:
                    self._pricing_config = self._load_pricing_config(pricing_path)
                    self._pricing_mtime = pricing_path.stat().st_mtime
                    logger.info(f"Loaded pricing config from {pricing_path}")
                except Exception as e:
                    logger.warning(f"Failed to load pricing config: {e}")
                    self._pricing_config = None
            else:
                logger.warning(f"Pricing config file not found: {pricing_path}")
                self._pricing_config = None
            
            # 更新状态
            self._last_reload_time = datetime.now()
            self._reload_count += 1
            
            # 触发回调
            for callback in self._reload_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Reload callback failed: {e}")
            
            status = self.status()
            logger.info(
                f"Configuration reloaded: {status.providers_count} providers, "
                f"reload #{self._reload_count}"
            )
            
            return status
    
    def _load_providers_config(self, path: Path) -> ProvidersConfig:
        """加载提供商配置。
        
        Args:
            path: 配置文件路径
            
        Returns:
            ProvidersConfig: 解析后的配置
            
        Raises:
            ConfigValidationError: 配置校验失败
        """
        with open(path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
        
        if not raw_config:
            raise ConfigValidationError("Providers config is empty")
        
        config = ProvidersConfig(**raw_config)
        return config
    
    def _load_pricing_config(self, path: Path) -> PricingConfig:
        """加载定价配置。
        
        Args:
            path: 配置文件路径
            
        Returns:
            PricingConfig: 解析后的配置
        """
        with open(path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
        
        if not raw_config:
            return PricingConfig()
        
        return PricingConfig(**raw_config)
    
    def check_for_updates(self) -> bool:
        """检查配置是否有更新。
        
        Returns:
            bool: 是否有更新
        """
        with self._lock:
            providers_path = get_providers_path()
            pricing_path = get_pricing_path()
            
            # 检查任何配置文件是否修改
            if (
                (providers_path.exists() and 
                 self._providers_mtime != providers_path.stat().st_mtime)
                or (pricing_path.exists() and 
                    self._pricing_mtime != pricing_path.stat().st_mtime)
            ):
                return True
            
            return False
    
    @property
    def providers(self) -> ProvidersConfig:
        """获取提供商配置。"""
        with self._lock:
            if self._providers_config is None:
                raise ConfigError("Providers config not loaded")
            return self._providers_config
    
    @property
    def pricing(self) -> PricingConfig:
        """获取定价配置。"""
        with self._lock:
            if self._pricing_config is None:
                return PricingConfig()
            return self._pricing_config
    
    def get_provider(self, provider_key: str) -> Optional[Any]:
        """获取指定提供商配置。
        
        Args:
            provider_key: 提供商键
            
        Returns:
            ProviderConfig 或 None
        """
        with self._lock:
            return self.providers.providers.get(provider_key)
    
    def list_provider_keys(self) -> list[str]:
        """列出所有提供商键。"""
        with self._lock:
            return list(self.providers.providers.keys())
    
    def status(self) -> ConfigStatus:
        """获取配置状态。"""
        with self._lock:
            return ConfigStatus(
                providers_path=str(get_providers_path()),
                providers_loaded=self._providers_config is not None,
                providers_count=len(self.providers.providers) if self._providers_config else 0,
                pricing_path=str(get_pricing_path()),
                pricing_loaded=self._pricing_config is not None,
                last_reload_time=self._last_reload_time,
                reload_count=self._reload_count,
            )
    
    def get_price(self, provider_key: str, model_key: str) -> Optional[Dict[str, float]]:
        """获取模型定价。

        Args:
            provider_key: 提供商键
            model_key: 模型键

        Returns:
            包含 input/output 的字典或 None
        """
        with self._lock:
            price = self.pricing.get_price(provider_key, model_key)
            if price:
                return {"input": price.input, "output": price.output}
            return None

    def get_model_tag(self, model_key: str) -> Optional[Any]:
        """获取模型标签。

        Args:
            model_key: 模型键

        Returns:
            ModelTag 或 None（当前未实现 model_tags.yaml）
        """
        # TODO: 实现 model_tags.yaml 加载
        return None


# 全局配置存储实例
_config_store: Optional[ConfigStore] = None


def get_config_store() -> ConfigStore:
    """获取全局配置存储实例。"""
    global _config_store
    if _config_store is None:
        _config_store = ConfigStore()
    return _config_store


def reset_config_store() -> None:
    """重置配置存储（主要用于测试）。"""
    global _config_store
    _config_store = None
