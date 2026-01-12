"""
Market Service - 市场数据服务

提供资产、行情、价格等市场数据相关的业务逻辑。
包含全球市场指数、Cockpit 宏观指标的缓存和获取逻辑。
"""

from __future__ import annotations

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .base import BaseService
from AICrews.database.models.market import (
    Asset,
    RealtimeQuote,
    StockPrice,
    FundamentalData,
    FinancialStatement,
    TechnicalIndicator,
    MarketNews,
    InsiderActivity,
    ActiveMonitoring,
)
from AICrews.database.models.user import UserPortfolio
from AICrews.database.models import UserCockpitIndicator
from AICrews.database.models.cockpit import MacroIndicatorCache
from AICrews.schemas.market import (
    AssetCreate,
    AssetResponse,
    RealtimeQuoteUpdate,
    MarketIndex,
    MarketDataResponse,
    CockpitMacroIndicator,
    CockpitMacroResponse,
)
from AICrews.schemas.portfolio import AssetSearchRequest, AssetSearchResult
from AICrews.infrastructure.cache.redis_manager import get_redis_manager
from AICrews.observability.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Unified Asset Search - Market Mappings (from config)
# =============================================================================
from AICrews.config.market_mappings import (
    get_commodity_futures_map,
    get_crypto_map,
    get_market_suffix_map,
    get_asset_type_labels,
    get_yfinance_macro_symbols,
)

# Compatibility aliases - load from config at module level
COMMODITY_FUTURES_MAP = get_commodity_futures_map()
CRYPTO_MAP = get_crypto_map()
MARKET_SUFFIX_MAP = get_market_suffix_map()
ASSET_TYPE_LABELS = get_asset_type_labels()
YFINANCE_SYMBOL_MAP = get_yfinance_macro_symbols()

COCKPIT_MACRO_REDIS_KEY = "cockpit:macro:all"

COCKPIT_MACRO_CONFIG = {
    "us10y": {
        "id": "us10y",
        "name": "US 10Y",
        "symbol": "US10Y",
        "yf_symbol": "^TNX",
        "type": "macro",
        "description": "美国10年期国债收益率",
        "default_value": "4.02%",
        "value_format": lambda x: f"{x:.2f}%" if x else "4.02%",
    },
    "dxy": {
        "id": "dxy",
        "name": "DXY",
        "symbol": "DXY",
        "yf_symbol": "DX-Y.NYB",
        "type": "macro",
        "description": "美元指数",
        "default_value": "102.4",
        "value_format": lambda x: f"{x:.1f}" if x else "102.4",
    },
    "gold": {
        "id": "gold",
        "name": "Gold",
        "symbol": "XAU/USD",
        "yf_symbol": "GC=F",
        "type": "commodity",
        "description": "黄金价格",
        "default_value": "$2,045",
        "value_format": lambda x: f"${x:,.0f}" if x else "$2,045",
    },
    "vix": {
        "id": "vix",
        "name": "VIX",
        "symbol": "VIX",
        "yf_symbol": "^VIX",
        "type": "index",
        "description": "恐慌指数",
        "default_value": "18.5",
        "critical": True,
        "value_format": lambda x: f"{x:.1f}" if x else "18.5",
    },
    "ndx": {
        "id": "ndx",
        "name": "NASDAQ",
        "symbol": "NDX",
        "yf_symbol": "^NDX",
        "type": "index",
        "description": "纳斯达克100指数",
        "default_value": "16,245",
        "value_format": lambda x: f"{x:,.0f}" if x else "16,245",
    },
    "spx": {
        "id": "spx",
        "name": "S&P 500",
        "symbol": "SPX",
        "yf_symbol": "^GSPC",
        "type": "index",
        "description": "标普500指数",
        "default_value": "5,022",
        "value_format": lambda x: f"{x:,.0f}" if x else "5,022",
    },
    "btc": {
        "id": "btc",
        "name": "BTC",
        "symbol": "BTC-USD",
        "yf_symbol": "BTC-USD",
        "type": "crypto",
        "description": "比特币",
        "default_value": "$64,200",
        "value_format": lambda x: f"${x:,.0f}" if x else "$64,200",
    },
    "eth": {
        "id": "eth",
        "name": "ETH",
        "symbol": "ETH-USD",
        "yf_symbol": "ETH-USD",
        "type": "crypto",
        "description": "以太坊",
        "default_value": "$3,450",
        "value_format": lambda x: f"${x:,.0f}" if x else "$3,450",
    },
    "hsi": {
        "id": "hsi",
        "name": "HSI",
        "symbol": "HSI",
        "yf_symbol": "^HSI",
        "type": "index",
        "description": "恒生指数",
        "default_value": "16,723",
        "value_format": lambda x: f"{x:,.0f}" if x else "16,723",
    },
}

# =============================================================================
# 市场配置
# =============================================================================

MARKET_CONFIG = {
    "NASDAQ": {
        "name": "NASDAQ",
        "symbol": "IXIC",
        "country": "US",
        "description": "纳斯达克综合指数",
        "color": "#00C805",
        "mcp_tool": "stock_us_spot_em",
    },
    "DJI": {
        "name": "DOW",
        "symbol": "DJI",
        "country": "US",
        "description": "道琼斯工业平均指数",
        "color": "#FF6B6B",
        "mcp_tool": "stock_us_spot_em",
    },
    "SPX": {
        "name": "S&P 500",
        "symbol": "SPX",
        "country": "US",
        "description": "标普 500 指数",
        "color": "#4ECDC4",
        "mcp_tool": "stock_us_spot_em",
    },
    "HSI": {
        "name": "HANG SENG",
        "symbol": "HSI",
        "country": "HK",
        "description": "恒生指数",
        "color": "#FFD93D",
        "mcp_tool": "stock_hk_spot_em",
    },
    "SSEC": {
        "name": "SSE",
        "symbol": "000001",
        "country": "CN",
        "description": "上证指数",
        "color": "#6BCB77",
        "mcp_tool": "stock_zh_index_spot_em",
    },
    "SZSE": {
        "name": "SZSE",
        "symbol": "399001",
        "country": "CN",
        "description": "深证成指",
        "color": "#4D96FF",
        "mcp_tool": "stock_zh_index_spot_em",
    },
    "N225": {
        "name": "NIKKEI",
        "symbol": "N225",
        "country": "JP",
        "description": "日经 225 指数",
        "color": "#FF85A1",
        "mcp_tool": "index_investing_global",
    },
    "KS11": {
        "name": "KOSPI",
        "symbol": "KS11",
        "country": "KR",
        "description": "韩国综合指数",
        "color": "#A8E6CF",
        "mcp_tool": "index_investing_global",
    },
    "FTSE": {
        "name": "FTSE",
        "symbol": "FTSE",
        "country": "UK",
        "description": "富时 100 指数",
        "color": "#DDA0DD",
        "mcp_tool": "index_investing_global",
    },
    "DAX": {
        "name": "DAX",
        "symbol": "DAX",
        "country": "DE",
        "description": "德国 DAX 指数",
        "color": "#98D8C8",
        "mcp_tool": "index_investing_global",
    },
}

