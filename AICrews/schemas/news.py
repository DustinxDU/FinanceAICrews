from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class NewsSource(str, Enum):
    """News source identifiers (legacy compatibility)."""
    YAHOO_RSS = "yahoo_rss"
    SINA_RSS = "sina_rss"
    COINTELEGRAPH_RSS = "cointelegraph_rss"
    CNBC_RSS = "cnbc_rss"
    REUTERS_RSS = "reuters_rss"
    INVESTING_RSS = "investing_rss"
    # Legacy aliases for backward compatibility
    YFINANCE = "yahoo_rss"
    AKSHARE = "sina_rss"
    RSS_INVESTING = "investing_rss"
    RSS_REUTERS = "reuters_rss"
    RSS_COINDESK = "cointelegraph_rss"

class Sentiment(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class NewsItemResponse(BaseModel):
    """新闻项响应"""
    id: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    tickers: List[str]
    sentiment: str
    news_type: str

class NewsListResponse(BaseModel):
    """新闻列表响应"""
    news: List[NewsItemResponse]
    total_count: int
    cached: bool
    last_updated: str
    next_update_in_seconds: int = 300

class NewsSourcesResponse(BaseModel):
    """可用新闻源状态"""
    sources: Dict[str, Dict[str, Any]]

class NewsFilterRequest(BaseModel):
    """新闻过滤请求"""
    tickers: Optional[List[str]] = Field(None, max_length=10)
    news_types: Optional[List[str]] = Field(None, max_length=4)
    sources: Optional[List[str]] = Field(None, max_length=3)
    limit: int = Field(50, ge=1, le=200)
    force_refresh: bool = False

class ArticleExtractResponse(BaseModel):
    """文章正文提取响应"""
    success: bool
    title: Optional[str] = None
    text: Optional[str] = None
    top_image: Optional[str] = None
    authors: List[str] = []
    url: str
    error: Optional[str] = None
    is_blacklisted: bool = False
