"""
Akshare MCP Server - Standard MCP Server for China A-Share Market Data

This is a standard MCP (Model Context Protocol) server implementation using SSE transport.
It provides tools for accessing China A-share market data via Akshare library.

Supports:
- Stock price data (A-share, HK)
- Fundamental analysis (financial indicators, balance sheet, cash flow)
- Macro economic data (GDP, CPI, PMI, M2)
- Market news
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import akshare as ak
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
class AkshareConfig:
    """Akshare MCP server configuration."""
    enable_caching: bool = True
    cache_ttl_default: int = 300  # 5 minutes
    rate_limit_per_minute: int = 60
    
    cache_ttl_by_type: Dict[str, int] = field(default_factory=lambda: {
        "stock_price": 60,
        "fundamentals": 3600,
        "financial_statements": 86400,
        "macro_data": 86400,
        "news": 300,
        "hk_stock": 60,
    })


def get_config() -> AkshareConfig:
    """Load configuration from environment variables."""
    config = AkshareConfig()
    config.enable_caching = os.environ.get("AKSHARE_MCP_CACHE", "true").lower() == "true"
    config.rate_limit_per_minute = int(os.environ.get("AKSHARE_MCP_RATE_LIMIT", "60"))
    return config


# =============================================================================
# Utilities
# =============================================================================

def df_to_dict(df: pd.DataFrame, symbol: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convert DataFrame to dictionary payload."""
    if not df.empty:
        # Clean DataFrame: replace NaN, inf, -inf with None for JSON compatibility
        df_cleaned = df.copy()
        
        # Replace infinite values with None
        df_cleaned = df_cleaned.replace([float('inf'), float('-inf')], None)
        
        # Replace NaN with None (Pandas 2.0+ compatible)
        df_cleaned = df_cleaned.where(df_cleaned.notna(), None)
        
        # Convert to dict
        data = df_cleaned.to_dict("records")
    else:
        data = []
    
    result = {
        "data": data,
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
# Akshare Data Client
# =============================================================================

class AkshareClient:
    """Direct Akshare access with fallback to raw API."""

    async def get_stock_price(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq",
    ) -> Dict[str, Any]:
        """Get China A-share stock price data."""
        def _fetch():
            try:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date or "",
                    end_date=end_date or "",
                    adjust=adjust,
                )
                if not df.empty:
                    return df_to_dict(df, symbol=symbol)
            except Exception as e:
                logger.warning(f"Akshare fetch failed for {symbol}: {e}")

            # Fallback to direct eastmoney API
            import requests
            market = "1" if symbol.startswith("6") else "0"
            secid = f"{market}.{symbol}"
            klt_map = {"daily": "101", "weekly": "102", "monthly": "103"}
            klt = klt_map.get(period, "101")
            fqt_map = {"qfq": "1", "hfq": "2", "": "0", "none": "0"}
            fqt = fqt_map.get(adjust, "1")

            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": klt,
                "fqt": fqt,
                "beg": start_date.replace("-", "") if start_date else "0",
                "end": end_date.replace("-", "") if end_date else "20500101",
            }
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(url, params=params, headers=headers, timeout=15)
            data = r.json()

            if "data" not in data or not data["data"] or "klines" not in data["data"]:
                return df_to_dict(pd.DataFrame(), symbol=symbol)

            klines = data["data"]["klines"]
            records = []
            for line in klines:
                parts = line.split(",")
                if len(parts) >= 11:
                    records.append({
                        "日期": parts[0],
                        "开盘": float(parts[1]),
                        "收盘": float(parts[2]),
                        "最高": float(parts[3]),
                        "最低": float(parts[4]),
                        "成交量": int(parts[5]),
                        "成交额": float(parts[6]),
                        "振幅": float(parts[7]),
                        "涨跌幅": float(parts[8]),
                        "涨跌额": float(parts[9]),
                        "换手率": float(parts[10]),
                    })
            df = pd.DataFrame(records)
            return df_to_dict(df, symbol=symbol)

        return await asyncio.to_thread(_fetch)

    async def get_hk_stock_price(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get Hong Kong stock price data."""
        def _fetch():
            df = ak.stock_hk_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
            return df_to_dict(df, symbol=symbol)
        return await asyncio.to_thread(_fetch)

    async def get_fundamentals(
        self,
        symbol: str,
        report_type: str = "profit",
    ) -> Dict[str, Any]:
        """Get fundamental financial data."""
        def _fetch():
            if report_type == "profit":
                df = ak.stock_financial_analysis_indicator(symbol=symbol)
            elif report_type == "balance":
                df = ak.stock_balance_sheet_by_report_em(symbol=symbol)
            elif report_type == "cash":
                df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
            else:
                raise ValueError(f"Unknown report type: {report_type}")

            if not df.empty and "报告期" in df.columns:
                df_sorted = df.sort_values("报告期", ascending=False)
            else:
                df_sorted = df
            return df_to_dict(df_sorted.head(10), symbol=symbol, extra={"report_type": report_type})
        return await asyncio.to_thread(_fetch)

    async def get_income_statement(self, symbol: str) -> Dict[str, Any]:
        """Get income statement data."""
        def _fetch():
            df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
            if not df.empty and "报告期" in df.columns:
                df = df.sort_values("报告期", ascending=False)
            return df_to_dict(df.head(10), symbol=symbol, extra={"report_type": "income"})
        return await asyncio.to_thread(_fetch)

    async def get_balance_sheet(self, symbol: str) -> Dict[str, Any]:
        """Get balance sheet data."""
        def _fetch():
            df = ak.stock_balance_sheet_by_report_em(symbol=symbol)
            if not df.empty and "报告期" in df.columns:
                df = df.sort_values("报告期", ascending=False)
            return df_to_dict(df.head(10), symbol=symbol, extra={"report_type": "balance"})
        return await asyncio.to_thread(_fetch)

    async def get_cashflow(self, symbol: str) -> Dict[str, Any]:
        """Get cash flow statement data."""
        def _fetch():
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
            if not df.empty and "报告期" in df.columns:
                df = df.sort_values("报告期", ascending=False)
            return df_to_dict(df.head(10), symbol=symbol, extra={"report_type": "cashflow"})
        return await asyncio.to_thread(_fetch)

    async def get_macro(self, indicator: str) -> Dict[str, Any]:
        """Get macro economic data."""
        def _fetch():
            indicator_map = {
                "GDP": ak.macro_china_gdp,
                "CPI": ak.macro_china_cpi,
                "PMI": ak.macro_china_pmi,
                "M2": ak.macro_china_m2,
                "PPI": ak.macro_china_ppi,
            }
            func = indicator_map.get(indicator.upper())
            if func is None:
                func = getattr(ak, f"macro_china_{indicator.lower()}", None)
            if func is None or not callable(func):
                raise ValueError(f"Unknown macro indicator: {indicator}")
            df = func()
            return df_to_dict(df, extra={"indicator": indicator})
        return await asyncio.to_thread(_fetch)

    async def get_news(self, source: str = "sina", limit: int = 20) -> Dict[str, Any]:
        """Get market news."""
        def _fetch():
            source_map = {
                "sina": ak.stock_news_em,
                "eastmoney": ak.stock_info_global_em,
            }
            func = source_map.get(source, ak.stock_news_em)
            df = func()
            data = df.head(limit) if not df.empty else df
            return df_to_dict(data, extra={"source": source})
        return await asyncio.to_thread(_fetch)

    async def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """Get basic stock information."""
        def _fetch():
            df = ak.stock_individual_info_em(symbol=symbol)
            return df_to_dict(df, symbol=symbol)
        return await asyncio.to_thread(_fetch)


# =============================================================================
# MCP Server Definition
# =============================================================================

# =============================================================================
# Tool Definitions - 100 Core Financial Analysis Tools
# =============================================================================
# Categories:
# 1. Stock Price Data (A-Share, HK, US) - 10 tools
# 2. Financial Statements - 8 tools
# 3. Valuation & Metrics - 8 tools
# 4. Board/Sector/Concept - 12 tools
# 5. Trading Activity (龙虎榜, 大宗交易, 融资融券) - 10 tools
# 6. Shareholder & Institutional - 8 tools
# 7. Macro Economics - 15 tools
# 8. Index Data - 10 tools
# 9. Fund/ETF - 8 tools
# 10. Bond/Convertible - 6 tools
# 11. News & Research - 5 tools
# =============================================================================

def _symbol_schema(desc: str = "Stock code (e.g., '000001', '600519')"):
    return {"type": "string", "description": desc}

def _date_schema(desc: str = "Date in YYYY-MM-DD or YYYYMMDD format"):
    return {"type": "string", "description": desc}

def _limit_schema(default: int = 50):
    return {"type": "integer", "default": default, "description": "Maximum number of results"}

TOOL_DEFINITIONS: List[Tool] = [
    # =========================================================================
    # 1. Stock Price Data (A-Share, HK, US) - 10 tools
    # =========================================================================
    Tool(
        name="stock_zh_a_hist",
        description="获取A股历史行情数据(OHLCV)。支持日/周/月线，前复权/后复权。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": _symbol_schema("A股代码，如 '000001', '600519'"),
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
                "start_date": _date_schema("开始日期"),
                "end_date": _date_schema("结束日期"),
                "adjust": {"type": "string", "enum": ["qfq", "hfq", ""], "default": "qfq", "description": "复权类型"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_zh_a_spot_em",
        description="获取A股实时行情快照，包含最新价、涨跌幅、成交量等。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_zh_a_minute",
        description="获取A股分钟级行情数据。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": _symbol_schema(),
                "period": {"type": "string", "enum": ["1", "5", "15", "30", "60"], "default": "5", "description": "分钟周期"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_hk_hist",
        description="获取港股历史行情数据(OHLCV)。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": _symbol_schema("港股代码，如 '00700', '09988'"),
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
                "start_date": _date_schema(),
                "end_date": _date_schema(),
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_hk_spot_em",
        description="获取港股实时行情快照。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_us_hist",
        description="获取美股历史行情数据。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": _symbol_schema("美股代码，如 'AAPL', 'MSFT'"),
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
                "start_date": _date_schema(),
                "end_date": _date_schema(),
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_us_spot_em",
        description="获取美股实时行情快照。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_individual_info_em",
        description="获取个股基本信息（公司名称、行业、市值、PE、PB等）。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_zh_a_hist_pre_min_em",
        description="获取A股盘前分时数据。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_bid_ask_em",
        description="获取A股买卖盘口数据（五档/十档）。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    
    # =========================================================================
    # 2. Financial Statements - 8 tools
    # =========================================================================
    Tool(
        name="stock_profit_sheet_by_report_em",
        description="获取利润表数据（按报告期）。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_balance_sheet_by_report_em",
        description="获取资产负债表数据（按报告期）。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_cash_flow_sheet_by_report_em",
        description="获取现金流量表数据（按报告期）。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_financial_analysis_indicator",
        description="获取财务分析指标（ROE、毛利率、净利率等）。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_yjbb_em",
        description="获取业绩报表（营收、净利润、同比增长等）。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("报告期，如 '20231231'")},
            "required": ["date"],
        },
    ),
    Tool(
        name="stock_yjyg_em",
        description="获取业绩预告数据。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("报告期")},
            "required": ["date"],
        },
    ),
    Tool(
        name="stock_yjkb_em",
        description="获取业绩快报数据。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("报告期")},
            "required": ["date"],
        },
    ),
    Tool(
        name="stock_fhps_em",
        description="获取分红配送数据。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("年份，如 '2023'")},
            "required": ["date"],
        },
    ),
    
    # =========================================================================
    # 3. Valuation & Metrics - 8 tools
    # =========================================================================
    Tool(
        name="stock_a_ttm_lyr",
        description="获取A股PE/PB估值数据（TTM和静态）。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_a_all_pb",
        description="获取全A股市净率(PB)数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_a_high_low_statistics",
        description="获取A股创新高/新低统计。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "enum": ["all", "创月新高", "创月新低", "创年新高", "创年新低"]}},
        },
    ),
    Tool(
        name="stock_a_below_net_asset_statistics",
        description="获取破净股统计数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_zh_a_gdhs",
        description="获取A股股东户数数据。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_comment_em",
        description="获取千股千评数据（综合评分、技术面、资金面）。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_rank_cxg_ths",
        description="获取同花顺创新高排行。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_rank_cxd_ths",
        description="获取同花顺创新低排行。",
        inputSchema={"type": "object", "properties": {}},
    ),
    
    # =========================================================================
    # 4. Board/Sector/Concept - 12 tools
    # =========================================================================
    Tool(
        name="stock_board_industry_name_em",
        description="获取东方财富行业板块列表。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_board_industry_spot_em",
        description="获取行业板块实时行情。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_board_industry_cons_em",
        description="获取行业板块成分股。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "行业板块名称，如 '银行'"}},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_board_industry_hist_em",
        description="获取行业板块历史行情。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "行业板块名称"},
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_board_concept_name_em",
        description="获取东方财富概念板块列表。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_board_concept_spot_em",
        description="获取概念板块实时行情。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_board_concept_cons_em",
        description="获取概念板块成分股。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "概念板块名称，如 '人工智能'"}},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_board_concept_hist_em",
        description="获取概念板块历史行情。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "概念板块名称"},
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_sector_fund_flow_rank",
        description="获取板块资金流向排行。",
        inputSchema={
            "type": "object",
            "properties": {"indicator": {"type": "string", "enum": ["今日", "5日", "10日"], "default": "今日"}},
        },
    ),
    Tool(
        name="stock_individual_fund_flow",
        description="获取个股资金流向。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_individual_fund_flow_rank",
        description="获取个股资金流向排行。",
        inputSchema={
            "type": "object",
            "properties": {"indicator": {"type": "string", "enum": ["今日", "3日", "5日", "10日"], "default": "今日"}},
        },
    ),
    Tool(
        name="stock_market_fund_flow",
        description="获取大盘资金流向（沪深两市）。",
        inputSchema={"type": "object", "properties": {}},
    ),
    
    # =========================================================================
    # 5. Trading Activity (龙虎榜, 大宗交易, 融资融券) - 10 tools
    # =========================================================================
    Tool(
        name="stock_lhb_detail_em",
        description="获取龙虎榜详情数据。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": _symbol_schema(),
                "date": _date_schema("交易日期"),
            },
        },
    ),
    Tool(
        name="stock_lhb_stock_statistic_em",
        description="获取龙虎榜个股统计。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "enum": ["近一月", "近三月", "近六月", "近一年"], "default": "近一月"}},
        },
    ),
    Tool(
        name="stock_lhb_jgmmtj_em",
        description="获取龙虎榜机构买卖统计。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "enum": ["近一月", "近三月", "近六月", "近一年"], "default": "近一月"}},
        },
    ),
    Tool(
        name="stock_dzjy_mrmx",
        description="获取大宗交易每日明细。",
        inputSchema={
            "type": "object",
            "properties": {
                "start_date": _date_schema(),
                "end_date": _date_schema(),
            },
        },
    ),
    Tool(
        name="stock_dzjy_mrtj",
        description="获取大宗交易每日统计。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("交易日期")},
            "required": ["date"],
        },
    ),
    Tool(
        name="stock_margin_detail_szse",
        description="获取深市融资融券明细。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("交易日期")},
            "required": ["date"],
        },
    ),
    Tool(
        name="stock_margin_detail_sse",
        description="获取沪市融资融券明细。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("交易日期")},
            "required": ["date"],
        },
    ),
    Tool(
        name="stock_zt_pool_em",
        description="获取涨停板股票池。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("交易日期")},
            "required": ["date"],
        },
    ),
    Tool(
        name="stock_dt_pool_em",
        description="获取跌停板股票池。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("交易日期")},
            "required": ["date"],
        },
    ),
    Tool(
        name="stock_zt_pool_strong_em",
        description="获取强势封板股票池。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("交易日期")},
            "required": ["date"],
        },
    ),
    
    # =========================================================================
    # 6. Shareholder & Institutional - 8 tools
    # =========================================================================
    Tool(
        name="stock_circulate_stock_holder",
        description="获取流通股东数据。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_main_stock_holder",
        description="获取十大股东数据。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_fund_stock_holder",
        description="获取基金持股数据。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("季度末，如 '20231231'")},
            "required": ["date"],
        },
    ),
    Tool(
        name="stock_hsgt_north_net_flow_in",
        description="获取北向资金净流入数据。",
        inputSchema={
            "type": "object",
            "properties": {"indicator": {"type": "string", "enum": ["沪股通", "深股通", "北向"], "default": "北向"}},
        },
    ),
    Tool(
        name="stock_hsgt_north_acc_flow_in",
        description="获取北向资金累计净流入。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_hsgt_hold_stock_em",
        description="获取沪深港通持股数据。",
        inputSchema={
            "type": "object",
            "properties": {"indicator": {"type": "string", "enum": ["沪股通", "深股通"], "default": "沪股通"}},
        },
    ),
    Tool(
        name="stock_gpzy_pledge_ratio_em",
        description="获取股票质押比例。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_repurchase_em",
        description="获取股票回购数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    
    # =========================================================================
    # 7. Macro Economics - 15 tools
    # =========================================================================
    Tool(
        name="macro_china_gdp",
        description="获取中国GDP数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_cpi",
        description="获取中国CPI消费者物价指数。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_ppi",
        description="获取中国PPI生产者物价指数。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_pmi",
        description="获取中国PMI采购经理指数。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_m2",
        description="获取中国M2货币供应量。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_fx_reserves",
        description="获取中国外汇储备数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_consumer_goods_retail",
        description="获取中国社会消费品零售总额。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_lpr",
        description="获取中国贷款市场报价利率(LPR)。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_new_financial_credit",
        description="获取中国新增信贷数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_shibor_all",
        description="获取上海银行间同业拆放利率(SHIBOR)。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_hk_market",
        description="获取中国香港市场相关数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_real_estate",
        description="获取中国房地产投资开发数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_fdi",
        description="获取中国外商直接投资(FDI)。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_wbck",
        description="获取中国外贸进出口数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="macro_china_stock_market_cap",
        description="获取中国股市总市值数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    
    # =========================================================================
    # 8. Index Data - 10 tools
    # =========================================================================
    Tool(
        name="index_zh_a_hist",
        description="获取A股指数历史行情（上证指数、深证成指等）。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "指数代码，如 '000001'(上证), '399001'(深证)"},
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
                "start_date": _date_schema(),
                "end_date": _date_schema(),
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="index_stock_cons",
        description="获取指数成分股。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "指数代码"}},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="index_stock_cons_weight_csindex",
        description="获取中证指数成分股权重。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "中证指数代码，如 '000300'"}},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_szse_summary",
        description="获取深交所市场总貌。",
        inputSchema={
            "type": "object",
            "properties": {"date": _date_schema("交易日期")},
        },
    ),
    Tool(
        name="stock_sse_summary",
        description="获取上交所市场总貌。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="index_value_name_funddb",
        description="获取主要指数估值数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="index_fear_greed_funddb",
        description="获取A股恐惧贪婪指数。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_market_activity_legu",
        description="获取A股市场活跃度。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="index_investing_global",
        description="获取全球主要指数行情。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_zh_index_spot_em",
        description="获取A股指数实时行情。",
        inputSchema={"type": "object", "properties": {}},
    ),
    
    # =========================================================================
    # 9. Fund/ETF - 8 tools
    # =========================================================================
    Tool(
        name="fund_etf_hist_em",
        description="获取ETF历史行情。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "ETF代码，如 '510300'"},
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
                "start_date": _date_schema(),
                "end_date": _date_schema(),
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="fund_etf_spot_em",
        description="获取ETF实时行情。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="fund_etf_fund_info_em",
        description="获取ETF基金信息。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "ETF代码"}},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="fund_open_fund_rank_em",
        description="获取开放式基金排行。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "enum": ["全部", "股票型", "混合型", "债券型", "指数型", "QDII"], "default": "全部"}},
        },
    ),
    Tool(
        name="fund_info_index_em",
        description="获取指数基金信息。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "基金代码"}},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="fund_portfolio_hold_em",
        description="获取基金持仓数据。",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "基金代码"},
                "date": _date_schema("季度末日期"),
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="fund_financial_fund_daily_em",
        description="获取货币基金收益数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="fund_scale_change_em",
        description="获取基金规模变动统计。",
        inputSchema={"type": "object", "properties": {}},
    ),
    
    # =========================================================================
    # 10. Bond/Convertible - 6 tools
    # =========================================================================
    Tool(
        name="bond_cb_jsl",
        description="获取可转债列表及数据（集思录）。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="bond_cb_index_jsl",
        description="获取可转债等权指数。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="bond_cb_redeem_jsl",
        description="获取可转债强赎数据。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="bond_zh_hs_cov_spot",
        description="获取沪深可转债实时行情。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="bond_zh_cov_info",
        description="获取可转债详情信息。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "转债代码"}},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="bond_china_yield",
        description="获取中国国债收益率曲线。",
        inputSchema={
            "type": "object",
            "properties": {"start_date": _date_schema(), "end_date": _date_schema()},
        },
    ),
    
    # =========================================================================
    # 11. News & Research - 5 tools
    # =========================================================================
    Tool(
        name="stock_news_em",
        description="获取东方财富股票新闻。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_info_global_em",
        description="获取全球财经快讯。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_research_report_em",
        description="获取个股研报数据。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
    Tool(
        name="stock_analyst_rank_em",
        description="获取分析师排名。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="stock_jgdy_detail_em",
        description="获取机构调研详情。",
        inputSchema={
            "type": "object",
            "properties": {"symbol": _symbol_schema()},
            "required": ["symbol"],
        },
    ),
]


def create_mcp_server() -> Server:
    """Create and configure the MCP server instance."""
    server = Server("akshare-mcp")
    config = get_config()
    client = AkshareClient()
    cache = DataCache() if config.enable_caching else None
    rate_limiter = RateLimiter(config.rate_limit_per_minute)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Return the list of available tools."""
        return TOOL_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Execute a tool and return the result."""
        logger.info(f"Calling tool: {name} with arguments: {arguments}")

        # Rate limiting
        await rate_limiter.acquire()

        # Check cache
        if cache:
            cache_key = f"{name}:{json.dumps(arguments, sort_keys=True)}"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit for {name}")
                return [TextContent(type="text", text=json.dumps(cached_result, ensure_ascii=False, default=str))]

        try:
            result = await _execute_tool(client, name, arguments)

            # Store in cache
            if cache:
                ttl = config.cache_ttl_by_type.get(
                    _get_data_type_for_tool(name),
                    config.cache_ttl_default,
                )
                cache.set(cache_key, result, ttl)

            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            error_result = {"error": str(e), "tool": name, "arguments": arguments}
            return [TextContent(type="text", text=json.dumps(error_result, ensure_ascii=False))]

    return server


def _get_data_type_for_tool(tool_name: str) -> str:
    """Map tool name to data type for cache TTL lookup."""
    name_lower = tool_name.lower()
    
    if any(x in name_lower for x in ["spot", "minute", "bid_ask"]):
        return "stock_price"  # 60s cache
    if any(x in name_lower for x in ["hist", "price"]):
        return "stock_price"  # 60s cache
    if any(x in name_lower for x in ["profit", "balance", "cash_flow", "financial", "yjbb", "yjyg", "yjkb", "fhps"]):
        return "financial_statements"  # 24h cache
    if any(x in name_lower for x in ["macro", "gdp", "cpi", "ppi", "pmi", "m2", "lpr", "shibor"]):
        return "macro_data"  # 24h cache
    if any(x in name_lower for x in ["news", "info_global"]):
        return "news"  # 5min cache
    if any(x in name_lower for x in ["board", "sector", "concept", "industry"]):
        return "fundamentals"  # 1h cache
    if any(x in name_lower for x in ["fund", "etf", "bond"]):
        return "fundamentals"  # 1h cache
    if any(x in name_lower for x in ["index", "value", "fear"]):
        return "fundamentals"  # 1h cache
    
    return "stock_price"


async def _execute_tool(client: AkshareClient, name: str, arguments: dict) -> Dict[str, Any]:
    """
    Execute the specified tool by dynamically calling the corresponding akshare function.
    
    This is a generic dispatcher that maps tool names directly to akshare functions.
    """
    def _fetch():
        # Get the akshare function by name
        ak_func = getattr(ak, name, None)
        if ak_func is None:
            raise ValueError(f"Unknown akshare function: {name}")
        
        # Build kwargs from arguments, filtering out None values
        kwargs = {k: v for k, v in arguments.items() if v is not None}
        
        # Call the function
        try:
            result = ak_func(**kwargs)
        except TypeError as e:
            # If there's a type error, try without arguments for no-arg functions
            if not kwargs:
                raise
            # Try to call with just the required args
            logger.warning(f"TypeError calling {name} with {kwargs}: {e}")
            result = ak_func(**{k: v for k, v in kwargs.items() if k in ["symbol", "indicator", "date"]})
        
        # Convert result to dict
        if isinstance(result, pd.DataFrame):
            return df_to_dict(result, symbol=arguments.get("symbol"), extra={"tool": name})
        elif isinstance(result, (list, dict)):
            return {"data": result, "tool": name}
        else:
            return {"data": str(result), "tool": name}
    
    return await asyncio.to_thread(_fetch)


# =============================================================================
# Starlette Application with SSE Transport
# =============================================================================

# 全局变量存储 MCP 服务器实例（供 REST API 使用）
_mcp_server_instance: Optional[Server] = None
_mcp_config: Optional[AkshareConfig] = None
_mcp_client: Optional[AkshareClient] = None
_mcp_cache: Optional[DataCache] = None


def create_starlette_app() -> Starlette:
    """Create Starlette application with SSE endpoint for MCP."""
    global _mcp_server_instance, _mcp_config, _mcp_client, _mcp_cache
    
    _mcp_server_instance = create_mcp_server()
    _mcp_config = get_config()
    _mcp_client = AkshareClient()
    _mcp_cache = DataCache() if _mcp_config.enable_caching else None
    
    sse_transport = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        """Handle SSE connections for MCP protocol."""
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as streams:
            await _mcp_server_instance.run(
                streams[0],
                streams[1],
                _mcp_server_instance.create_initialization_options(),
            )
        return Response()

    async def handle_health(request: Request):
        """Health check endpoint."""
        return JSONResponse({
            "status": "ok",
            "server": "akshare-mcp",
            "version": "1.0.0",
            "transport": "sse",
            "tools_count": len(TOOL_DEFINITIONS),
        })

    async def handle_tools_list(request: Request):
        """REST endpoint for listing tools (for debugging/discovery)."""
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
        """
        REST API 端点：直接调用 MCP 工具
        
        请求格式：
        POST /call
        Content-Type: application/json
        
        {
            "tool": "stock_zh_index_spot_em",
            "arguments": {}
        }
        
        响应格式：
        {
            "success": true,
            "result": {...}
        }
        """
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
            
            # 调用工具（复用 MCP 服务器的逻辑）
            from mcp.types import TextContent
            
            # 速率限制
            rate_limiter = RateLimiter(_mcp_config.rate_limit_per_minute)
            await rate_limiter.acquire()
            
            # 检查缓存
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
            
            # 执行工具调用
            try:
                result = await _execute_tool(_mcp_client, tool_name, arguments)
                
                # 存储到缓存
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

    host = os.environ.get("AKSHARE_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("AKSHARE_MCP_PORT", "8009"))

    logger.info(f"Starting Akshare MCP Server on {host}:{port}")
    logger.info(f"SSE endpoint: http://{host}:{port}/sse")
    logger.info(f"Health check: http://{host}:{port}/health")
    logger.info(f"Tools list: http://{host}:{port}/tools")

    uvicorn.run(app, host=host, port=port)
