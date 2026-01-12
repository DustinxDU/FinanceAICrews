"""
Market Data Tools - 市场数据工具

提供统一的市场数据获取接口，供 CrewAI Agent 使用。
数据源：yfinance (美股、港股、加密货币)

使用方式:
    client = MarketDataClient()

    # 获取历史数据
    df = await client.get_historical_data("AAPL", period="3mo")

    # 获取实时行情
    quote = await client.get_realtime_quote("AAPL")
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import concurrent.futures

import pandas as pd

from crewai.tools import tool
from AICrews.observability.logging import get_logger

logger = get_logger(__name__)


class MarketDataClient:
    """市场数据客户端

    提供统一的市场数据获取接口，使用 yfinance 作为数据源。
    """

    def __init__(self):
        pass

    async def get_historical_data(
        self, ticker: str, period: str = "3mo", interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """获取历史价格数据

        Args:
            ticker: 股票代码
            period: 时间周期 (1mo, 3mo, 6mo, 1y, 2y)
            interval: 数据间隔 (1d, 1wk, 1mo)

        Returns:
            包含 OHLCV 数据的 DataFrame
        """
        try:
            # 使用 yfinance 获取数据
            logger.info(f"Fetching historical data for {ticker} via yfinance")
            df = await self._fetch_with_yfinance(ticker, period)
            if df is not None and len(df) > 0:
                return df

            # 回退到模拟数据 (仅用于演示)
            logger.warning(f"yfinance failed for {ticker}, using mock data")
            return self._generate_mock_data(ticker, period)

        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            return self._generate_mock_data(ticker, period)

    async def _fetch_with_yfinance(
        self, ticker: str, period: str
    ) -> Optional[pd.DataFrame]:
        """使用 yfinance 作为备选数据源"""
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            df = stock.history(period=period)

            if df is not None and len(df) > 0:
                df = df.reset_index()
                df.columns = df.columns.str.lower()
                return df

        except ImportError:
            logger.warning("yfinance not installed")
        except Exception as e:
            logger.warning(f"yfinance fetch error for {ticker}: {e}")

        return self._generate_mock_data(ticker, period)

    def _generate_mock_data(self, ticker: str, period: str) -> pd.DataFrame:
        """生成模拟数据（用于测试和演示）"""
        import random

        # 根据 period 确定天数
        period_days = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252, "2y": 504}
        days = period_days.get(period, 66)

        # 生成模拟数据
        base_price = 100.0 + random.random() * 100
        data = []
        now = datetime.now()

        for i in range(days):
            date = now - timedelta(days=days - i)
            change = random.uniform(-0.03, 0.03)
            open_price = base_price
            close_price = base_price * (1 + change)
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
            volume = random.randint(1000000, 10000000)

            data.append(
                {
                    "date": date,
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": volume,
                }
            )
            base_price = close_price

        return pd.DataFrame(data)

    async def get_realtime_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取实时行情

        Args:
            ticker: 股票代码

        Returns:
            包含价格、涨跌幅、成交量等信息的字典
        """
        try:
            logger.info(f"Fetching realtime quote for {ticker} via yfinance")
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.fast_info
            return {
                "ticker": ticker,
                "price": info.last_price,
                "change": None,  # fast_info doesn't have change
                "change_percent": None,
                "volume": info.last_volume,
                "high": info.day_high,
                "low": info.day_low,
                "source": "yfinance",
            }
        except Exception as e:
            logger.warning(f"yfinance quote failed for {ticker}: {e}")
            return None

    async def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取基本面数据

        Args:
            ticker: 股票代码

        Returns:
            包含市值、PE、行业等信息的字典
        """
        try:
            import yfinance as yf

            logger.info(f"Fetching fundamentals for {ticker} via yfinance")
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                "ticker": ticker,
                "name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
            }
        except Exception as e:
            logger.warning(f"Failed to get fundamentals for {ticker}: {e}")
            return None

    async def get_news(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取相关新闻

        Args:
            ticker: 股票代码
            limit: 返回的新闻数量

        Returns:
            新闻列表
        """
        try:
            import yfinance as yf

            logger.info(f"Fetching news for {ticker} via yfinance")
            stock = yf.Ticker(ticker)
            news = stock.news

            if news:
                result = []
                for item in news[:limit]:
                    content = item.get("content", item)
                    title = (
                        content.get("title", "")
                        if isinstance(content, dict)
                        else item.get("title", "")
                    )
                    if title:
                        result.append({"title": title})
                return result

            return []
        except Exception as e:
            logger.warning(f"Failed to get news for {ticker}: {e}")
            return []


