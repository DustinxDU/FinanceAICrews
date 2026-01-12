"""
Chart Data Service - 图表数据服务

提供图表数据的获取、缓存和标准化逻辑。
采用混合模式：
1. 优先检查 Redis 缓存
2. 缓存未命中则调用 SDK Fetcher 获取实时数据
3. 数据标准化后存入缓存并返回
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, time
import pytz

from AICrews.observability.logging import get_logger
from AICrews.infrastructure.data_fetcher import (
    get_yfinance_fetcher,
    is_yfinance_rate_limited,
    get_yfinance_cooldown_remaining,
)
from AICrews.schemas.chart import (
    ChartDataRequest,
    OHLCVData,
    ChartDataResponse,
    SparklineResponse,
)
from AICrews.infrastructure.cache.redis_manager import get_redis_manager

logger = get_logger(__name__)


class ChartDataService:
    """图表数据服务 - 透传模式 + Redis缓存"""

    def __init__(self):
        self.redis_manager = get_redis_manager()
        self.yf_fetcher = get_yfinance_fetcher()

    async def get_chart_data(self, request: ChartDataRequest) -> ChartDataResponse:
        """获取图表数据（透传+缓存模式）

        逻辑：
        1. 生成缓存键
        2. 检查Redis缓存
        3. 缓存未命中 -> 调用MCP -> 存缓存 -> 返回
        4. 缓存命中 -> 直接返回
        
        v2.1 优化：在 YFinance 限流时，如果有缓存则直接返回缓存数据，
        避免发起注定失败的请求。
        """
        cache_key = self._generate_cache_key(request)

        # 1. 尝试从Redis获取缓存
        cached_data = await self.redis_manager.get_json(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {cache_key}")
            return ChartDataResponse(
                ticker=request.ticker,
                resolution=request.resolution,
                data=[OHLCVData(**item) for item in cached_data["data"]],
                cached=True,
                last_updated=datetime.fromisoformat(cached_data["last_updated"]),
            )

        # 2. 检查 YFinance 是否处于限流状态
        if is_yfinance_rate_limited():
            cooldown_remaining = get_yfinance_cooldown_remaining()
            logger.warning(
                f"YFinance rate limited for chart request {request.ticker}, "
                f"cooldown remaining: {cooldown_remaining:.1f}s, no cache available"
            )
            # 没有缓存且被限流，返回 None 让 API 层处理
            return None

        # 3. 缓存未命中，从 SDK Fetcher 获取数据
        logger.debug(f"Cache miss for {cache_key}, fetching from SDK")
        raw_data = await self._fetch_from_sdk(request)

        if not raw_data:
            # 如果没有数据，尝试返回空列表而不是报错，或者根据业务需求抛出异常
            # 这里保持原逻辑抛出异常
            # raise HTTPException(status_code=404, detail=f"No data found for {request.ticker}")
            # Service层不应该直接抛出HTTP异常，返回None让API层处理
            return None

        # 3. 转换数据格式
        chart_data = self._normalize_chart_data(raw_data)

        # 4. 存储到Redis缓存
        cache_data = {
            "data": [
                {
                    "timestamp": item.timestamp.isoformat(),
                    "open": item.open,
                    "high": item.high,
                    "low": item.low,
                    "close": item.close,
                    "volume": item.volume,
                }
                for item in chart_data
            ],
            "last_updated": datetime.now().isoformat(),
        }

        # 根据分辨率设置不同的缓存时间
        ttl = self._get_cache_ttl(request.resolution)
        await self.redis_manager.set(cache_key, cache_data, ttl=ttl)

        return ChartDataResponse(
            ticker=request.ticker,
            resolution=request.resolution,
            data=chart_data,
            cached=False,
            last_updated=datetime.now(),
        )

    def _generate_cache_key(self, request: ChartDataRequest) -> str:
        """生成缓存键"""
        key_parts = [
            "chart",
            request.ticker.upper(),
            request.resolution,
            request.start_date or "default",
            request.end_date or "default",
            str(request.limit),
        ]
        return ":".join(key_parts)

    def _get_cache_ttl(self, resolution: str, ticker: str = None) -> int:
        """缓存TTL 策略（实时优先）"""
        base_ttl_map = {
            "1m": 30,
            "5m": 120,
            "15m": 300,
            "1h": 600,
            "1d": 900,
        }
        return base_ttl_map.get(resolution, 120)

    def _is_market_open(self, ticker: str) -> bool:
        """判断市场是否开盘"""
        try:
            current_utc = datetime.now().replace(tzinfo=pytz.UTC)

            # 根据ticker判断市场类型
            if self._is_us_market(ticker):
                return self._is_us_market_open(current_utc)
            elif self._is_hk_market(ticker):
                return self._is_hk_market_open(current_utc)
            elif self._is_crypto_market(ticker):
                return True  # 加密货币24小时交易
            else:
                return True  # 未知市场默认开盘

        except Exception as e:
            logger.error(f"Error checking market status for {ticker}: {e}")
            return True

    def _is_us_market(self, ticker: str) -> bool:
        return not (
            ".HK" in ticker
            or "-USD" in ticker
            or ticker in ["US10Y", "DXY", "VIX", "GOLD"]
        )

    def _is_hk_market(self, ticker: str) -> bool:
        return ".HK" in ticker

    def _is_crypto_market(self, ticker: str) -> bool:
        return "-USD" in ticker or ticker.endswith("USDT")

    def _is_us_market_open(self, current_utc: datetime) -> bool:
        try:
            et_tz = pytz.timezone("America/New_York")
            et_time = current_utc.astimezone(et_tz)

            if et_time.weekday() >= 5:
                return False

            current_time = et_time.time()
            # 扩展交易时间：4:00 AM - 8:00 PM ET
            extended_open = time(4, 0)
            extended_close = time(20, 0)

            return extended_open <= current_time <= extended_close

        except Exception as e:
            logger.error(f"Error checking US market hours: {e}")
            return True

    def _is_hk_market_open(self, current_utc: datetime) -> bool:
        try:
            hk_tz = pytz.timezone("Asia/Hong_Kong")
            hk_time = current_utc.astimezone(hk_tz)

            if hk_time.weekday() >= 5:
                return False

            current_time = hk_time.time()

            morning_open = time(9, 30)
            morning_close = time(12, 0)
            afternoon_open = time(13, 0)
            afternoon_close = time(16, 0)

            return (morning_open <= current_time <= morning_close) or (
                afternoon_open <= current_time <= afternoon_close
            )

        except Exception as e:
            logger.error(f"Error checking HK market hours: {e}")
            return True

    async def _fetch_from_sdk(
        self, request: ChartDataRequest
    ) -> Optional[List[Dict[str, Any]]]:
        """从 SDK Fetcher 获取原始数据
        
        v2.1 优化：在 YFinance 限流时直接返回 None，避免发起注定失败的请求。
        """
        # 检查 YFinance 是否处于限流状态
        if is_yfinance_rate_limited():
            cooldown_remaining = get_yfinance_cooldown_remaining()
            logger.warning(
                f"YFinance rate limited, skipping SDK fetch for {request.ticker} "
                f"(cooldown remaining: {cooldown_remaining:.1f}s)"
            )
            return None

        try:
            ticker = request.ticker.upper()

            if "-USD" in ticker or ticker.endswith("USDT"):
                return await self._fetch_crypto_data(ticker, request)
            elif ".HK" in ticker:
                return await self._fetch_hk_data(ticker, request)
            elif ticker in ["US10Y", "DXY", "VIX", "GOLD"]:
                return await self._fetch_macro_data(ticker, request)
            else:
                return await self._fetch_us_data(ticker, request)

        except Exception as e:
            logger.error(f"Error fetching data from SDK for {request.ticker}: {e}")
            return None

    async def _fetch_us_data(
        self, ticker: str, request: ChartDataRequest
    ) -> Optional[List[Dict[str, Any]]]:
        """获取美股数据 - 使用 SDK Fetcher"""
        try:
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "1d": "1d",
                "1wk": "1wk",
                "1mo": "1mo",
            }
            interval = interval_map.get(request.resolution, "1d")

            end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
            if request.start_date:
                start_date = request.start_date
            else:
                days_map = {"1m": 7, "5m": 30, "15m": 60, "1h": 90, "1d": 365}
                days = days_map.get(request.resolution, 365)
                start_date = (datetime.now() - timedelta(days=days)).strftime(
                    "%Y-%m-%d"
                )

            result = await self.yf_fetcher.fetch_history(
                ticker=ticker,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
            )

            return result if result else None

        except Exception as e:
            logger.error(f"Error fetching US stock data for {ticker}: {e}")
            return None

    async def _fetch_crypto_data(
        self, ticker: str, request: ChartDataRequest
    ) -> Optional[List[Dict[str, Any]]]:
        """获取加密货币数据 - 使用 SDK Fetcher"""
        try:
            symbol = ticker if "-USD" in ticker else f"{ticker}-USD"

            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "1d": "1d",
                "1wk": "1wk",
                "1mo": "1mo",
            }
            interval = interval_map.get(request.resolution, "1d")

            end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
            if request.start_date:
                start_date = request.start_date
            else:
                days_map = {"1m": 7, "5m": 30, "15m": 60, "1h": 90, "1d": 365}
                days = days_map.get(request.resolution, 365)
                start_date = (datetime.now() - timedelta(days=days)).strftime(
                    "%Y-%m-%d"
                )

            result = await self.yf_fetcher.fetch_history(
                ticker=symbol,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
            )

            return result if result else None

        except Exception as e:
            logger.error(f"Error fetching crypto data for {ticker}: {e}")
            return None

    async def _fetch_hk_data(
        self, ticker: str, request: ChartDataRequest
    ) -> Optional[List[Dict[str, Any]]]:
        """获取港股数据 - 使用 SDK Fetcher"""
        try:
            symbol = ticker if ".HK" in ticker else f"{ticker.zfill(4)}.HK"

            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "1d": "1d",
                "1wk": "1wk",
                "1mo": "1mo",
            }
            interval = interval_map.get(request.resolution, "1d")

            end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
            if request.start_date:
                start_date = request.start_date
            else:
                days_map = {"1m": 7, "5m": 30, "15m": 60, "1h": 90, "1d": 365}
                days = days_map.get(request.resolution, 365)
                start_date = (datetime.now() - timedelta(days=days)).strftime(
                    "%Y-%m-%d"
                )

            result = await self.yf_fetcher.fetch_history(
                ticker=symbol,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
            )

            return result if result else None

        except Exception as e:
            logger.error(f"Error fetching HK stock data for {ticker}: {e}")
            return None

    async def _fetch_macro_data(
        self, ticker: str, request: ChartDataRequest
    ) -> Optional[List[Dict[str, Any]]]:
        """获取宏观指标数据 - 使用 SDK Fetcher"""
        try:
            symbol_map = {
                "US10Y": "^TNX",
                "DXY": "DX-Y.NYB",
                "VIX": "^VIX",
                "GOLD": "GC=F",
            }

            symbol = symbol_map.get(ticker)
            if not symbol:
                return None

            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "1d": "1d",
                "1wk": "1wk",
                "1mo": "1mo",
            }
            interval = interval_map.get(request.resolution, "1d")

            end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
            if request.start_date:
                start_date = request.start_date
            else:
                days_map = {"1m": 7, "5m": 30, "15m": 60, "1h": 90, "1d": 365}
                days = days_map.get(request.resolution, 365)
                start_date = (datetime.now() - timedelta(days=days)).strftime(
                    "%Y-%m-%d"
                )

            result = await self.yf_fetcher.fetch_history(
                ticker=symbol,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
            )

            return result if result else None

        except Exception as e:
            logger.error(f"Error fetching macro data for {ticker}: {e}")
            return None

    def _normalize_chart_data(self, raw_data: List[Dict[str, Any]]) -> List[OHLCVData]:
        """标准化图表数据格式"""
        normalized_data = []

        for row in raw_data:
            try:
                timestamp = self._parse_timestamp(row)

                ohlcv = OHLCVData(
                    timestamp=timestamp,
                    open=float(row.get("Open") or row.get("open", 0)),
                    high=float(row.get("High") or row.get("high", 0)),
                    low=float(row.get("Low") or row.get("low", 0)),
                    close=float(row.get("Close") or row.get("close", 0)),
                    volume=int(row.get("Volume") or row.get("volume", 0)),
                )
                normalized_data.append(ohlcv)
            except Exception as e:
                logger.warning(f"Error normalizing data row: {e}, row: {row}")
                continue

        return normalized_data

    def _parse_timestamp(self, row: Dict[str, Any]) -> datetime:
        """解析时间戳，处理多种格式"""
        ts_val = (
            row.get("Date")
            or row.get("date")
            or row.get("Datetime")
            or row.get("datetime")
        )

        if isinstance(ts_val, (int, float)):
            # 毫秒时间戳
            if ts_val > 10000000000:
                return datetime.fromtimestamp(ts_val / 1000)
            return datetime.fromtimestamp(ts_val)

        if isinstance(ts_val, str):
            try:
                # 尝试 ISO 格式
                return datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            except ValueError:
                pass

            try:
                # 尝试 yfinance 常见格式
                return datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S%z")
            except ValueError:
                pass

            try:
                return datetime.strptime(ts_val, "%Y-%m-%d")
            except ValueError:
                pass

        # 如果已经是 datetime 对象
        if isinstance(ts_val, datetime):
            return ts_val

        # 默认返回当前时间 (防止报错，但记录警告)
        logger.warning(f"Could not parse timestamp from {ts_val}")
        return datetime.now()

    async def get_sparkline(
        self, ticker: str, period: str = "5d", force_refresh: bool = False
    ) -> Optional[SparklineResponse]:
        """获取简略行情数据（用于前端组件展示）

        逻辑：
        1. 生成缓存键
        2. 检查Redis缓存（除非 force_refresh=True）
        3. 缓存未命中 -> 调用 SDK Fetcher 获取数据 -> 提取简略信息 -> 存缓存 -> 返回
        4. 缓存命中 -> 直接返回
        
        v2.1 优化：
        - 在 YFinance 限流时，如果有缓存则返回缓存数据（即使过期）
        - 增加缓存 TTL 到 10 分钟，减少限流期间的缓存失效
        """
        cache_key = f"sparkline:{ticker.upper()}:{period}"

        # 1. 尝试从Redis获取缓存
        cached_data = await self.redis_manager.get_json(cache_key)
        
        # 如果有缓存且不强制刷新，直接返回
        if cached_data and not force_refresh:
            logger.debug(f"Sparkline cache hit for {cache_key}")
            return SparklineResponse(
                ticker=ticker.upper(),
                period=period,
                current_price=cached_data["current_price"],
                change_percent=cached_data["change_percent"],
                sparkline_data=cached_data["sparkline_data"],
                last_updated=datetime.fromisoformat(cached_data["last_updated"]),
                data=cached_data.get("data", cached_data["sparkline_data"]),
                timestamps=cached_data.get("timestamps", []),
                high=cached_data.get("high", 0),
                low=cached_data.get("low", 0),
                cached=True,
                last_close_date=cached_data.get("last_close_date"),
            )

        # 2. 检查 YFinance 是否处于限流状态
        if is_yfinance_rate_limited():
            cooldown_remaining = get_yfinance_cooldown_remaining()
            # 如果有缓存（即使过期），在限流时返回缓存数据
            if cached_data:
                logger.warning(
                    f"YFinance rate limited for sparkline {ticker}, "
                    f"returning stale cache (cooldown remaining: {cooldown_remaining:.1f}s)"
                )
                return SparklineResponse(
                    ticker=ticker.upper(),
                    period=period,
                    current_price=cached_data["current_price"],
                    change_percent=cached_data["change_percent"],
                    sparkline_data=cached_data["sparkline_data"],
                    last_updated=datetime.fromisoformat(cached_data["last_updated"]),
                    data=cached_data.get("data", cached_data["sparkline_data"]),
                    timestamps=cached_data.get("timestamps", []),
                    high=cached_data.get("high", 0),
                    low=cached_data.get("low", 0),
                    cached=True,
                    last_close_date=cached_data.get("last_close_date"),
                )
            else:
                logger.warning(
                    f"YFinance rate limited for sparkline {ticker}, "
                    f"no cache available (cooldown remaining: {cooldown_remaining:.1f}s)"
                )
                return None

        # 3. 缓存未命中，从 SDK Fetcher 获取数据
        logger.debug(f"Sparkline cache miss for {cache_key}, fetching from SDK")

        # 将 period 转换为日期范围
        period_map = {"5d": 5, "1m": 30, "3m": 90, "1y": 365, "5y": 1825}
        days = period_map.get(period, 5)

        request = ChartDataRequest(
            ticker=ticker,
            resolution="1d",
            start_date=(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
            limit=100,
        )

        raw_data = await self._fetch_from_sdk(request)

        if not raw_data or len(raw_data) == 0:
            # 如果获取失败但有缓存，返回缓存数据
            if cached_data:
                logger.warning(f"SDK fetch failed for sparkline {ticker}, returning stale cache")
                return SparklineResponse(
                    ticker=ticker.upper(),
                    period=period,
                    current_price=cached_data["current_price"],
                    change_percent=cached_data["change_percent"],
                    sparkline_data=cached_data["sparkline_data"],
                    last_updated=datetime.fromisoformat(cached_data["last_updated"]),
                    data=cached_data.get("data", cached_data["sparkline_data"]),
                    timestamps=cached_data.get("timestamps", []),
                    high=cached_data.get("high", 0),
                    low=cached_data.get("low", 0),
                    cached=True,
                    last_close_date=cached_data.get("last_close_date"),
                )
            return None

        # 4. 提取简略信息
        chart_data = self._normalize_chart_data(raw_data)

        if len(chart_data) == 0:
            return None

        # 计算变化百分比
        first_close = chart_data[0].close
        last_close = chart_data[-1].close
        change_percent = (
            ((last_close - first_close) / first_close * 100) if first_close > 0 else 0
        )

        # 提取简化的价格数据点（只保留收盘价）
        sparkline_data = [item.close for item in chart_data]

        # 计算高低点
        high_price = max(item.high for item in chart_data) if chart_data else 0
        low_price = min(item.low for item in chart_data) if chart_data else 0

        # 提取时间戳标签
        timestamps = [item.timestamp.strftime("%Y-%m-%d") for item in chart_data]

        # 获取最后收盘价的日期
        last_close_date = chart_data[-1].timestamp.strftime("%Y-%m-%d") if chart_data else None

        # 5. 存储到Redis缓存（缓存10分钟，增加以应对限流）
        cache_data = {
            "current_price": last_close,
            "change_percent": change_percent,
            "sparkline_data": sparkline_data,
            "last_updated": datetime.now().isoformat(),
            "data": sparkline_data,
            "timestamps": timestamps,
            "high": high_price,
            "low": low_price,
            "last_close_date": last_close_date,
        }

        await self.redis_manager.set(cache_key, cache_data, ttl=600)

        return SparklineResponse(
            ticker=ticker.upper(),
            period=period,
            current_price=last_close,
            change_percent=change_percent,
            sparkline_data=sparkline_data,
            last_updated=datetime.now(),
            data=sparkline_data,
            timestamps=timestamps,
            high=high_price,
            low=low_price,
            cached=False,
            last_close_date=last_close_date,
        )
