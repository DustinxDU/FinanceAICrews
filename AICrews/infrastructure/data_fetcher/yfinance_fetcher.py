"""
YFinance Fetcher - 美股、加密货币数据获取

直接使用 yfinance 库，不经过 MCP HTTP API

v2.1 更新：
- 添加 429 错误检测和全局冷却机制
- 当检测到 Rate Limit 时，所有请求暂停一段时间
- 使用指数退避策略处理持续的限流
"""

from AICrews.observability.logging import get_logger
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import asyncio
import os
import time

import yfinance as yf

from .sdk_fetcher import SDKFetcherBase

logger = get_logger(__name__)


# 全局冷却状态（跨所有 YFinanceFetcher 实例共享）
_global_cooldown_until: float = 0.0
_consecutive_rate_limits: int = 0
_cooldown_lock = asyncio.Lock()


def is_yfinance_rate_limited() -> bool:
    """检查 YFinance 是否处于限流冷却状态
    
    供外部服务调用，用于在发起请求前检查是否应该跳过。
    这是一个同步方法，可以在任何地方调用。
    
    Returns:
        True 如果当前处于冷却状态，应该跳过请求
    """
    return time.time() < _global_cooldown_until


def get_yfinance_cooldown_remaining() -> float:
    """获取 YFinance 冷却剩余时间（秒）
    
    Returns:
        剩余冷却时间，如果不在冷却状态则返回 0
    """
    remaining = _global_cooldown_until - time.time()
    return max(0.0, remaining)


def _is_rate_limit_error(error: Exception) -> bool:
    """检测是否为速率限制错误
    
    注意：yfinance 库在遇到 429 错误时可能显示误导性的错误信息，
    如 "possibly delisted" 或 "no price data found"。
    """
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in [
        "too many requests",
        "rate limit",
        "429",
        "yfrateerror",
        "yfratelmiterror",
        "possibly delisted",  # yfinance 在 429 时的误导性错误
        "no price data found",  # yfinance 在 429 时的另一个误导性错误
    ])


def _is_network_error(error: Exception) -> bool:
    """检测是否为网络连接错误
    
    网络错误也应该触发冷却，因为持续重试只会浪费资源。
    """
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in [
        "connection timed out",
        "connection refused",
        "network unreachable",
        "name resolution",
        "curl:",
        "timeout",
    ])


