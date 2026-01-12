"""
Market Schemas - 市场数据相关模型

定义 Asset、Quote、Price 等市场数据相关的 Pydantic 模型。
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from AICrews.schemas.common import BaseSchema
from AICrews.schemas.portfolio import AssetSearchRequest, AssetSearchResult


class AssetCreate(BaseSchema):
    """资产创建请求"""
    ticker: str = Field(..., min_length=1, max_length=20, description="资产代码")
    name: Optional[str] = Field(None, max_length=200, description="资产名称")
    asset_type: str = Field(..., description="资产类型: US, HK, CRYPTO, MACRO")
    exchange: Optional[str] = Field(None, max_length=50, description="交易所")
    currency: str = Field("USD", description="货币")
    sector: Optional[str] = Field(None, max_length=100, description="行业")
    industry: Optional[str] = Field(None, max_length=100, description="子行业")
    description: Optional[str] = Field(None, description="描述")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "asset_type": "US",
                "exchange": "NASDAQ",
                "currency": "USD",
                "sector": "Technology",
                "industry": "Consumer Electronics"
            }
        }
    )


class AssetUpdate(BaseSchema):
    """资产更新请求"""
    name: Optional[str] = Field(None, max_length=200, description="资产名称")
    asset_type: Optional[str] = Field(None, description="资产类型")
    exchange: Optional[str] = Field(None, max_length=50, description="交易所")
    currency: Optional[str] = Field(None, description="货币")
    sector: Optional[str] = Field(None, max_length=100, description="行业")
    industry: Optional[str] = Field(None, max_length=100, description="子行业")
    description: Optional[str] = Field(None, description="描述")
    is_active: Optional[bool] = Field(None, description="是否启用")


class AssetResponse(BaseSchema):
    """资产响应"""
    ticker: str = Field(..., description="资产代码")
    name: Optional[str] = Field(None, description="资产名称")
    asset_type: str = Field(..., description="资产类型")
    exchange: Optional[str] = Field(None, description="交易所")
    currency: str = Field(..., description="货币")
    sector: Optional[str] = Field(None, description="行业")
    industry: Optional[str] = Field(None, description="子行业")
    description: Optional[str] = Field(None, description="描述")
    is_active: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 关联的实时行情
    realtime_quote: Optional["RealtimeQuoteResponse"] = Field(None, description="实时行情")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "asset_type": "US",
                "exchange": "NASDAQ",
                "currency": "USD",
                "sector": "Technology",
                "is_active": True,
                "created_at": "2025-12-26T00:00:00Z",
                "updated_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class RealtimeQuoteUpdate(BaseSchema):
    """实时行情更新请求"""
    price: Optional[float] = Field(None, description="价格（美元）")
    price_local: Optional[float] = Field(None, description="本地货币价格")
    currency_local: Optional[str] = Field(None, description="本地货币代码")
    change_value: Optional[float] = Field(None, description="绝对变化")
    change_percent: Optional[float] = Field(None, description="百分比变化")
    volume: Optional[int] = Field(None, description="成交量")
    market_cap: Optional[int] = Field(None, description="市值")
    open_price: Optional[float] = Field(None, description="开盘价")
    high_price: Optional[float] = Field(None, description="最高价")
    low_price: Optional[float] = Field(None, description="最低价")
    prev_close: Optional[float] = Field(None, description="昨收价")
    trade_time: Optional[datetime] = Field(None, description="交易时间")
    data_source: Optional[str] = Field(None, description="数据来源")
    fetch_error: Optional[str] = Field(None, description="获取错误")
    is_market_open: Optional[bool] = Field(None, description="市场是否开放")


class RealtimeQuoteResponse(BaseSchema):
    """实时行情响应"""
    ticker: str = Field(..., description="资产代码")
    price: Optional[float] = Field(None, description="价格（美元）")
    price_local: Optional[float] = Field(None, description="本地货币价格")
    currency_local: Optional[str] = Field(None, description="本地货币代码")
    change_value: Optional[float] = Field(None, description="绝对变化")
    change_percent: Optional[float] = Field(None, description="百分比变化")
    volume: Optional[int] = Field(None, description="成交量")
    market_cap: Optional[int] = Field(None, description="市值")
    open_price: Optional[float] = Field(None, description="开盘价")
    high_price: Optional[float] = Field(None, description="最高价")
    low_price: Optional[float] = Field(None, description="最低价")
    prev_close: Optional[float] = Field(None, description="昨收价")
    trade_time: Optional[datetime] = Field(None, description="交易时间")
    last_updated: datetime = Field(..., description="最后更新时间")
    data_source: str = Field(..., description="数据来源")
    fetch_error: Optional[str] = Field(None, description="获取错误")
    is_market_open: Optional[bool] = Field(None, description="市场是否开放")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "price": 185.0,
                "price_local": 185.0,
                "currency_local": "USD",
                "change_value": 2.5,
                "change_percent": 1.37,
                "volume": 50000000,
                "market_cap": 2900000000000,
                "open_price": 183.5,
                "high_price": 185.5,
                "low_price": 183.0,
                "prev_close": 182.5,
                "data_source": "mcp",
                "last_updated": "2025-12-26T00:00:00Z"
            }
        }
    )


class StockPriceResponse(BaseSchema):
    """K线数据响应"""
    id: int = Field(..., description="记录 ID")
    ticker: str = Field(..., description="资产代码")
    date: datetime = Field(..., description="日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")
    resolution: str = Field(..., description="周期: 1d, 1h, 5m")
    source: str = Field(..., description="数据来源")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ticker": "AAPL",
                "date": "2025-12-26T00:00:00Z",
                "open": 183.5,
                "high": 185.5,
                "low": 183.0,
                "close": 185.0,
                "volume": 50000000.0,
                "resolution": "1d",
                "source": "mcp",
                "created_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class MarketNewsResponse(BaseSchema):
    """市场新闻响应"""
    id: int = Field(..., description="新闻 ID")
    ticker: Optional[str] = Field(None, description="资产代码")
    published_at: datetime = Field(..., description="发布时间")
    title: str = Field(..., description="标题")
    url: str = Field(..., description="链接")
    source: str = Field(..., description="来源")
    content: Optional[str] = Field(None, description="内容")
    summary: Optional[str] = Field(None, description="摘要")
    sentiment_score: Optional[float] = Field(None, description="情感分数")
    author: Optional[str] = Field(None, description="作者")
    image_url: Optional[str] = Field(None, description="图片链接")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ticker": "AAPL",
                "published_at": "2025-12-26T00:00:00Z",
                "title": "Apple Announces New iPhone",
                "url": "https://example.com/news/1",
                "source": "TechNews",
                "content": "Apple announced...",
                "summary": "Apple announced new iPhone...",
                "sentiment_score": 0.8,
                "created_at": "2025-12-26T00:00:00Z"
            }
        }
    )


class FundamentalDataResponse(BaseSchema):
    """基本面数据响应"""
    id: int = Field(..., description="记录 ID")
    ticker: str = Field(..., description="资产代码")
    data_date: datetime = Field(..., description="数据日期")
    
    # 基础信息
    company_name: Optional[str] = Field(None, description="公司名称")
    sector: Optional[str] = Field(None, description="行业")
    industry: Optional[str] = Field(None, description="子行业")
    country: Optional[str] = Field(None, description="国家")
    exchange: Optional[str] = Field(None, description="交易所")
    
    # 关键指标
    market_cap: Optional[float] = Field(None, description="市值")
    pe_ratio: Optional[float] = Field(None, description="市盈率")
    forward_pe: Optional[float] = Field(None, description="远期市盈率")
    pb_ratio: Optional[float] = Field(None, description="市净率")
    dividend_yield: Optional[float] = Field(None, description="股息率")
    beta: Optional[float] = Field(None, description="Beta")
    
    # 财务健康
    current_ratio: Optional[float] = Field(None, description="流动比率")
    debt_to_equity: Optional[float] = Field(None, description="债务股本比")
    return_on_equity: Optional[float] = Field(None, description="净资产收益率")
    profit_margins: Optional[float] = Field(None, description="利润率")
    
    week_52_high: Optional[float] = Field(None, description="52周最高")
    week_52_low: Optional[float] = Field(None, description="52周最低")
    
    source: str = Field(..., description="数据来源")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ticker": "AAPL",
                "data_date": "2025-12-26T00:00:00Z",
                "company_name": "Apple Inc.",
                "sector": "Technology",
                "market_cap": 2900000000000.0,
                "pe_ratio": 30.5,
                "forward_pe": 28.5,
                "pb_ratio": 45.2,
                "dividend_yield": 0.5,
                "beta": 1.2,
                "source": "mcp",
                "created_at": "2025-12-26T00:00:00Z"
            }
        }
    )


__all__ = [
    "AssetCreate",
    "AssetUpdate",
    "AssetResponse",
    "RealtimeQuoteResponse",
    "StockPriceResponse",
    "MarketNewsResponse",
    "FundamentalDataResponse",
    "MarketIndex",
    "MarketDataResponse",
    "CockpitMacroIndicator",
    "CockpitMacroResponse",
    "AvailableIndicatorResponse",
    "AssetSearchRequest",
    "AssetSearchResult",
]


class MarketIndex(BaseModel):
    """市场指数数据"""
    code: str
    name: str
    symbol: str
    country: str
    description: str
    color: str
    price: float
    change: float
    change_percent: float
    volume: Optional[float] = None
    timestamp: str
    is_up: bool


class MarketDataResponse(BaseModel):
    """全球市场数据响应"""
    markets: List[MarketIndex]
    last_updated: str
    next_update_in_seconds: int = 300  # 5 minutes


class CockpitMacroIndicator(BaseModel):
    """Cockpit 宏观指标"""
    id: str
    name: str
    value: str
    change: str
    change_percent: float
    trend: str  # 'up' | 'down'
    critical: bool = False
    symbol: str
    type: str


class CockpitMacroResponse(BaseModel):
    """Cockpit 宏观数据响应"""
    indicators: List[CockpitMacroIndicator]
    last_updated: str
    next_update_in_seconds: int = 300


class AvailableIndicatorResponse(BaseModel):
    """可用指标响应（用于 GlobalContextCustomizer）"""
    indicator_id: str
    indicator_name: str
    symbol: str
    indicator_type: str
    is_critical: bool = False
    current_value: Optional[str] = None
    change_percent: Optional[float] = None
    trend: Optional[str] = None
    is_selected: bool = False
    last_updated: Optional[str] = None