# =========================================================================
# CrewAI 工具函数
# =========================================================================

_market_client = MarketDataClient()


@tool("get_stock_price")
def get_stock_price(ticker: str) -> str:
    """获取股票的当前价格和基本行情信息

    Args:
        ticker: 股票代码 (如 "AAPL", "MSFT", "GOOGL")

    Returns:
        当前价格、涨跌幅、成交量等信息
    """

    import re

    raw_ticker = str(ticker or "").strip()
    if not raw_ticker:
        return "Invalid ticker format: Ticker cannot be empty"
    if not re.fullmatch(r"[A-Za-z0-9.\-]+", raw_ticker):
        return "Invalid ticker format: ticker contains invalid characters"

    normalized = raw_ticker.upper()
    if re.fullmatch(r"\d{4}\.HK", normalized):
        pass
    elif re.fullmatch(r"\d{6}\.(SS|SZ)", normalized):
        pass
    elif re.fullmatch(r"\d{4}", normalized):
        normalized = f"{normalized}.HK"
    elif re.fullmatch(r"\d{6}", normalized):
        normalized = (
            f"{normalized}.SS" if normalized.startswith("6") else f"{normalized}.SZ"
        )

    async def _get_price():
        quote = await _market_client.get_realtime_quote(normalized)
        if quote:
            return f"""
{normalized} Current Quote:
- Price: ${quote.get("price", "N/A")}
- Change: {quote.get("change", "N/A")} ({quote.get("change_percent", "N/A")}%)
- Volume: {quote.get("volume", "N/A"):,}
- Day High: ${quote.get("high", "N/A")}
- Day Low: ${quote.get("low", "N/A")}
""".strip()
        return f"Unable to get quote for {normalized}"

    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_price())
                return future.result()
        else:
            return loop.run_until_complete(_get_price())
    except Exception as e:
        return f"Error getting price for {normalized}: {str(e)}"


@tool("get_stock_fundamentals")
def get_stock_fundamentals(ticker: str) -> str:
    """获取股票的基本面数据

    包括市值、PE比率、股息率、所属行业等信息。

    Args:
        ticker: 股票代码

    Returns:
        基本面数据摘要
    """

    async def _get_fundamentals():
        data = await _market_client.get_fundamentals(ticker)
        if data:
            return f"""
{ticker} Fundamentals:
- Company: {data.get("name", "N/A")}
- Sector: {data.get("sector", "N/A")}
- Industry: {data.get("industry", "N/A")}
- Market Cap: ${data.get("market_cap", 0):,.0f}
- P/E Ratio: {data.get("pe_ratio", "N/A")}
- Forward P/E: {data.get("forward_pe", "N/A")}
- Dividend Yield: {data.get("dividend_yield", "N/A")}
- Beta: {data.get("beta", "N/A")}
- 52-Week High: ${data.get("52_week_high", "N/A")}
- 52-Week Low: ${data.get("52_week_low", "N/A")}
""".strip()
        return f"Unable to get fundamentals for {ticker}"

    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_fundamentals())
                return future.result()
        else:
            return loop.run_until_complete(_get_fundamentals())
    except Exception as e:
        return f"Error getting fundamentals for {ticker}: {str(e)}"


@tool("get_stock_news")
def get_stock_news(ticker: str, limit: int = 5) -> str:
    """获取股票相关的最新新闻

    Args:
        ticker: 股票代码
        limit: 返回的新闻数量，默认5条

    Returns:
        新闻标题和链接列表
    """

    async def _get_news():
        news_list = await _market_client.get_news(ticker, limit)
        if news_list:
            output = f"Latest News for {ticker}:\n\n"
            for i, news in enumerate(news_list, 1):
                title = news.get("title") or news.get("标题", "No title")
                output += f"{i}. {title}\n"
            return output.strip()
        return f"No recent news found for {ticker}"

    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_news())
                return future.result()
        else:
            return loop.run_until_complete(_get_news())
    except Exception as e:
        return f"Error getting news for {ticker}: {str(e)}"
