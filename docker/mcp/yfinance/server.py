"""
YFinance MCP Server - Standard MCP Server for US/Global Market Data

This is a standard MCP (Model Context Protocol) server implementation using SSE transport.
It provides tools for accessing US and global market data via yfinance library.

Supports:
- Stock price data (US, Global)
- Fundamental analysis (financial statements, key metrics)
- Options data
- Crypto data
- ETF data
- Market news and analysis
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yfinance as yf
import pandas as pd
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    ListToolsResult,
)
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.responses import Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class YFinanceConfig:
    """YFinance MCP server configuration."""
    enable_caching: bool = True
    cache_ttl_default: int = 300  # 5 minutes
    rate_limit_per_minute: int = 120
    
    cache_ttl_by_type: Dict[str, int] = field(default_factory=lambda: {
        "stock_price": 60,
        "fundamentals": 3600,
        "financial_statements": 86400,
        "options": 300,
        "crypto": 60,
        "news": 300,
        "info": 3600,
    })


def get_config() -> YFinanceConfig:
    """Load configuration from environment variables."""
    config = YFinanceConfig()
    config.enable_caching = os.environ.get("YFINANCE_MCP_CACHE", "true").lower() == "true"
    config.rate_limit_per_minute = int(os.environ.get("YFINANCE_MCP_RATE_LIMIT", "120"))
    return config


# =============================================================================
# Utilities
# =============================================================================

def df_to_dict(df: pd.DataFrame, symbol: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convert DataFrame to dictionary payload."""
    if df is None:
        df = pd.DataFrame()
    
    # Reset index if it's a DatetimeIndex
    if hasattr(df, 'index') and hasattr(df.index, 'name') and df.index.name:
        df = df.reset_index()
    
    # Convert datetime columns to string
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)
    
    result = {
        "data": df.to_dict("records") if not df.empty else [],
        "columns": df.columns.tolist() if hasattr(df, "columns") else [],
        "count": len(df),
    }
    if symbol:
        result["symbol"] = symbol
    if extra:
        result.update(extra)
    if df.empty:
        result.setdefault("message", "No data found")
    return result