# =============================================================================
# 缓存管理
# =============================================================================


class MarketDataCache:
    """市场数据缓存"""

    def __init__(self, ttl_seconds: int = 300):  # 5 minutes
        self._data: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._ttl = ttl_seconds
        self._update_lock = asyncio.Lock()
        self._updating = False

    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        if self._last_update is None:
            return True
        elapsed = (datetime.now() - self._last_update).total_seconds()
        return elapsed > self._ttl

    async def get_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """获取市场数据（自动更新）"""
        async with self._update_lock:
            if self._updating:
                # 等待正在进行的更新
                while self._updating:
                    await asyncio.sleep(0.1)
                return self._data

            if self.is_expired() or force_refresh:
                self._updating = True
                try:
                    self._data = await self._fetch_all_markets()
                    self._last_update = datetime.now()
                    logger.info(
                        f"Market data updated: {len(self._data.get('markets', []))} markets"
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch market data: {e}")
                    # 如果有缓存数据，返回旧数据
                    if not self._data:
                        self._data = {
                            "markets": [],
                            "last_updated": datetime.now().isoformat(),
                        }
                finally:
                    self._updating = False

            return self._data

    async def _fetch_all_markets(self) -> Dict[str, Any]:
        """获取所有市场数据"""
        markets = []

        for code, config in MARKET_CONFIG.items():
            try:
                # _fetch_single_market 内部已经处理了数据源选择逻辑
                # 它会根据 country 自动选择 akshare 或 yfinance
                market_data = await self._fetch_single_market(None, code, config)
                markets.append(market_data)
            except Exception as e:
                logger.warning(f"Failed to fetch {code}: {e}")
                markets.append(self._get_mock_data(code, config))

        return {
            "markets": markets,
            "last_updated": datetime.now().isoformat(),
        }

    async def _fetch_single_market(
        self, mcp: Any, code: str, config: Dict[str, Any]
    ) -> MarketIndex:
        """获取单个市场数据"""
        country = config["country"]

        # A股和港股优先使用 akshare 库直接调用
        if country in ("CN", "HK"):
            try:
                market_data = await self._fetch_from_akshare_direct(code, config)
                if market_data.price > 0:
                    return market_data
            except Exception as e:
                logger.warning(f"Direct akshare call failed for {code}: {e}")

            # akshare 失败，尝试 yfinance
            try:
                return await self._fetch_from_yfinance_direct(code, config)
            except Exception as e:
                logger.warning(f"YFinance fallback failed for {code}: {e}")

        else:
            # 美股等其他市场优先使用 yfinance
            try:
                return await self._fetch_from_yfinance_direct(code, config)
            except Exception as e:
                logger.warning(f"YFinance call failed for {code}: {e}")

        # 返回模拟数据
        return self._get_mock_data(code, config)

    async def _fetch_from_akshare_direct(
        self, code: str, config: Dict[str, Any]
    ) -> MarketIndex:
        """直接使用 akshare 库获取市场数据（无需 MCP）"""
        country = config["country"]
        symbol = config["symbol"]

        def safe_float(value, default=0.0):
            try:
                val = float(value) if value is not None else default
                return default if (val != val) else val  # NaN check
            except (ValueError, TypeError):
                return default

        def fetch_data():
            try:
                import akshare as ak

                if country == "CN":
                    # 获取中国指数数据
                    df = ak.stock_zh_index_spot_em()
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            if str(row.get("代码", "")) == symbol:
                                price = safe_float(row.get("最新价"))
                                change = safe_float(row.get("涨跌额"))
                                change_pct = safe_float(row.get("涨跌幅"))
                                return {
                                    "price": price,
                                    "change": change,
                                    "change_percent": change_pct,
                                    "name": row.get("名称", config["name"]),
                                }

                elif country == "HK":
                    # 获取港股指数数据
                    df = ak.stock_hk_spot()
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            row_symbol = str(row.get("symbol", ""))
                            if symbol in row_symbol or row_symbol.endswith(symbol):
                                price = safe_float(row.get("lasttrade"))
                                prev_close = safe_float(row.get("prevclose"))
                                change = (
                                    price - prev_close if price and prev_close else 0
                                )
                                change_pct = (
                                    (change / prev_close * 100) if prev_close else 0
                                )
                                return {
                                    "price": price,
                                    "change": change,
                                    "change_percent": change_pct,
                                    "name": row.get("name", config["name"]),
                                }

            except Exception as e:
                logger.warning(f"akshare direct call failed: {e}")

            return None

        result = await asyncio.to_thread(fetch_data)

        if result and result["price"] > 0:
            return MarketIndex(
                code=code,
                name=result["name"],
                symbol=symbol,
                country=country,
                description=f"{result['name']} Index",
                color="green" if result["change_percent"] >= 0 else "red",
                price=result["price"],
                change=result["change"],
                change_percent=result["change_percent"],
                timestamp=datetime.now().isoformat(),
                is_up=result["change_percent"] >= 0,
            )

        return self._get_mock_data(code, config)

    async def _fetch_from_yfinance_direct(
        self, code: str, config: Dict[str, Any]
    ) -> MarketIndex:
        """直接使用 yfinance 获取市场数据"""
        country = config["country"]
        symbol = config["symbol"]

        # 转换符号格式
        yf_symbol = symbol
        if country == "CN":
            if symbol.startswith("0") or symbol.startswith("3"):
                yf_symbol = f"{symbol}.SZ"
            elif symbol.startswith("6"):
                yf_symbol = f"{symbol}.SS"
        elif country == "HK":
            yf_symbol = f"{symbol}.HK" if not symbol.endswith(".HK") else symbol
        elif country == "US":
            # 美股指数符号映射
            index_map = {"IXIC": "^IXIC", "DJI": "^DJI", "SPX": "^GSPC"}
            yf_symbol = index_map.get(symbol, symbol)
        elif country in ["JP", "KR", "UK", "DE"]:
            # 国际指数符号映射
            index_map = {
                "N225": "^N225",
                "KS11": "^KS11",
                "FTSE": "^FTSE",
                "DAX": "^GDAXI",
            }
            yf_symbol = index_map.get(symbol, f"^{symbol}")

        def fetch_data():
            try:
                import yfinance as yf

                ticker = yf.Ticker(yf_symbol)
                info = ticker.info

                if info:
                    price = info.get("regularMarketPrice") or info.get(
                        "previousClose", 0
                    )
                    prev_close = info.get("previousClose", 0)
                    change = price - prev_close if price and prev_close else 0
                    change_pct = (change / prev_close * 100) if prev_close else 0

                    return {
                        "price": float(price),
                        "change": change,
                        "change_percent": change_pct,
                        "name": info.get("longName", config["name"]),
                    }
            except Exception as e:
                logger.warning(f"yfinance direct call failed: {e}")

            return None

        result = await asyncio.to_thread(fetch_data)

        if result and result["price"] > 0:
            return MarketIndex(
                code=code,
                name=result["name"],
                symbol=symbol,
                country=country,
                description=f"{result['name']} Index",
                color="green" if result["change_percent"] >= 0 else "red",
                price=result["price"],
                change=result["change"],
                change_percent=result["change_percent"],
                timestamp=datetime.now().isoformat(),
                is_up=result["change_percent"] >= 0,
            )

        return self._get_mock_data(code, config)

    def _get_mock_data(self, code: str, config: Dict[str, Any]) -> MarketIndex:
        """获取模拟数据（当真实数据获取失败时使用）"""
        base_price = {
            "NASDAQ": 16245.32,
            "DJI": 40287.53,
            "SPX": 5021.84,
            "HSI": 16723.92,
            "SSEC": 2916.48,
            "SZSE": 8673.84,
            "N225": 38947.60,
            "KS11": 2692.51,
            "FTSE": 7682.30,
            "DAX": 17422.08,
        }.get(code, 10000)

        change = (random.random() - 0.5) * 100
        change_percent = (change / base_price) * 100

        return MarketIndex(
            code=code,
            name=config["name"],
            symbol=config["symbol"],
            country=config["country"],
            description=config["description"],
            color=config["color"],
            price=round(base_price + change, 2),
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            volume=None,
            timestamp=datetime.now().isoformat(),
            is_up=change >= 0,
        )


class CockpitMacroCache:
    """Cockpit 宏观指标缓存"""

    def __init__(self, ttl_seconds: int = 300):  # 5 minutes
        self._data: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._ttl = ttl_seconds
        self._update_lock = asyncio.Lock()
        self._updating = False

    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        if self._last_update is None:
            return True
        elapsed = (datetime.now() - self._last_update).total_seconds()
        return elapsed > self._ttl

    async def get_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """获取宏观数据（自动更新）"""
        async with self._update_lock:
            if self._updating:
                while self._updating:
                    await asyncio.sleep(0.1)
                return self._data

            if self.is_expired() or force_refresh:
                self._updating = True
                try:
                    self._data = await self._fetch_all_indicators()
                    self._last_update = datetime.now()
                    logger.info(
                        f"Cockpit macro data updated: {len(self._data.get('indicators', []))} indicators"
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch cockpit macro data: {e}")
                    if not self._data:
                        self._data = {
                            "indicators": [],
                            "last_updated": datetime.now().isoformat(),
                        }
                finally:
                    self._updating = False

            return self._data

    async def _fetch_all_indicators(self) -> Dict[str, Any]:
        """获取所有宏观指标"""
        indicators = []

        for code, config in COCKPIT_MACRO_CONFIG.items():
            try:
                indicator = await self._fetch_single_indicator(code, config)
                indicators.append(indicator)
            except Exception as e:
                logger.warning(f"Failed to fetch {code}: {e}")
                indicators.append(self._get_mock_indicator(code, config))

        return {
            "indicators": indicators,
            "last_updated": datetime.now().isoformat(),
        }

    async def _fetch_single_indicator(
        self, code: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """获取单个指标数据（直接使用 yfinance SDK）"""
        yf_symbol = config.get("yf_symbol", config["symbol"])
        value_format = config.get("value_format", lambda x: str(x))

        try:
            import yfinance as yf

            def fetch_quote():
                ticker = yf.Ticker(yf_symbol)
                try:
                    info = ticker.fast_info
                    return {
                        "price": getattr(info, "last_price", None) or 0,
                        "previous_close": getattr(info, "previous_close", None) or 0,
                    }
                except Exception:
                    # Fallback to info dict
                    info = ticker.info
                    return {
                        "price": info.get("regularMarketPrice", 0),
                        "previous_close": info.get("regularMarketPreviousClose", 0),
                    }

            result = await asyncio.to_thread(fetch_quote)

            if result and result["price"]:
                price = float(result["price"])
                prev_close = float(result["previous_close"]) if result["previous_close"] else price
                change_percent = ((price - prev_close) / prev_close * 100) if prev_close else 0
                change_sign = "+" if change_percent >= 0 else ""

                return {
                    "id": code,
                    "name": config["name"],
                    "value": value_format(price),
                    "change": f"{change_sign}{change_percent:.2f}%",
                    "change_percent": change_percent,
                    "trend": "up" if change_percent >= 0 else "down",
                    "critical": config.get("critical", False),
                    "symbol": config["symbol"],
                    "type": config["type"],
                }

            logger.warning(f"No data returned for {code} ({yf_symbol})")

        except Exception as e:
            logger.warning(f"YFinance SDK call failed for {code}: {e}")

        return self._get_mock_indicator(code, config)

    def _get_mock_indicator(self, code: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """获取降级数据（不使用随机模拟，避免生产环境“假数据”）"""
        default_value = config.get("default_value", "0")
        change_percent = 0.0
        return {
            "id": code,
            "name": config["name"],
            "value": default_value,
            "change": "+0.00%",
            "change_percent": change_percent,
            "trend": "up",
            "critical": config.get("critical", False),
            "symbol": config["symbol"],
            "type": config["type"],
        }


# 全局缓存实例
_market_cache = MarketDataCache(ttl_seconds=600)  # 10 minutes TTL
_cockpit_macro_cache = CockpitMacroCache(ttl_seconds=300)  # 5 minutes TTL


class MarketService(BaseService[Asset]):
    """市场数据服务"""

    def __init__(self, db: Session):
        """初始化市场服务"""
        super().__init__(db, Asset)

    # =========================================================================
    # Global Market Data & Cockpit
    # =========================================================================

    async def get_global_market_data(
        self, force_refresh: bool = False
    ) -> MarketDataResponse:
        """获取全球主要市场指数数据"""
        data = await _market_cache.get_data(force_refresh=force_refresh)
        return MarketDataResponse(
            markets=data["markets"],
            last_updated=data["last_updated"],
            next_update_in_seconds=300,
        )

    async def get_single_market(self, code: str) -> Optional[MarketIndex]:
        """获取单个市场数据"""
        data = await _market_cache.get_data()
        for market in data["markets"]:
            if market.code == code.upper():
                return market
        return None

    async def get_market_status(self) -> Dict[str, Any]:
        """获取市场数据状态"""
        data = await _market_cache.get_data()
        return {
            "last_updated": data["last_updated"],
            "is_expired": _market_cache.is_expired(),
            "markets_count": len(data["markets"]),
            "next_update_in_seconds": 300,
        }

    async def get_cockpit_macro_data(
        self, force_refresh: bool = False
    ) -> CockpitMacroResponse:
        """获取 Cockpit 宏观指标数据"""
        redis = get_redis_manager()

        # 1) Redis 热缓存（默认）
        if not force_refresh:
            cached = await redis.get_json(COCKPIT_MACRO_REDIS_KEY)
            if cached and cached.get("indicators"):
                indicators = [
                    CockpitMacroIndicator(**ind) for ind in cached["indicators"]
                ]
                return CockpitMacroResponse(
                    indicators=indicators,
                    last_updated=cached.get("last_updated")
                    or datetime.now().isoformat(),
                    next_update_in_seconds=600,
                )

        # 2) DB（macro_indicator_cache）
        rows = (
            self.db.query(MacroIndicatorCache)
            .filter(MacroIndicatorCache.is_active == True)
            .all()
        )

        by_id = {r.indicator_id: r for r in rows}
        ordered: List[CockpitMacroIndicator] = []

        last_updated: Optional[datetime] = None
        for code, config in COCKPIT_MACRO_CONFIG.items():
            row = by_id.get(code)
            if not row or not row.current_value:
                continue
            if row.last_updated and (
                last_updated is None or row.last_updated > last_updated
            ):
                last_updated = row.last_updated
            ordered.append(
                CockpitMacroIndicator(
                    id=code,
                    name=row.indicator_name or config.get("name", code),
                    value=row.current_value,
                    change=row.change_value or "+0.00%",
                    change_percent=float(row.change_percent or 0.0),
                    trend=row.trend
                    or ("up" if (row.change_percent or 0.0) >= 0 else "down"),
                    critical=bool(config.get("critical", row.is_critical)),
                    symbol=row.symbol or config.get("symbol", code),
                    type=row.indicator_type or config.get("type", "macro"),
                )
            )

        # 3) 写回 Redis（避免 API 直接打 DB）
        payload = {
            "indicators": [ind.model_dump() for ind in ordered],
            "last_updated": (last_updated or datetime.now()).isoformat(),
        }
        await redis.set(COCKPIT_MACRO_REDIS_KEY, payload, ttl=600)

        return CockpitMacroResponse(
            indicators=ordered,
            last_updated=payload["last_updated"],
            next_update_in_seconds=600,
        )

    async def get_personalized_cockpit_data(
        self, user_id: int, force_refresh: bool = False
    ) -> CockpitMacroResponse:
        """获取个性化的 Cockpit 宏观指标数据"""
        # 首先获取实时数据
        realtime_response = await self.get_cockpit_macro_data(
            force_refresh=force_refresh
        )
        realtime_indicators = {ind.id: ind for ind in realtime_response.indicators}

        # 获取用户选择
        user_selections = (
            self.db.query(UserCockpitIndicator)
            .filter(
                and_(
                    UserCockpitIndicator.user_id == user_id,
                    UserCockpitIndicator.is_active == True,
                )
            )
            .order_by(UserCockpitIndicator.display_order)
            .all()
        )

        if not user_selections:
            return realtime_response

        indicators = []
        for selection in user_selections:
            indicator_id = selection.indicator_id
            if indicator_id in realtime_indicators:
                indicators.append(realtime_indicators[indicator_id])
            else:
                logger.warning(
                    f"User selected indicator {indicator_id} not found in realtime cache"
                )

        if not indicators:
            return realtime_response

        return CockpitMacroResponse(
            indicators=indicators,
            last_updated=realtime_response.last_updated,
            next_update_in_seconds=realtime_response.next_update_in_seconds,
        )

    async def get_single_indicator(
        self, indicator_id: str
    ) -> Optional[CockpitMacroIndicator]:
        """获取单个宏观指标"""
        response = await self.get_cockpit_macro_data()
        for indicator in response.indicators:
            if indicator.id == indicator_id.lower():
                return indicator
        return None

    async def get_cockpit_status(self) -> Dict[str, Any]:
        """获取 Cockpit 数据状态"""
        redis = get_redis_manager()
        cached = await redis.get_json(COCKPIT_MACRO_REDIS_KEY)
        last_updated = cached.get("last_updated") if cached else None

        if not last_updated:
            row = (
                self.db.query(MacroIndicatorCache)
                .filter(MacroIndicatorCache.is_active == True)
                .order_by(MacroIndicatorCache.last_updated.desc())
                .first()
            )
            last_updated = (
                row.last_updated.isoformat() if row and row.last_updated else None
            )

        if not last_updated:
            last_updated = datetime.now().isoformat()

        # 过期语义：超过 2 个周期仍未更新
        try:
            ts = datetime.fromisoformat(last_updated)
            is_expired = (datetime.now() - ts).total_seconds() > 1200
        except Exception as e:
            logger.debug(f"Failed to parse last_updated timestamp '{last_updated}': {e}")
            is_expired = True

        return {
            "last_updated": last_updated,
            "is_expired": is_expired,
        }

    async def get_available_indicators(
        self, user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取所有可用的 Cockpit 指标，标记用户已选择的指标"""
        # 1. 从 COCKPIT_MACRO_CONFIG 获取所有可用指标
        all_indicators = []
        
        # 获取用户已选择的指标 ID 列表
        user_selected_ids: set = set()
        if user_id:
            user_selections = (
                self.db.query(UserCockpitIndicator)
                .filter(
                    and_(
                        UserCockpitIndicator.user_id == user_id,
                        UserCockpitIndicator.is_active == True,
                    )
                )
                .all()
            )
            user_selected_ids = {s.indicator_id for s in user_selections}
        
        # 获取缓存的实时数据（如果有）
        redis = get_redis_manager()
        cached = await redis.get_json(COCKPIT_MACRO_REDIS_KEY)
        cached_indicators = {}
        if cached and cached.get("indicators"):
            for ind in cached["indicators"]:
                cached_indicators[ind.get("id")] = ind
        
        # 构建可用指标列表
        for code, config in COCKPIT_MACRO_CONFIG.items():
            indicator_id = config.get("id", code)
            cached_data = cached_indicators.get(indicator_id, {})
            
            all_indicators.append({
                "indicator_id": indicator_id,
                "indicator_name": config.get("name", indicator_id),
                "symbol": config.get("symbol", indicator_id),
                "indicator_type": config.get("type", "macro"),
                "is_critical": config.get("critical", False),
                "current_value": cached_data.get("value"),
                "change_percent": cached_data.get("change_percent"),
                "trend": cached_data.get("trend"),
                "is_selected": indicator_id in user_selected_ids,
                "last_updated": cached.get("last_updated") if cached else None,
            })
        
        return all_indicators

    async def get_user_indicators(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户选择的 Cockpit 指标列表"""
        user_indicators = (
            self.db.query(UserCockpitIndicator)
            .filter(
                and_(
                    UserCockpitIndicator.user_id == user_id,
                    UserCockpitIndicator.is_active == True,
                )
            )
            .order_by(UserCockpitIndicator.display_order)
            .all()
        )
        
        return [
            {
                "id": ind.id,
                "indicator_id": ind.indicator_id,
                "display_order": ind.display_order,
                "is_active": ind.is_active,
            }
            for ind in user_indicators
        ]

    async def add_user_indicator(self, user_id: int, indicator_id: str, display_order: int = 0) -> Dict[str, Any]:
        """添加用户 Cockpit 指标"""
        # 检查是否已存在
        existing = (
            self.db.query(UserCockpitIndicator)
            .filter(
                and_(
                    UserCockpitIndicator.user_id == user_id,
                    UserCockpitIndicator.indicator_id == indicator_id,
                )
            )
            .first()
        )
        
        if existing:
            # 如果已存在但被禁用，重新激活
            if not existing.is_active:
                existing.is_active = True
                existing.display_order = display_order
                self.db.commit()
                return {"message": "Indicator reactivated", "id": existing.id}
            return {"message": "Indicator already exists", "id": existing.id}
        
        # 如果没有指定顺序，放到最后
        if display_order == 0:
            max_order = (
                self.db.query(UserCockpitIndicator.display_order)
                .filter(
                    and_(
                        UserCockpitIndicator.user_id == user_id,
                        UserCockpitIndicator.is_active == True,
                    )
                )
                .order_by(UserCockpitIndicator.display_order.desc())
                .first()
            )
            display_order = (max_order[0] + 1) if max_order else 1
        
        new_indicator = UserCockpitIndicator(
            user_id=user_id,
            indicator_id=indicator_id,
            display_order=display_order,
            is_active=True,
        )
        self.db.add(new_indicator)
        self.db.commit()
        
        return {"message": "Indicator added", "id": new_indicator.id}

    async def remove_user_indicator(self, user_id: int, indicator_id: str) -> Dict[str, str]:
        """移除用户 Cockpit 指标"""
        indicator = (
            self.db.query(UserCockpitIndicator)
            .filter(
                and_(
                    UserCockpitIndicator.user_id == user_id,
                    UserCockpitIndicator.indicator_id == indicator_id,
                )
            )
            .first()
        )
        
        if not indicator:
            raise ValueError(f"Indicator {indicator_id} not found for user")
        
        indicator.is_active = False
        self.db.commit()
        
        return {"message": "Indicator removed"}

    async def update_indicator_order(self, user_id: int, indicator_id: str, new_order: int) -> Dict[str, str]:
        """更新用户 Cockpit 指标顺序"""
        indicator = (
            self.db.query(UserCockpitIndicator)
            .filter(
                and_(
                    UserCockpitIndicator.user_id == user_id,
                    UserCockpitIndicator.indicator_id == indicator_id,
                    UserCockpitIndicator.is_active == True,
                )
            )
            .first()
        )
        
        if not indicator:
            raise ValueError(f"Indicator {indicator_id} not found for user")
        
        indicator.display_order = new_order
        self.db.commit()
        
        return {"message": "Order updated"}

    async def get_status(self) -> Dict[str, Any]:
        """获取市场数据服务状态（统一接口）"""
        market_status = await self.get_market_status()
        cockpit_status = await self.get_cockpit_status()
        return {
            "last_updated": market_status["last_updated"],
            "is_expired": market_status["is_expired"],
            "markets_count": market_status["markets_count"],
            "next_update_in_seconds": market_status["next_update_in_seconds"],
            "cockpit": {
                "last_updated": cockpit_status["last_updated"],
                "is_expired": cockpit_status["is_expired"],
            },
        }

    async def refresh_data(self):
        """刷新所有市场数据"""
        await _market_cache.get_data(force_refresh=True)
        # Cockpit macro refresh: 只清理 Redis，让下一次读取回落 DB（外部拉取由后台同步服务负责）
        redis = get_redis_manager()
        await redis.delete(COCKPIT_MACRO_REDIS_KEY)

    # =========================================================================
    # Asset 管理 (Existing Logic)
    # =========================================================================

    def get_asset_by_ticker(self, ticker: str) -> Optional[Asset]:
        """根据 ticker 获取资产"""
        return self.db.query(Asset).filter(Asset.ticker == ticker).first()

    def search_assets(
        self, query: str, asset_type: Optional[str] = None, limit: int = 20
    ) -> List[Asset]:
        """搜索资产 (Database Only)"""
        query_filter = Asset.ticker.ilike(f"%{query}%") | Asset.name.ilike(f"%{query}%")

        db_query = self.db.query(Asset).filter(query_filter)

        if asset_type:
            db_query = db_query.filter(Asset.asset_type == asset_type)

        return db_query.filter(Asset.is_active == True).limit(limit).all()

    # =========================================================================
    # Unified Asset Search (yfinance + akshare, NO MCP)
    # =========================================================================

    def _infer_market_and_symbol(self, query: str) -> tuple[str, str, str]:
        """
        Smart inference of market type and yfinance symbol from user input.

        Returns: (yf_symbol, market_type, display_ticker)
        """
        query = query.strip()
        query_upper = query.upper()

        # 1. Check commodity futures mapping
        if query_upper in COMMODITY_FUTURES_MAP:
            yf_symbol = COMMODITY_FUTURES_MAP[query_upper]
            return yf_symbol, "COMMODITY", yf_symbol

        # Check Chinese commodity names
        if query in COMMODITY_FUTURES_MAP:
            yf_symbol = COMMODITY_FUTURES_MAP[query]
            return yf_symbol, "COMMODITY", yf_symbol

        # 2. Check crypto mapping
        if query_upper in CRYPTO_MAP:
            yf_symbol = CRYPTO_MAP[query_upper]
            return yf_symbol, "CRYPTO", yf_symbol

        # Already in yfinance crypto format (e.g., BTC-USD)
        if "-USD" in query_upper and len(query_upper) <= 12:
            return query_upper, "CRYPTO", query_upper

        # 3. Check if already has market suffix (e.g., 0700.HK, BP.L)
        if "." in query:
            parts = query.rsplit(".", 1)
            if len(parts) == 2:
                code, suffix = parts
                suffix_upper = suffix.upper()
                if suffix_upper == "HK":
                    # Normalize HK stock code (pad to 4 digits)
                    code_normalized = code.lstrip("0").zfill(4)
                    yf_symbol = f"{code_normalized}.HK"
                    return yf_symbol, "HK", yf_symbol
                elif suffix_upper in ("SS", "SH"):
                    return f"{code}.SS", "SS", f"{code}.SS"
                elif suffix_upper == "SZ":
                    return f"{code}.SZ", "SZ", f"{code}.SZ"
                elif suffix_upper in MARKET_SUFFIX_MAP:
                    normalized = f"{code.upper()}{MARKET_SUFFIX_MAP[suffix_upper]}"
                    return normalized, suffix_upper, normalized
                else:
                    # Assume it's a valid yfinance symbol
                    return query_upper, "INTL", query_upper

        # 4. Check for futures format (e.g., GC=F, CL=F)
        if "=F" in query_upper:
            return query_upper, "COMMODITY", query_upper

        # 5. Infer from numeric code format
        if query.isdigit():
            code_len = len(query)
            code_int = int(query)

            # Hong Kong stocks: 4-5 digit codes starting with 0-9
            if code_len <= 5 and code_int < 100000:
                # 00700 or 0700 -> 0700.HK
                code_normalized = query.lstrip("0").zfill(4)
                yf_symbol = f"{code_normalized}.HK"
                return yf_symbol, "HK", yf_symbol

            # A-shares: 6 digit codes
            if code_len == 6:
                if query.startswith(("600", "601", "603", "605", "688")):
                    # Shanghai
                    return f"{query}.SS", "SS", f"{query}.SS"
                elif query.startswith(("000", "001", "002", "003", "300", "301")):
                    # Shenzhen
                    return f"{query}.SZ", "SZ", f"{query}.SZ"

        # 6. Default: assume US stock (pure alphabetic or mixed)
        # Remove any invalid characters
        clean_symbol = "".join(c for c in query_upper if c.isalnum() or c in ".-")
        return clean_symbol, "US", clean_symbol

    async def _verify_with_yfinance(
        self, yf_symbol: str, timeout: float = 3.0
    ) -> Optional[Dict[str, Any]]:
        """Verify asset with yfinance and return info if valid."""
        try:
            import yfinance as yf

            def fetch_info():
                try:
                    ticker = yf.Ticker(yf_symbol)
                    info = ticker.info
                    # Check if it's a valid ticker
                    if info and (
                        "shortName" in info
                        or "longName" in info
                        or "regularMarketPrice" in info
                        or "currentPrice" in info
                    ):
                        return info
                except Exception as e:
                    logger.debug(f"yfinance fetch_info failed for {yf_symbol}: {e}")
                return None

            info = await asyncio.wait_for(
                asyncio.to_thread(fetch_info), timeout=timeout
            )
            return info
        except asyncio.TimeoutError:
            logger.debug(f"yfinance timeout for {yf_symbol}")
            return None
        except Exception as e:
            logger.debug(f"yfinance error for {yf_symbol}: {e}")
            return None

    async def _search_with_akshare(
        self, query: str, market_hint: str, limit: int = 10
    ) -> List[AssetSearchResult]:
        """Fallback search using akshare SDK."""
        results = []
        try:
            import akshare as ak

            query_upper = query.upper()

            # Search based on market hint
            if market_hint in ("HK", "SS", "SZ", "CN"):
                # A-shares and HK stocks
                try:
                    def search_a_shares():
                        try:
                            # Get A-share stock list
                            df = ak.stock_zh_a_spot_em()
                            if df is not None and not df.empty:
                                matches = []
                                for _, row in df.iterrows():
                                    code = str(row.get("代码", ""))
                                    name = str(row.get("名称", ""))
                                    if query in code or query in name.upper():
                                        # Determine exchange
                                        if code.startswith(("600", "601", "603", "605", "688")):
                                            suffix = ".SS"
                                            exchange = "SSE"
                                        else:
                                            suffix = ".SZ"
                                            exchange = "SZSE"
                                        matches.append({
                                            "ticker": f"{code}{suffix}",
                                            "name": name,
                                            "exchange": exchange,
                                            "asset_type": "CN",
                                            "currency": "CNY",
                                        })
                                        if len(matches) >= limit:
                                            break
                                return matches
                        except Exception as e:
                            logger.debug(f"akshare A-share search failed for query '{query}': {e}")
                        return []

                    matches = await asyncio.wait_for(
                        asyncio.to_thread(search_a_shares), timeout=5.0
                    )
                    for m in matches:
                        results.append(AssetSearchResult(**m))
                except asyncio.TimeoutError:
                    logger.debug(f"akshare A-share search timed out for query '{query}'")

            elif market_hint == "US":
                # US stocks via akshare
                try:
                    def search_us_stocks():
                        try:
                            df = ak.stock_us_spot_em()
                            if df is not None and not df.empty:
                                matches = []
                                for _, row in df.iterrows():
                                    code = str(row.get("代码", "")).upper()
                                    name = str(row.get("名称", ""))
                                    if query_upper in code or query_upper in name.upper():
                                        matches.append({
                                            "ticker": code,
                                            "name": name,
                                            "exchange": "NYSE/NASDAQ",
                                            "asset_type": "US",
                                            "currency": "USD",
                                        })
                                        if len(matches) >= limit:
                                            break
                                return matches
                        except Exception as e:
                            logger.debug(f"akshare US stock search failed for query '{query}': {e}")
                        return []

                    matches = await asyncio.wait_for(
                        asyncio.to_thread(search_us_stocks), timeout=5.0
                    )
                    for m in matches:
                        results.append(AssetSearchResult(**m))
                except asyncio.TimeoutError:
                    logger.debug(f"akshare US stock search timed out for query '{query}'")

        except ImportError:
            logger.warning("akshare not installed, fallback search unavailable")
        except Exception as e:
            logger.debug(f"akshare search error: {e}")

        return results[:limit]

    async def unified_search_assets(
        self, request: AssetSearchRequest
    ) -> List[AssetSearchResult]:
        """
        Unified asset search with smart market inference.

        Priority: yfinance (primary) -> akshare (fallback)
        Supports: US, HK, A-shares, Crypto, Commodities, UK, JP, DE, SG
        """
        query = request.query.strip()
        if not query:
            return []

        results = []
        seen_tickers = set()
        limit = request.limit or 10

        # 1. Smart inference: determine market type and yfinance symbol
        yf_symbol, market_type, display_ticker = self._infer_market_and_symbol(query)

        # 2. Try yfinance verification first
        info = await self._verify_with_yfinance(yf_symbol)
        if info:
            # Get asset type info
            type_info = ASSET_TYPE_LABELS.get(market_type, ("US", "NYSE/NASDAQ", "USD"))
            asset_type, exchange, currency = type_info

            # Override with actual info from yfinance if available
            actual_exchange = info.get("exchange", exchange)
            actual_currency = info.get("currency", currency)

            result = AssetSearchResult(
                ticker=display_ticker,
                name=info.get("shortName") or info.get("longName") or display_ticker,
                asset_type=asset_type,
                exchange=actual_exchange,
                currency=actual_currency,
                market_cap=info.get("marketCap"),
            )
            results.append(result)
            seen_tickers.add(display_ticker.upper())

        # 3. If query is too short or generic, also search for partial matches
        if len(results) < limit and len(query) >= 1:
            # Try additional formats for the same query
            additional_formats = []
            query_upper = query.upper()

            # If it's a crypto short name, try with -USD
            if query_upper in CRYPTO_MAP and query_upper not in seen_tickers:
                crypto_symbol = CRYPTO_MAP[query_upper]
                if crypto_symbol not in seen_tickers:
                    additional_formats.append((crypto_symbol, "CRYPTO", crypto_symbol))

            # If it's a commodity keyword
            if query_upper in COMMODITY_FUTURES_MAP and query_upper not in seen_tickers:
                commodity_symbol = COMMODITY_FUTURES_MAP[query_upper]
                if commodity_symbol not in seen_tickers:
                    additional_formats.append((commodity_symbol, "COMMODITY", commodity_symbol))

            # Check Chinese commodity/crypto names
            if query in COMMODITY_FUTURES_MAP:
                commodity_symbol = COMMODITY_FUTURES_MAP[query]
                if commodity_symbol not in seen_tickers:
                    additional_formats.append((commodity_symbol, "COMMODITY", commodity_symbol))

            if query in CRYPTO_MAP:
                crypto_symbol = CRYPTO_MAP[query]
                if crypto_symbol not in seen_tickers:
                    additional_formats.append((crypto_symbol, "CRYPTO", crypto_symbol))

            # Verify additional formats
            for yf_sym, mkt_type, disp_ticker in additional_formats:
                if len(results) >= limit:
                    break
                if disp_ticker.upper() in seen_tickers:
                    continue

                info = await self._verify_with_yfinance(yf_sym, timeout=2.0)
                if info:
                    type_info = ASSET_TYPE_LABELS.get(mkt_type, ("US", "NYSE/NASDAQ", "USD"))
                    asset_type, exchange, currency = type_info

                    result = AssetSearchResult(
                        ticker=disp_ticker,
                        name=info.get("shortName") or info.get("longName") or disp_ticker,
                        asset_type=asset_type,
                        exchange=info.get("exchange", exchange),
                        currency=info.get("currency", currency),
                        market_cap=info.get("marketCap"),
                    )
                    results.append(result)
                    seen_tickers.add(disp_ticker.upper())

        # 4. Fallback to akshare if needed
        if len(results) < limit:
            akshare_results = await self._search_with_akshare(
                query, market_type, limit - len(results)
            )
            for r in akshare_results:
                if r.ticker.upper() not in seen_tickers:
                    results.append(r)
                    seen_tickers.add(r.ticker.upper())
                    if len(results) >= limit:
                        break

        # 5. Filter by asset_types if specified
        if request.asset_types:
            # Handle MACRO -> COMMODITY mapping (frontend uses MACRO, backend uses COMMODITY)
            filter_types = set(request.asset_types)
            if "MACRO" in filter_types:
                filter_types.discard("MACRO")
                filter_types.add("COMMODITY")
            results = [r for r in results if r.asset_type in filter_types]

        return results[:limit]

    async def search_assets_extended(
        self, request: AssetSearchRequest
    ) -> List[AssetSearchResult]:
        """
        高级资产搜索 (已重构为使用统一搜索)

        Deprecated: 请直接使用 unified_search_assets()
        """
        return await self.unified_search_assets(request)

    def create_or_update_asset(self, asset_data: Dict[str, Any]) -> Asset:
        """创建或更新资产"""
        ticker = asset_data.get("ticker")
        asset = self.get_asset_by_ticker(ticker)

        if asset:
            for key, value in asset_data.items():
                if hasattr(asset, key) and value is not None:
                    setattr(asset, key, value)
            asset.updated_at = datetime.now()
        else:
            asset = Asset(**asset_data)
            self.db.add(asset)

        self.db.commit()
        self.db.refresh(asset)
        return asset

    # =========================================================================
    # 实时行情管理 (Existing Logic)
    # =========================================================================

    def get_realtime_quote(self, ticker: str) -> Optional[RealtimeQuote]:
        """获取实时行情"""
        return (
            self.db.query(RealtimeQuote).filter(RealtimeQuote.ticker == ticker).first()
        )

    def update_realtime_quote(
        self, ticker: str, quote_data: Dict[str, Any]
    ) -> RealtimeQuote:
        """更新实时行情"""
        quote = self.get_realtime_quote(ticker)

        if quote:
            for key, value in quote_data.items():
                if hasattr(quote, key) and value is not None:
                    setattr(quote, key, value)
        else:
            quote = RealtimeQuote(ticker=ticker, **quote_data)
            self.db.add(quote)

        quote.last_updated = datetime.now()
        self.db.commit()
        self.db.refresh(quote)
        return quote

    def batch_update_quotes(self, quotes_data: List[Dict[str, Any]]) -> int:
        """批量更新行情"""
        updated_count = 0
        for quote_data in quotes_data:
            ticker = quote_data.get("ticker")
            if ticker:
                self.update_realtime_quote(ticker, quote_data)
                updated_count += 1
        return updated_count

    # =========================================================================
    # 历史价格管理 (Existing Logic)
    # =========================================================================

    def get_stock_prices(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        resolution: str = "1d",
    ) -> List[StockPrice]:
        """获取历史价格"""
        query = self.db.query(StockPrice).filter(
            StockPrice.ticker == ticker, StockPrice.resolution == resolution
        )

        if start_date:
            query = query.filter(StockPrice.date >= start_date)

        if end_date:
            query = query.filter(StockPrice.date <= end_date)

        return query.order_by(StockPrice.date.asc()).all()

    # =========================================================================
    # 基本面数据管理 (Existing Logic)
    # =========================================================================

    def get_fundamental_data(
        self, ticker: str, data_date: Optional[datetime] = None
    ) -> Optional[FundamentalData]:
        """获取基本面数据"""
        query = self.db.query(FundamentalData).filter(FundamentalData.ticker == ticker)

        if data_date:
            query = query.filter(FundamentalData.data_date == data_date)
        else:
            query = query.order_by(FundamentalData.data_date.desc())

        return query.first()

    # =========================================================================
    # 技术指标管理 (Existing Logic)
    # =========================================================================

    def get_technical_indicators(
        self, ticker: str, indicator_name: str, days_back: int = 30
    ) -> List[TechnicalIndicator]:
        """获取技术指标"""
        cutoff_date = datetime.now() - timedelta(days=days_back)

        return (
            self.db.query(TechnicalIndicator)
            .filter(
                TechnicalIndicator.ticker == ticker,
                TechnicalIndicator.indicator_name == indicator_name,
                TechnicalIndicator.date >= cutoff_date,
            )
            .order_by(TechnicalIndicator.date.asc())
            .all()
        )

    # =========================================================================
    # 新闻管理 (Existing Logic)
    # =========================================================================

    def get_market_news(
        self, ticker: Optional[str] = None, limit: int = 20
    ) -> List[MarketNews]:
        """获取市场新闻"""
        query = self.db.query(MarketNews)

        if ticker:
            query = query.filter(MarketNews.ticker == ticker)

        return query.order_by(MarketNews.published_at.desc()).limit(limit).all()

    # =========================================================================
    # 用户投资组合 (Existing Logic)
    # =========================================================================

    def get_user_portfolio_assets(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户投资组合及其最新行情"""
        portfolio = (
            self.db.query(UserPortfolio).filter(UserPortfolio.user_id == user_id).all()
        )

        result = []
        for item in portfolio:
            asset = item.asset
            quote = asset.realtime_quote if asset else None

            result.append(
                {
                    "ticker": item.ticker,
                    "asset_name": asset.name if asset else None,
                    "asset_type": asset.asset_type if asset else None,
                    "notes": item.notes,
                    "target_price": item.target_price,
                    "current_price": quote.price if quote else None,
                    "change_percent": quote.change_percent if quote else None,
                    "added_at": item.added_at,
                }
            )

        return result


__all__ = ["MarketService"]
