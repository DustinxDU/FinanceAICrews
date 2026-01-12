"""
市场映射配置加载器
Market Mappings Configuration Loader

从 YAML 配置文件加载市场数据映射，提供类型安全的访问接口。
Loads market data mappings from YAML configuration file with type-safe access.

用法 Usage:
    from AICrews.config.market_mappings import get_market_mappings

    mappings = get_market_mappings()
    gold_symbol = mappings.commodity_futures.get("GOLD")  # "GC=F"

兼容性函数 Compatibility functions (for gradual migration):
    from AICrews.config.market_mappings import (
        get_commodity_futures_map,
        get_crypto_map,
        get_market_suffix_map,
        get_asset_type_labels,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
import threading

import yaml

from AICrews.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MarketMappings:
    """
    市场映射数据类
    Market Mappings Data Class

    包含所有市场数据映射的不可变数据容器。
    Immutable container for all market data mappings.
    """

    commodity_futures: Dict[str, str] = field(default_factory=dict)
    crypto: Dict[str, str] = field(default_factory=dict)
    market_suffix: Dict[str, str] = field(default_factory=dict)
    asset_type_labels: Dict[str, Dict[str, str]] = field(default_factory=dict)
    yfinance_macro_symbols: Dict[str, str] = field(default_factory=dict)
    market_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class MarketMappingsLoader:
    """
    市场映射加载器（单例模式）
    Market Mappings Loader (Singleton Pattern)

    从 YAML 配置文件加载市场映射并提供缓存的单例访问。
    Loads market mappings from YAML config file and provides cached singleton access.
    """

    _instance: Optional[MarketMappings] = None
    _lock = threading.Lock()
    _config_path: Optional[Path] = None

    @classmethod
    def get_config_path(cls) -> Path:
        """
        获取配置文件路径
        Get the configuration file path

        Returns:
            Path: 配置文件的绝对路径
        """
        if cls._config_path is None:
            # 默认配置文件路径：项目根目录/config/market_mappings.yaml
            # Default config path: project_root/config/market_mappings.yaml
            cls._config_path = (
                Path(__file__).parent.parent.parent / "config" / "market_mappings.yaml"
            )
        return cls._config_path

    @classmethod
    def set_config_path(cls, path: Path) -> None:
        """
        设置配置文件路径（用于测试）
        Set the configuration file path (for testing)

        Args:
            path: 配置文件路径
        """
        with cls._lock:
            cls._config_path = path
            cls._instance = None  # 重置实例以重新加载

    @classmethod
    def load(cls) -> MarketMappings:
        """
        加载市场映射配置（单例）
        Load market mappings configuration (singleton)

        Returns:
            MarketMappings: 市场映射数据类实例

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析错误
        """
        if cls._instance is not None:
            return cls._instance

        with cls._lock:
            # Double-check locking pattern
            if cls._instance is not None:
                return cls._instance

            config_path = cls.get_config_path()

            if not config_path.exists():
                raise FileNotFoundError(
                    f"Market mappings config file not found: {config_path}"
                )

            logger.info(f"Loading market mappings from: {config_path}")

            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            cls._instance = MarketMappings(
                commodity_futures=data.get("commodity_futures", {}),
                crypto=data.get("crypto", {}),
                market_suffix=data.get("market_suffix", {}),
                asset_type_labels=data.get("asset_type_labels", {}),
                yfinance_macro_symbols=data.get("yfinance_macro_symbols", {}),
                market_config=data.get("market_config", {}),
            )

            logger.info(
                f"Market mappings loaded: "
                f"{len(cls._instance.commodity_futures)} commodity futures, "
                f"{len(cls._instance.crypto)} crypto, "
                f"{len(cls._instance.market_suffix)} market suffixes, "
                f"{len(cls._instance.asset_type_labels)} asset type labels"
            )

            return cls._instance

    @classmethod
    def reload(cls) -> MarketMappings:
        """
        强制重新加载配置
        Force reload configuration

        Returns:
            MarketMappings: 新加载的市场映射数据类实例
        """
        with cls._lock:
            cls._instance = None
        return cls.load()

    @classmethod
    def reset(cls) -> None:
        """
        重置加载器状态（用于测试）
        Reset loader state (for testing)
        """
        with cls._lock:
            cls._instance = None
            cls._config_path = None


# =============================================================================
# 公共 API / Public API
# =============================================================================


def get_market_mappings() -> MarketMappings:
    """
    获取市场映射配置（推荐使用）
    Get market mappings configuration (recommended)

    Returns:
        MarketMappings: 市场映射数据类实例

    Example:
        >>> mappings = get_market_mappings()
        >>> mappings.commodity_futures.get("GOLD")
        'GC=F'
    """
    return MarketMappingsLoader.load()


# =============================================================================
# 兼容性函数 / Compatibility Functions
# 这些函数用于从 market_service.py 逐步迁移
# These functions are for gradual migration from market_service.py
# =============================================================================


def get_commodity_futures_map() -> Dict[str, str]:
    """
    获取商品期货映射（兼容性函数）
    Get commodity futures mapping (compatibility function)

    Returns:
        Dict[str, str]: 商品名称到 yfinance 符号的映射
    """
    return get_market_mappings().commodity_futures


def get_crypto_map() -> Dict[str, str]:
    """
    获取加密货币映射（兼容性函数）
    Get crypto mapping (compatibility function)

    Returns:
        Dict[str, str]: 加密货币名称到 yfinance 符号的映射
    """
    return get_market_mappings().crypto


def get_market_suffix_map() -> Dict[str, str]:
    """
    获取市场后缀映射（兼容性函数）
    Get market suffix mapping (compatibility function)

    Returns:
        Dict[str, str]: 市场代码到后缀的映射
    """
    return get_market_mappings().market_suffix


def get_asset_type_labels() -> Dict[str, tuple]:
    """
    获取资产类型标签（元组格式，兼容 market_service.py）
    Get asset type labels (tuple format, compatible with market_service.py)

    Returns:
        Dict mapping market code to (region, exchange, currency) tuple

    Example:
        >>> labels = get_asset_type_labels()
        >>> labels["US"]
        ('US', 'NYSE/NASDAQ', 'USD')
        >>> labels["US"][0]  # region
        'US'
    """
    mappings = get_market_mappings()
    result = {}
    for key, label_dict in mappings.asset_type_labels.items():
        result[key] = (
            label_dict.get("region", ""),
            label_dict.get("exchange", ""),
            label_dict.get("currency", ""),
        )
    return result


def get_yfinance_macro_symbols() -> Dict[str, str]:
    """
    获取 YFinance 宏观指标符号映射（兼容性函数）
    Get YFinance macro symbols mapping (compatibility function)

    Returns:
        Dict[str, str]: 宏观指标名称到 yfinance 符号的映射
    """
    return get_market_mappings().yfinance_macro_symbols


def get_market_config() -> Dict[str, Dict[str, Any]]:
    """
    获取市场配置（兼容性函数）
    Get market configuration (compatibility function)

    Returns:
        Dict[str, Dict[str, Any]]: 市场代码到配置信息的映射
    """
    return get_market_mappings().market_config


# =============================================================================
# 模块导出 / Module Exports
# =============================================================================

__all__ = [
    # 数据类
    "MarketMappings",
    # 加载器
    "MarketMappingsLoader",
    # 主要 API
    "get_market_mappings",
    # 兼容性函数
    "get_commodity_futures_map",
    "get_crypto_map",
    "get_market_suffix_map",
    "get_asset_type_labels",
    "get_yfinance_macro_symbols",
    "get_market_config",
]
