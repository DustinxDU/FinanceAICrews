"""
AkShare Fetcher - A股、港股数据获取

直接使用 akshare 库，不经过 MCP HTTP API
"""

import asyncio
from typing import Any, Dict, List, Optional

from AICrews.observability.logging import get_logger
from .sdk_fetcher import SDKFetcherBase

logger = get_logger(__name__)


class AkShareFetcher(SDKFetcherBase):
    """AkShare 数据获取器

    使用 ProviderRateLimiter 控制请求速率，防止 API 限流。
    """

    def __init__(self):
        import akshare as ak
        from AICrews.infrastructure.limits.provider_limiter import get_provider_limiter

        self.ak = ak
        self._limiter = get_provider_limiter()

    async def fetch_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取 A股/港股实时价格

        使用 ProviderRateLimiter 控制请求速率。
        """
        await self._limiter.acquire("akshare")
        try:
            ticker_upper = ticker.upper()

            if ticker_upper.endswith(".HK"):
                return await self._fetch_hk_price(ticker_upper)
            elif ticker_upper.endswith(".SS") or ticker_upper.endswith(".SZ"):
                return await self._fetch_cn_price(ticker_upper)
            else:
                return await self._fetch_cn_by_code(ticker)
        except Exception as e:
            logger.error(f"AkShare fetch_price error for {ticker}: {e}")
            return None
        finally:
            self._limiter.release("akshare")

    async def _fetch_hk_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取港股价格"""
        import akshare as ak

        code = ticker.replace(".HK", "").zfill(5)

        def fetch():
            try:
                df = ak.stock_hk_spot()
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        row_code = str(row.get("symbol", "") or row.get("代码", ""))
                        if code in row_code or row_code.endswith(code):
                            return {
                                "price": row.get("lasttrade") or row.get("最新价"),
                                "prev_close": row.get("prevclose") or row.get("昨收"),
                                "name": row.get("name") or row.get("名称", ticker),
                            }
            except Exception as e:
                logger.warning(f"AkShare HK spot failed: {e}")
            return None

        result = await asyncio.to_thread(fetch)
        if not result:
            return None

        price = result.get("price")
        prev_close = result.get("prev_close")

        if price and prev_close:
            try:
                price = float(price)
                prev_close = float(prev_close)
                change = price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0

                return {
                    "price": price,
                    "change": change,
                    "change_percent": change_pct,
                    "name": result.get("name"),
                    "currency": "HKD",
                }
            except (ValueError, TypeError):
                pass

        return None

    async def _fetch_cn_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取 A股价格"""
        import akshare as ak

        code = ticker.replace(".SS", "").replace(".SZ", "")

        def fetch():
            try:
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        if str(row.get("代码", "")) == code:
                            return row.to_dict()
            except Exception as e:
                logger.warning(f"AkShare CN spot failed: {e}")
            return None

        row_data = await asyncio.to_thread(fetch)
        if not row_data:
            return None

        def safe_float(value, default=0):
            try:
                val = float(value) if value is not None else default
                return default if (val != val) else val
            except (ValueError, TypeError):
                return default

        price = safe_float(row_data.get("最新价"))
        change = safe_float(row_data.get("涨跌额"))
        change_pct = safe_float(row_data.get("涨跌幅"))

        if price > 0:
            return {
                "price": price,
                "change": change,
                "change_percent": change_pct,
                "volume": row_data.get("成交量"),
                "high": row_data.get("最高"),
                "low": row_data.get("最低"),
                "name": row_data.get("名称"),
                "currency": "CNY",
            }

        return None

    async def _fetch_cn_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """通过纯数字代码获取 A股"""
        if len(code) == 6 and code.isdigit():
            if code.startswith(("0", "3")):
                ticker = f"{code}.SZ"
            else:
                ticker = f"{code}.SS"
            return await self._fetch_cn_price(ticker)
        return None

    async def fetch_history(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> Optional[List[Dict[str, Any]]]:
        """获取 A股历史数据

        使用 ProviderRateLimiter 控制请求速率。
        """
        await self._limiter.acquire("akshare")
        try:
            ticker_upper = ticker.upper()
            import akshare as ak

            if ticker_upper.endswith(".SS") or ticker_upper.endswith(".SZ"):
                code = ticker_upper.replace(".SS", "").replace(".SZ", "")
                func = ak.stock_zh_a_hist
                kwargs = {"symbol": code, "period": interval}
            elif ticker_upper.endswith(".HK"):
                code = ticker_upper.replace(".HK", "").zfill(5)
                func = ak.stock_hk_daily
                kwargs = {"symbol": code}
            else:
                return None

            def fetch():
                try:
                    df = func(**kwargs)
                    if df is not None and not df.empty:
                        return df
                except Exception as e:
                    logger.warning(f"AkShare history failed for {ticker}: {e}")
                return None

            df = await asyncio.to_thread(fetch)
            if df is None:
                return None

            result = []
            for _, row in df.iterrows():
                result.append(
                    {
                        "date": str(row.get("日期", "")),
                        "open": float(row.get("开盘", 0)),
                        "high": float(row.get("最高", 0)),
                        "low": float(row.get("最低", 0)),
                        "close": float(row.get("收盘", 0)),
                        "volume": int(row.get("成交量", 0)),
                    }
                )

            return result
        except Exception as e:
            logger.error(f"AkShare fetch_history error for {ticker}: {e}")
            return None
        finally:
            self._limiter.release("akshare")

    async def fetch_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取 A股/港股报价"""
        price_data = await self.fetch_price(ticker)
        if price_data:
            return {
                "ticker": ticker,
                "name": price_data.get("name"),
                "price": price_data.get("price"),
                "change": price_data.get("change"),
                "change_percent": price_data.get("change_percent"),
                "currency": price_data.get("currency", "CNY"),
            }
        return None


_akshare_fetcher: Optional[AkShareFetcher] = None


def get_akshare_fetcher() -> AkShareFetcher:
    """获取 AkShare Fetcher 单例"""
    global _akshare_fetcher
    if _akshare_fetcher is None:
        _akshare_fetcher = AkShareFetcher()
    return _akshare_fetcher
