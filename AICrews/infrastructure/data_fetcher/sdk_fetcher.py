"""
SDK Fetcher Base - 数据获取抽象层

提供统一的数据获取接口:
- YFinanceFetcher: 美股、加密货币
- AkShareFetcher: A股、港股

Philosophy: SDK 优先，失败则抛出异常，不做 fallback
"""

from AICrews.observability.logging import get_logger
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = get_logger(__name__)


class SDKFetcherBase(ABC):
    """SDK 数据获取器基类"""

    @abstractmethod
    async def fetch_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取实时价格"""
        pass

    @abstractmethod
    async def fetch_history(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> Optional[List[Dict[str, Any]]]:
        """获取历史数据"""
        pass

    @abstractmethod
    async def fetch_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取报价信息"""
        pass


class MarketType:
    """市场类型枚举"""

    US = "US"
    HK = "HK"
    CN = "CN"
    CRYPTO = "CRYPTO"
    MACRO = "MACRO"


def detect_market(ticker: str) -> str:
    """
    检测股票代码所属市场

    Examples:
        "AAPL" -> US
        "0700.HK" -> HK
        "600000.SS" -> CN
        "BTC-USD" -> CRYPTO
    """
    ticker_upper = ticker.upper()

    # 加密货币
    if "-USD" in ticker_upper or ticker_upper.endswith("USDT"):
        return MarketType.CRYPTO

    # 港股
    if ticker_upper.endswith(".HK"):
        return MarketType.HK

    # A股
    if ticker_upper.endswith(".SS") or ticker_upper.endswith(".SZ"):
        return MarketType.CN

    # 宏观指标 (放在美股检测之前，确保优先匹配)
    if ticker_upper in ["US10Y", "DXY", "VIX", "GOLD", "SPX", "NDX", "HSI"]:
        return MarketType.MACRO

    # 美股 (纯字母，2-5位，但排除已匹配的宏观指标)
    if ticker_upper.isalpha() and 1 <= len(ticker_upper) <= 5:
        return MarketType.US

    # 默认美股
    return MarketType.US


def get_fetcher_for_market(market: str) -> SDKFetcherBase:
    """根据市场类型获取对应的 Fetcher"""
    from .yfinance_fetcher import YFinanceFetcher
    from .akshare_fetcher import AkShareFetcher

    if market in [MarketType.US, MarketType.CRYPTO, MarketType.MACRO]:
        return YFinanceFetcher()
    elif market in [MarketType.HK, MarketType.CN]:
        return AkShareFetcher()
    else:
        return YFinanceFetcher()


def get_fetcher_for_ticker(ticker: str) -> SDKFetcherBase:
    """根据股票代码自动选择 Fetcher"""
    market = detect_market(ticker)
    return get_fetcher_for_market(market)