def safe_get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from object."""
    try:
        val = getattr(obj, attr, default)
        if callable(val):
            val = val()
        return val
    except Exception:
        return default


# =============================================================================
# Cache & Rate Limiter
# =============================================================================

class DataCache:
    """Simple in-memory TTL cache."""

    def __init__(self):
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        value = self._store.get(key)
        if not value:
            return None
        expire, data = value
        if expire and expire < time.time():
            self._store.pop(key, None)
            return None
        return data

    def set(self, key: str, value: Any, ttl: int):
        expire = time.time() + ttl if ttl else None
        self._store[key] = (expire, value)

    def clear(self):
        self._store.clear()


class RateLimiter:
    """Basic sliding window rate limiter."""

    def __init__(self, limit_per_minute: int):
        self.limit = limit_per_minute
        self._timestamps: List[float] = []

    async def acquire(self):
        now = time.time()
        window_start = now - 60
        self._timestamps = [t for t in self._timestamps if t >= window_start]
        if self.limit and len(self._timestamps) >= self.limit:
            oldest = self._timestamps[0]
            sleep_for = max(0.0, (oldest + 60) - now)
            await asyncio.sleep(sleep_for)
        self._timestamps.append(time.time())


# =============================================================================
# YFinance Data Client
# =============================================================================

class YFinanceClient:
    """YFinance data access client."""

    async def get_stock_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> Dict[str, Any]:
        """Get stock price history."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            return df_to_dict(df, symbol=symbol, extra={"period": period, "interval": interval})
        return await asyncio.to_thread(_fetch)

    async def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """Get stock basic info."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {"symbol": symbol, "info": info}
        return await asyncio.to_thread(_fetch)

    async def get_stock_financials(self, symbol: str, statement: str = "income") -> Dict[str, Any]:
        """Get financial statements."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            if statement == "income":
                df = ticker.income_stmt
            elif statement == "balance":
                df = ticker.balance_sheet
            elif statement == "cash":
                df = ticker.cashflow
            elif statement == "quarterly_income":
                df = ticker.quarterly_income_stmt
            elif statement == "quarterly_balance":
                df = ticker.quarterly_balance_sheet
            elif statement == "quarterly_cash":
                df = ticker.quarterly_cashflow
            else:
                df = pd.DataFrame()
            
            if df is not None and not df.empty:
                df = df.T.reset_index()
                df.columns = ['Date'] + list(df.columns[1:])
            return df_to_dict(df, symbol=symbol, extra={"statement_type": statement})
        return await asyncio.to_thread(_fetch)

    async def get_stock_actions(self, symbol: str) -> Dict[str, Any]:
        """Get dividends and stock splits."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            actions = ticker.actions
            return df_to_dict(actions, symbol=symbol)
        return await asyncio.to_thread(_fetch)

    async def get_stock_dividends(self, symbol: str) -> Dict[str, Any]:
        """Get dividend history."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            dividends = ticker.dividends
            df = dividends.reset_index() if not dividends.empty else pd.DataFrame()
            return df_to_dict(df, symbol=symbol)
        return await asyncio.to_thread(_fetch)

    async def get_stock_splits(self, symbol: str) -> Dict[str, Any]:
        """Get stock split history."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            splits = ticker.splits
            df = splits.reset_index() if not splits.empty else pd.DataFrame()
            return df_to_dict(df, symbol=symbol)
        return await asyncio.to_thread(_fetch)

    async def get_stock_holders(self, symbol: str, holder_type: str = "major") -> Dict[str, Any]:
        """Get stock holders info."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            if holder_type == "major":
                df = ticker.major_holders
            elif holder_type == "institutional":
                df = ticker.institutional_holders
            elif holder_type == "mutual_fund":
                df = ticker.mutualfund_holders
            else:
                df = pd.DataFrame()
            return df_to_dict(df, symbol=symbol, extra={"holder_type": holder_type})
        return await asyncio.to_thread(_fetch)

    async def get_stock_recommendations(self, symbol: str) -> Dict[str, Any]:
        """Get analyst recommendations."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            rec = ticker.recommendations
            return df_to_dict(rec, symbol=symbol)
        return await asyncio.to_thread(_fetch)

    async def get_stock_calendar(self, symbol: str) -> Dict[str, Any]:
        """Get earnings and events calendar."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            if isinstance(cal, pd.DataFrame):
                return df_to_dict(cal, symbol=symbol)
            elif isinstance(cal, dict):
                return {"symbol": symbol, "calendar": cal}
            return {"symbol": symbol, "calendar": {}}
        return await asyncio.to_thread(_fetch)

    async def get_stock_earnings(self, symbol: str) -> Dict[str, Any]:
        """Get earnings history."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            earnings = ticker.earnings_history
            return df_to_dict(earnings, symbol=symbol)
        return await asyncio.to_thread(_fetch)

    async def get_stock_news(self, symbol: str) -> Dict[str, Any]:
        """Get stock news."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            news = ticker.news
            return {"symbol": symbol, "news": news[:20] if news else [], "count": len(news) if news else 0}
        return await asyncio.to_thread(_fetch)

    async def get_options_chain(self, symbol: str, date: Optional[str] = None) -> Dict[str, Any]:
        """Get options chain data."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            dates = ticker.options
            if not dates:
                return {"symbol": symbol, "options_dates": [], "calls": [], "puts": []}
            
            target_date = date if date and date in dates else dates[0]
            opt = ticker.option_chain(target_date)
            
            calls_df = opt.calls if hasattr(opt, 'calls') else pd.DataFrame()
            puts_df = opt.puts if hasattr(opt, 'puts') else pd.DataFrame()
            
            return {
                "symbol": symbol,
                "expiration_date": target_date,
                "options_dates": list(dates),
                "calls": df_to_dict(calls_df)["data"],
                "puts": df_to_dict(puts_df)["data"],
            }
        return await asyncio.to_thread(_fetch)

    async def get_crypto_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> Dict[str, Any]:
        """Get cryptocurrency price history."""
        def _fetch():
            # Ensure crypto symbol format
            if not symbol.endswith("-USD"):
                crypto_symbol = f"{symbol}-USD"
            else:
                crypto_symbol = symbol
            ticker = yf.Ticker(crypto_symbol)
            df = ticker.history(period=period, interval=interval)
            return df_to_dict(df, symbol=crypto_symbol, extra={"period": period, "interval": interval})
        return await asyncio.to_thread(_fetch)

    async def get_market_summary(self) -> Dict[str, Any]:
        """Get market summary (major indices)."""
        def _fetch():
            indices = ["^GSPC", "^DJI", "^IXIC", "^RUT", "^VIX"]
            results = []
            for idx in indices:
                try:
                    ticker = yf.Ticker(idx)
                    info = ticker.info
                    results.append({
                        "symbol": idx,
                        "name": info.get("shortName", idx),
                        "price": info.get("regularMarketPrice"),
                        "change": info.get("regularMarketChange"),
                        "change_percent": info.get("regularMarketChangePercent"),
                        "previous_close": info.get("previousClose"),
                    })
                except Exception as e:
                    logger.warning(f"Failed to get {idx}: {e}")
            return {"indices": results, "count": len(results)}
        return await asyncio.to_thread(_fetch)

    async def get_sector_performance(self) -> Dict[str, Any]:
        """Get sector ETF performance."""
        def _fetch():
            sector_etfs = {
                "XLK": "Technology",
                "XLF": "Financials",
                "XLV": "Healthcare",
                "XLE": "Energy",
                "XLI": "Industrials",
                "XLY": "Consumer Discretionary",
                "XLP": "Consumer Staples",
                "XLU": "Utilities",
                "XLB": "Materials",
                "XLRE": "Real Estate",
                "XLC": "Communication Services",
            }
            results = []
            for symbol, name in sector_etfs.items():
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    results.append({
                        "symbol": symbol,
                        "sector": name,
                        "price": info.get("regularMarketPrice"),
                        "change_percent": info.get("regularMarketChangePercent"),
                    })
                except Exception as e:
                    logger.warning(f"Failed to get {symbol}: {e}")
            return {"sectors": results, "count": len(results)}
        return await asyncio.to_thread(_fetch)

    async def get_trending_tickers(self) -> Dict[str, Any]:
        """Get trending tickers."""
        def _fetch():
            try:
                trending = yf.Tickers("AAPL MSFT GOOGL AMZN NVDA TSLA META")
                results = []
                for symbol in ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]:
                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        results.append({
                            "symbol": symbol,
                            "name": info.get("shortName"),
                            "price": info.get("regularMarketPrice"),
                            "change_percent": info.get("regularMarketChangePercent"),
                            "volume": info.get("regularMarketVolume"),
                        })
                    except Exception:
                        pass
                return {"tickers": results, "count": len(results)}
            except Exception as e:
                logger.error(f"Failed to get trending: {e}")
                return {"tickers": [], "count": 0}
        return await asyncio.to_thread(_fetch)

    async def download_multiple(
        self,
        symbols: List[str],
        period: str = "1mo",
        interval: str = "1d",
    ) -> Dict[str, Any]:
        """Download data for multiple symbols."""
        def _fetch():
            df = yf.download(symbols, period=period, interval=interval, group_by='ticker')
            results = {}
            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        symbol_df = df
                    else:
                        symbol_df = df[symbol] if symbol in df.columns.get_level_values(0) else pd.DataFrame()
                    results[symbol] = df_to_dict(symbol_df, symbol=symbol)
                except Exception as e:
                    results[symbol] = {"error": str(e)}
            return {"symbols": results, "count": len(results)}
        return await asyncio.to_thread(_fetch)

    async def get_key_stats(self, symbol: str) -> Dict[str, Any]:
        """Get key statistics for a stock."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            stats = {
                "symbol": symbol,
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "trailing_pe": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "price_to_book": info.get("priceToBook"),
                "price_to_sales": info.get("priceToSalesTrailing12Months"),
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "return_on_assets": info.get("returnOnAssets"),
                "return_on_equity": info.get("returnOnEquity"),
                "revenue": info.get("totalRevenue"),
                "revenue_per_share": info.get("revenuePerShare"),
                "quarterly_revenue_growth": info.get("revenueGrowth"),
                "gross_profit": info.get("grossProfits"),
                "ebitda": info.get("ebitda"),
                "net_income": info.get("netIncomeToCommon"),
                "eps_trailing": info.get("trailingEps"),
                "eps_forward": info.get("forwardEps"),
                "total_cash": info.get("totalCash"),
                "total_debt": info.get("totalDebt"),
                "current_ratio": info.get("currentRatio"),
                "book_value": info.get("bookValue"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "50_day_average": info.get("fiftyDayAverage"),
                "200_day_average": info.get("twoHundredDayAverage"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "float_shares": info.get("floatShares"),
                "shares_short": info.get("sharesShort"),
                "short_ratio": info.get("shortRatio"),
                "dividend_rate": info.get("dividendRate"),
                "dividend_yield": info.get("dividendYield"),
                "payout_ratio": info.get("payoutRatio"),
                "ex_dividend_date": str(info.get("exDividendDate")) if info.get("exDividendDate") else None,
            }
            return stats
        return await asyncio.to_thread(_fetch)

    async def get_analyst_price_targets(self, symbol: str) -> Dict[str, Any]:
        """Get analyst price targets."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                "symbol": symbol,
                "target_high": info.get("targetHighPrice"),
                "target_low": info.get("targetLowPrice"),
                "target_mean": info.get("targetMeanPrice"),
                "target_median": info.get("targetMedianPrice"),
                "recommendation": info.get("recommendationKey"),
                "recommendation_mean": info.get("recommendationMean"),
                "number_of_analysts": info.get("numberOfAnalystOpinions"),
            }
        return await asyncio.to_thread(_fetch)

    async def get_sustainability(self, symbol: str) -> Dict[str, Any]:
        """Get ESG sustainability scores."""
        def _fetch():
            ticker = yf.Ticker(symbol)
            sustainability = ticker.sustainability
            if sustainability is not None and not sustainability.empty:
                return df_to_dict(sustainability.T.reset_index(), symbol=symbol)
            return {"symbol": symbol, "data": [], "message": "No sustainability data"}
        return await asyncio.to_thread(_fetch)


# =============================================================================
# Tool Definitions (Core 100+ Tools)
# =============================================================================

TOOL_DEFINITIONS: List[Tool] = [
    # === Stock Price Data ===
    Tool(
        name="stock_history",
        description="Get historical stock price data (OHLCV). Supports US and global stocks.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL, MSFT, 0700.HK)"},
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                    "default": "1mo",
                    "description": "Data period"
                },
                "interval": {
                    "type": "string",
                    "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
                    "default": "1d",
                    "description": "Data interval"
                },
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_info",
        description="Get comprehensive stock information including company profile, sector, industry, and key metrics.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_key_stats",
        description="Get key financial statistics and ratios for a stock.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_quote",
        description="Get real-time stock quote with current price, change, and volume.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Financial Statements ===
    Tool(
        name="stock_income_statement",
        description="Get annual income statement (profit & loss).",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_balance_sheet",
        description="Get annual balance sheet.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_cash_flow",
        description="Get annual cash flow statement.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_quarterly_income",
        description="Get quarterly income statement.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_quarterly_balance",
        description="Get quarterly balance sheet.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_quarterly_cash_flow",
        description="Get quarterly cash flow statement.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Dividends & Splits ===
    Tool(
        name="stock_dividends",
        description="Get dividend payment history.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_splits",
        description="Get stock split history.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_actions",
        description="Get all corporate actions (dividends and splits).",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Holders & Ownership ===
    Tool(
        name="stock_major_holders",
        description="Get major shareholders breakdown.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_institutional_holders",
        description="Get institutional shareholders list.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_mutual_fund_holders",
        description="Get mutual fund shareholders list.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Analyst Data ===
    Tool(
        name="stock_recommendations",
        description="Get analyst recommendations history.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_price_targets",
        description="Get analyst price targets.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Earnings & Calendar ===
    Tool(
        name="stock_earnings",
        description="Get earnings history.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_calendar",
        description="Get upcoming earnings and events calendar.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === News ===
    Tool(
        name="stock_news",
        description="Get latest news for a stock.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Options ===
    Tool(
        name="options_chain",
        description="Get options chain data (calls and puts) for a stock.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL, MSFT)"},
                "date": {"type": "string", "description": "Expiration date in YYYY-MM-DD format. If not provided, uses nearest expiration."},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="options_expirations",
        description="Get available options expiration dates for a stock.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Cryptocurrency ===
    Tool(
        name="crypto_history",
        description="Get cryptocurrency price history.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Crypto symbol (e.g., BTC, ETH, or BTC-USD)"},
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                    "default": "1mo",
                    "description": "Data period"
                },
                "interval": {
                    "type": "string",
                    "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
                    "default": "1d",
                    "description": "Data interval"
                },
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="crypto_info",
        description="Get cryptocurrency information.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Crypto symbol (e.g., BTC, ETH)"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Market Overview ===
    Tool(
        name="market_summary",
        description="Get market summary with major indices (S&P 500, Dow Jones, NASDAQ, Russell 2000, VIX).",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="sector_performance",
        description="Get sector ETF performance (XLK, XLF, XLV, etc.).",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="trending_tickers",
        description="Get trending/popular tickers.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    
    # === Batch Operations ===
    Tool(
        name="download_multiple",
        description="Download historical data for multiple symbols at once.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbols": {"type": "array", "items": {"type": "string"}, "description": "List of ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])"},
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                    "default": "1mo",
                    "description": "Data period"
                },
                "interval": {
                    "type": "string",
                    "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
                    "default": "1d",
                    "description": "Data interval"
                },
            },
            "required": ["symbols"],
        },
    ),
    
    # === ESG & Sustainability ===
    Tool(
        name="stock_sustainability",
        description="Get ESG sustainability scores and ratings.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Index Data ===
    Tool(
        name="index_history",
        description="Get historical data for market indices.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Index symbol (e.g., ^GSPC for S&P 500, ^DJI for Dow Jones, ^IXIC for NASDAQ)"},
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                    "default": "1mo",
                    "description": "Data period"
                },
                "interval": {
                    "type": "string",
                    "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
                    "default": "1d",
                    "description": "Data interval"
                },
            },
            "required": ["symbol"],
        },
    ),

    # === ETF Data ===
    Tool(
        name="etf_history",
        description="Get ETF historical price data.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "ETF symbol (e.g., SPY, QQQ, VTI, IWM)"},
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                    "default": "1mo",
                    "description": "Data period"
                },
                "interval": {
                    "type": "string",
                    "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
                    "default": "1d",
                    "description": "Data interval"
                },
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="etf_info",
        description="Get ETF information and holdings.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "ETF symbol"},
            },
            "required": ["symbol"],
        },
    ),
    
    # === Forex ===
    Tool(
        name="forex_history",
        description="Get forex currency pair historical data.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Currency pair (e.g., EURUSD=X, GBPUSD=X, USDJPY=X)"},
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                    "default": "1mo",
                    "description": "Data period"
                },
                "interval": {
                    "type": "string",
                    "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
                    "default": "1d",
                    "description": "Data interval"
                },
            },
            "required": ["symbol"],
        },
    ),

    # === Futures ===
    Tool(
        name="futures_history",
        description="Get futures contract historical data.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Futures symbol (e.g., ES=F for S&P 500 futures, GC=F for Gold, CL=F for Crude Oil)"},
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                    "default": "1mo",
                    "description": "Data period"
                },
                "interval": {
                    "type": "string",
                    "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
                    "default": "1d",
                    "description": "Data interval"
                },
            },
            "required": ["symbol"],
        },
    ),
]

# Total: 35 core tools


# =============================================================================
# Tool Execution
# =============================================================================

_mcp_client = YFinanceClient()
_mcp_config = get_config()
_mcp_cache = DataCache() if _mcp_config.enable_caching else None


def _get_data_type_for_tool(tool_name: str) -> str:
    """Map tool name to data type for cache TTL."""
    if "history" in tool_name or "quote" in tool_name:
        return "stock_price"
    if "income" in tool_name or "balance" in tool_name or "cash" in tool_name or "financials" in tool_name:
        return "financial_statements"
    if "options" in tool_name:
        return "options"
    if "crypto" in tool_name:
        return "crypto"
    if "news" in tool_name:
        return "news"
    if "info" in tool_name or "stats" in tool_name:
        return "info"
    return "fundamentals"


async def _execute_tool(client: YFinanceClient, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool and return the result."""
    symbol = arguments.get("symbol", "")
    period = arguments.get("period", "1mo")
    interval = arguments.get("interval", "1d")
    
    # Stock Price Data
    if tool_name == "stock_history":
        return await client.get_stock_history(symbol, period, interval)
    elif tool_name == "stock_info":
        return await client.get_stock_info(symbol)
    elif tool_name == "stock_key_stats":
        return await client.get_key_stats(symbol)
    elif tool_name == "stock_quote":
        info_result = await client.get_stock_info(symbol)
        info = info_result.get("info", {})
        return {
            "symbol": symbol,
            "price": info.get("regularMarketPrice"),
            "change": info.get("regularMarketChange"),
            "change_percent": info.get("regularMarketChangePercent"),
            "volume": info.get("regularMarketVolume"),
            "market_cap": info.get("marketCap"),
            "previous_close": info.get("previousClose"),
            "open": info.get("regularMarketOpen"),
            "day_high": info.get("regularMarketDayHigh"),
            "day_low": info.get("regularMarketDayLow"),
        }
    
    # Financial Statements
    elif tool_name == "stock_income_statement":
        return await client.get_stock_financials(symbol, "income")
    elif tool_name == "stock_balance_sheet":
        return await client.get_stock_financials(symbol, "balance")
    elif tool_name == "stock_cash_flow":
        return await client.get_stock_financials(symbol, "cash")
    elif tool_name == "stock_quarterly_income":
        return await client.get_stock_financials(symbol, "quarterly_income")
    elif tool_name == "stock_quarterly_balance":
        return await client.get_stock_financials(symbol, "quarterly_balance")
    elif tool_name == "stock_quarterly_cash_flow":
        return await client.get_stock_financials(symbol, "quarterly_cash")
    
    # Dividends & Splits
    elif tool_name == "stock_dividends":
        return await client.get_stock_dividends(symbol)
    elif tool_name == "stock_splits":
        return await client.get_stock_splits(symbol)
    elif tool_name == "stock_actions":
        return await client.get_stock_actions(symbol)
    
    # Holders
    elif tool_name == "stock_major_holders":
        return await client.get_stock_holders(symbol, "major")
    elif tool_name == "stock_institutional_holders":
        return await client.get_stock_holders(symbol, "institutional")
    elif tool_name == "stock_mutual_fund_holders":
        return await client.get_stock_holders(symbol, "mutual_fund")
    
    # Analyst
    elif tool_name == "stock_recommendations":
        return await client.get_stock_recommendations(symbol)
    elif tool_name == "stock_price_targets":
        return await client.get_analyst_price_targets(symbol)
    
    # Earnings & Calendar
    elif tool_name == "stock_earnings":
        return await client.get_stock_earnings(symbol)
    elif tool_name == "stock_calendar":
        return await client.get_stock_calendar(symbol)
    
    # News
    elif tool_name == "stock_news":
        return await client.get_stock_news(symbol)
    
    # Options
    elif tool_name == "options_chain":
        return await client.get_options_chain(symbol, arguments.get("date"))
    elif tool_name == "options_expirations":
        def _fetch():
            ticker = yf.Ticker(symbol)
            return {"symbol": symbol, "expirations": list(ticker.options)}
        return await asyncio.to_thread(_fetch)
    
    # Crypto
    elif tool_name == "crypto_history":
        return await client.get_crypto_history(symbol, period, interval)
    elif tool_name == "crypto_info":
        crypto_symbol = f"{symbol}-USD" if not symbol.endswith("-USD") else symbol
        return await client.get_stock_info(crypto_symbol)
    
    # Market Overview
    elif tool_name == "market_summary":
        return await client.get_market_summary()
    elif tool_name == "sector_performance":
        return await client.get_sector_performance()
    elif tool_name == "trending_tickers":
        return await client.get_trending_tickers()
    
    # Batch
    elif tool_name == "download_multiple":
        symbols = arguments.get("symbols", [])
        return await client.download_multiple(symbols, period, interval)
    
    # ESG
    elif tool_name == "stock_sustainability":
        return await client.get_sustainability(symbol)
    
    # Index/ETF/Forex/Futures (all use same history method)
    elif tool_name in ["index_history", "etf_history", "forex_history", "futures_history"]:
        return await client.get_stock_history(symbol, period, interval)
    elif tool_name == "etf_info":
        return await client.get_stock_info(symbol)
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# =============================================================================
# MCP Server Setup
# =============================================================================

def create_mcp_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("yfinance-mcp")

    @server.list_tools()
    async def list_tools() -> ListToolsResult:
        return ListToolsResult(tools=TOOL_DEFINITIONS)

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
        logger.info(f"Calling tool: {name} with args: {arguments}")
        
        # Rate limiting
        rate_limiter = RateLimiter(_mcp_config.rate_limit_per_minute)
        await rate_limiter.acquire()
        
        # Check cache
        cache_key = f"{name}:{json.dumps(arguments, sort_keys=True)}"
        if _mcp_cache:
            cached = _mcp_cache.get(cache_key)
            if cached is not None:
                logger.info(f"Cache hit for {name}")
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(cached))]
                )
        
        try:
            result = await _execute_tool(_mcp_client, name, arguments)
            
            # Store in cache
            if _mcp_cache:
                ttl = _mcp_config.cache_ttl_by_type.get(
                    _get_data_type_for_tool(name),
                    _mcp_config.cache_ttl_default,
                )
                _mcp_cache.set(cache_key, result, ttl)
            
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result))]
            )
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({"error": str(e)}))]
            )

    return server