class YFinanceFetcher(SDKFetcherBase):
    """YFinance 数据获取器

    特性：
    - 使用 ProviderRateLimiter 控制请求速率
    - 全局冷却机制：当检测到 429 错误时，所有请求暂停
    - 指数退避：连续 429 错误会增加冷却时间
    """

    # 冷却时间配置（秒）
    BASE_COOLDOWN_SECONDS = int(os.getenv("FAIC_YFINANCE_BASE_COOLDOWN_SECONDS", "60"))
    MAX_COOLDOWN_SECONDS = int(os.getenv("FAIC_YFINANCE_MAX_COOLDOWN_SECONDS", "300"))

    def __init__(self):
        from AICrews.infrastructure.limits.provider_limiter import get_provider_limiter
        self._limiter = get_provider_limiter()

    async def _wait_for_cooldown(self) -> None:
        """等待全局冷却结束"""
        global _global_cooldown_until

        now = time.time()
        if _global_cooldown_until > now:
            wait_time = _global_cooldown_until - now
            logger.warning(
                "YFinance in cooldown, waiting %.1f seconds before request",
                wait_time
            )
            await asyncio.sleep(wait_time)

    async def _trigger_cooldown(self) -> None:
        """触发全局冷却（当检测到 429 错误时调用）"""
        global _global_cooldown_until, _consecutive_rate_limits

        async with _cooldown_lock:
            _consecutive_rate_limits += 1

            # 指数退避：每次连续 429 错误，冷却时间翻倍
            cooldown_seconds = min(
                self.BASE_COOLDOWN_SECONDS * (2 ** (_consecutive_rate_limits - 1)),
                self.MAX_COOLDOWN_SECONDS
            )

            _global_cooldown_until = time.time() + cooldown_seconds

            logger.warning(
                "YFinance rate limited! Triggering global cooldown: %d seconds "
                "(consecutive errors: %d)",
                cooldown_seconds,
                _consecutive_rate_limits
            )

    async def _reset_cooldown_counter(self) -> None:
        """重置连续错误计数（成功请求后调用）"""
        global _consecutive_rate_limits

        if _consecutive_rate_limits > 0:
            async with _cooldown_lock:
                _consecutive_rate_limits = 0

    async def fetch_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取实时价格

        使用 ProviderRateLimiter 控制请求速率，防止 API 限流。
        包含全局冷却机制，当检测到 429 错误时暂停所有请求。
        """
        # 先等待冷却结束
        await self._wait_for_cooldown()

        await self._limiter.acquire("yfinance")
        try:
            stock = yf.Ticker(ticker)

            # Prefer fast_info for performance, but fall back to info for indices/special symbols.
            try:
                fast_info = stock.fast_info

                last_price = getattr(fast_info, "last_price", None) or 0
                prev_close = getattr(fast_info, "regularMarketPreviousClose", None)

                if last_price and prev_close:
                    await self._reset_cooldown_counter()
                    return {
                        "price": last_price,
                        "change": last_price - prev_close,
                        "change_percent": ((last_price - prev_close) / prev_close * 100)
                        if prev_close
                        else 0,
                        "volume": getattr(fast_info, "last_volume", None),
                        "high": getattr(fast_info, "day_high", None),
                        "low": getattr(fast_info, "day_low", None),
                    }
            except Exception as e:
                if _is_rate_limit_error(e) or _is_network_error(e):
                    logger.error(f"YFinance fetch_price error for {ticker}: {e}")
                    await self._trigger_cooldown()
                    return None
                logger.debug(
                    "YFinance fast_info unavailable for %s; falling back to info",
                    ticker,
                    exc_info=True,
                )

            try:
                info = stock.info or {}
                price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
                prev_close = (
                    info.get("regularMarketPreviousClose") or info.get("previousClose") or price
                )

                if not price:
                    return None

                high = info.get("regularMarketDayHigh") or info.get("dayHigh")
                low = info.get("regularMarketDayLow") or info.get("dayLow")
                volume = info.get("regularMarketVolume") or info.get("volume")

                await self._reset_cooldown_counter()
                return {
                    "price": float(price),
                    "change": float(price) - float(prev_close or 0),
                    "change_percent": ((float(price) - float(prev_close or 0)) / float(prev_close) * 100)
                    if prev_close
                    else 0,
                    "volume": volume,
                    "high": high,
                    "low": low,
                }
            except Exception as e:
                if _is_rate_limit_error(e) or _is_network_error(e):
                    await self._trigger_cooldown()
                logger.error(f"YFinance fetch_price error for {ticker}: {e}")
                return None
        finally:
            self._limiter.release("yfinance")

    async def fetch_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """获取历史 K 线数据

        使用 ProviderRateLimiter 控制请求速率。
        包含全局冷却机制。

        Args:
            ticker: 股票代码
            period: 获取周期 (如 "1d", "5d", "1mo", "1y")，当 start_date/end_date 未指定时使用
            interval: 数据间隔 (如 "1m", "5m", "1h", "1d")
            start_date: 开始日期 (YYYY-MM-DD 格式)，指定后忽略 period
            end_date: 结束日期 (YYYY-MM-DD 格式)，指定后忽略 period

        Returns:
            K 线数据列表，每条包含 timestamp, open, high, low, close, volume
        """
        # 先等待冷却结束
        await self._wait_for_cooldown()

        await self._limiter.acquire("yfinance")
        try:
            stock = yf.Ticker(ticker)

            # 如果指定了 start_date 和 end_date，使用日期范围查询
            if start_date and end_date:
                df = stock.history(start=start_date, end=end_date, interval=interval)
            else:
                df = stock.history(period=period, interval=interval)

            if df is None or df.empty:
                return None

            result = []
            for idx, row in df.iterrows():
                result.append(
                    {
                        "timestamp": idx.isoformat(),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    }
                )

            await self._reset_cooldown_counter()
            return result
        except Exception as e:
            if _is_rate_limit_error(e) or _is_network_error(e):
                await self._trigger_cooldown()
            logger.error(f"YFinance fetch_history error for {ticker}: {e}")
            return None
        finally:
            self._limiter.release("yfinance")

    async def fetch_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取完整报价信息

        使用 ProviderRateLimiter 控制请求速率。
        包含全局冷却机制。
        """
        # 先等待冷却结束
        await self._wait_for_cooldown()

        await self._limiter.acquire("yfinance")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            await self._reset_cooldown_counter()
            return {
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName"),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "change": info.get("regularMarketChange"),
                "change_percent": info.get("regularMarketChangePercent"),
                "volume": info.get("regularMarketVolume"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
            }
        except Exception as e:
            if _is_rate_limit_error(e) or _is_network_error(e):
                await self._trigger_cooldown()
            logger.error(f"YFinance fetch_quote error for {ticker}: {e}")
            return None
        finally:
            self._limiter.release("yfinance")

    async def fetch_crypto_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """专门获取加密货币价格"""
        symbol = ticker if "-USD" in ticker else f"{ticker}-USD"
        return await self.fetch_price(symbol)

    # 批量请求的最大 ticker 数量（避免单次请求过大触发限流）
    BATCH_CHUNK_SIZE = int(os.getenv("FAIC_YFINANCE_BATCH_CHUNK_SIZE", "20"))

    async def fetch_prices_batch(
        self, tickers: List[str], period: str = "2d"
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """批量获取多个 ticker 的价格数据

        使用 yf.download() 进行批量请求，显著减少 API 调用次数。
        包含全局冷却机制和分批处理，避免触发速率限制。

        v2.1 更新：
        - 添加分批处理（每批最多 BATCH_CHUNK_SIZE 个 ticker）
        - 批次之间添加延迟，避免连续请求
        - 检测 429 错误并触发全局冷却

        Args:
            tickers: ticker 列表
            period: 获取周期（默认 2d，获取最近两天数据以计算涨跌）

        Returns:
            Dict[ticker, price_data] 映射
        """
        if not tickers:
            return {}

        # 先等待冷却结束
        await self._wait_for_cooldown()

        results: Dict[str, Optional[Dict[str, Any]]] = {}

        # 分批处理，避免单次请求过大
        chunks = [
            tickers[i:i + self.BATCH_CHUNK_SIZE]
            for i in range(0, len(tickers), self.BATCH_CHUNK_SIZE)
        ]

        for chunk_idx, chunk in enumerate(chunks):
            # 批次之间添加延迟（除了第一批）
            if chunk_idx > 0:
                delay = 2.0  # 批次间延迟 2 秒
                logger.debug(f"Batch {chunk_idx + 1}/{len(chunks)}: waiting {delay}s before next chunk")
                await asyncio.sleep(delay)

            # 检查是否进入冷却状态
            await self._wait_for_cooldown()

            chunk_results = await self._fetch_batch_chunk(chunk, period)
            results.update(chunk_results)

        # 填充未处理的 ticker
        for ticker in tickers:
            if ticker not in results:
                results[ticker] = None

        success_count = len([v for v in results.values() if v])
        logger.info(f"Batch fetched {success_count}/{len(tickers)} tickers in {len(chunks)} chunks")
        return results

    async def _fetch_batch_chunk(
        self, tickers: List[str], period: str
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """获取单个批次的数据"""
        await self._limiter.acquire("yfinance")
        try:
            results: Dict[str, Optional[Dict[str, Any]]] = {}

            # yf.download 支持批量下载，极大减少 API 调用
            df = yf.download(
                tickers,
                period=period,
                interval="1d",
                group_by="ticker",
                progress=False,  # 禁用 tqdm 进度条
                threads=False,   # 禁用多线程，避免更多 API 调用
            )

            if df is None or df.empty:
                return {t: None for t in tickers}

            # 处理单个 ticker 的特殊情况（DataFrame 结构不同）
            if len(tickers) == 1:
                ticker = tickers[0]
                try:
                    if not df.empty:
                        last_row = df.iloc[-1]
                        close = float(last_row.get("Close", 0) or 0)
                        prev_close = float(df.iloc[-2].get("Close", close) or close) if len(df) > 1 else close

                        results[ticker] = {
                            "price": close,
                            "change": close - prev_close,
                            "change_percent": ((close - prev_close) / prev_close * 100) if prev_close else 0,
                            "volume": int(last_row.get("Volume", 0) or 0),
                            "high": float(last_row.get("High", 0) or 0),
                            "low": float(last_row.get("Low", 0) or 0),
                        }
                    else:
                        results[ticker] = None
                except Exception as e:
                    logger.debug(f"Error parsing batch data for {ticker}: {e}")
                    results[ticker] = None

                await self._reset_cooldown_counter()
                return results

            # 处理多个 ticker
            for ticker in tickers:
                try:
                    if ticker in df.columns.get_level_values(0):
                        ticker_df = df[ticker]
                        if not ticker_df.empty and not ticker_df.isna().all().all():
                            last_row = ticker_df.iloc[-1]
                            close = float(last_row.get("Close", 0) or 0)

                            # 尝试获取前一天收盘价
                            prev_close = close
                            if len(ticker_df) > 1:
                                prev_row = ticker_df.iloc[-2]
                                prev_close = float(prev_row.get("Close", close) or close)

                            if close > 0:
                                results[ticker] = {
                                    "price": close,
                                    "change": close - prev_close,
                                    "change_percent": ((close - prev_close) / prev_close * 100) if prev_close else 0,
                                    "volume": int(last_row.get("Volume", 0) or 0),
                                    "high": float(last_row.get("High", 0) or 0),
                                    "low": float(last_row.get("Low", 0) or 0),
                                }
                            else:
                                results[ticker] = None
                        else:
                            results[ticker] = None
                    else:
                        results[ticker] = None
                except Exception as e:
                    logger.debug(f"Error parsing batch data for {ticker}: {e}")
                    results[ticker] = None

            await self._reset_cooldown_counter()
            return results

        except Exception as e:
            if _is_rate_limit_error(e) or _is_network_error(e):
                await self._trigger_cooldown()
            logger.error(f"YFinance batch fetch error: {e}")
            return {t: None for t in tickers}
        finally:
            self._limiter.release("yfinance")


_yfinance_fetcher: Optional[YFinanceFetcher] = None


def get_yfinance_fetcher() -> YFinanceFetcher:
    """获取 YFinance Fetcher 单例"""
    global _yfinance_fetcher
    if _yfinance_fetcher is None:
        _yfinance_fetcher = YFinanceFetcher()
    return _yfinance_fetcher