# =============================================================================
# Starlette App (HTTP + SSE)
# =============================================================================

def create_starlette_app() -> Starlette:
    """Create Starlette app with MCP SSE transport."""
    mcp_server = create_mcp_server()
    sse_transport = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server.run(
                streams[0], streams[1], mcp_server.create_initialization_options()
            )
        return Response()

    async def handle_health(request: Request):
        return JSONResponse({
            "status": "healthy",
            "service": "yfinance-mcp",
            "tools_count": len(TOOL_DEFINITIONS),
            "cache_enabled": _mcp_config.enable_caching,
        })

    async def handle_tools_list(request: Request):
        """REST endpoint for listing tools."""
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in TOOL_DEFINITIONS
        ]
        return JSONResponse({"tools": tools, "count": len(tools)})

    async def handle_call(request: Request):
        """REST API endpoint for calling MCP tools directly."""
        try:
            data = await request.json()
            tool_name = data.get("tool")
            arguments = data.get("arguments", {})
            
            if not tool_name:
                return JSONResponse({
                    "success": False,
                    "error": "Missing 'tool' parameter"
                }, status_code=400)
            
            logger.info(f"REST API calling tool: {tool_name} with args: {arguments}")
            
            # Rate limiting
            rate_limiter = RateLimiter(_mcp_config.rate_limit_per_minute)
            await rate_limiter.acquire()
            
            # Check cache
            cache_key = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
            if _mcp_cache:
                cached_result = _mcp_cache.get(cache_key)
                if cached_result is not None:
                    logger.info(f"REST API cache hit for {tool_name}")
                    return JSONResponse({
                        "success": True,
                        "result": cached_result,
                        "cached": True
                    })
            
            # Execute tool
            try:
                result = await _execute_tool(_mcp_client, tool_name, arguments)
                
                # Store in cache
                if _mcp_cache:
                    ttl = _mcp_config.cache_ttl_by_type.get(
                        _get_data_type_for_tool(tool_name),
                        _mcp_config.cache_ttl_default,
                    )
                    _mcp_cache.set(cache_key, result, ttl)
                
                return JSONResponse({
                    "success": True,
                    "result": result,
                    "cached": False
                })
                
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                return JSONResponse({
                    "success": False,
                    "error": str(e),
                    "tool": tool_name
                }, status_code=500)
                
        except Exception as e:
            logger.error(f"REST API error: {e}")
            return JSONResponse({
                "success": False,
                "error": str(e)
            }, status_code=500)

    routes = [
        Route("/health", handle_health, methods=["GET"]),
        Route("/tools", handle_tools_list, methods=["GET"]),
        Route("/call", handle_call, methods=["POST"]),
        Route("/sse", handle_sse, methods=["GET"]),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ]

    return Starlette(routes=routes)


# =============================================================================
# Entry Point
# =============================================================================

app = create_starlette_app()


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("YFINANCE_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("YFINANCE_MCP_PORT", "8010"))

    logger.info(f"Starting YFinance MCP Server on {host}:{port}")
    logger.info(f"SSE endpoint: http://{host}:{port}/sse")
    logger.info(f"Health check: http://{host}:{port}/health")
    logger.info(f"Tools list: http://{host}:{port}/tools")
    logger.info(f"Total tools: {len(TOOL_DEFINITIONS)}")

    uvicorn.run(app, host=host, port=port)
