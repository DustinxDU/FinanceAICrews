from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class LibraryInsight(BaseModel):
    """简化的分析洞察响应（用于列表展示）"""
    id: int
    ticker: str
    asset_name: Optional[str]
    asset_type: Optional[str]
    source_type: str
    source_id: Optional[str]
    crew_name: Optional[str]
    title: str
    summary: Optional[str]
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    signal: Optional[str]
    key_metrics: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    is_favorite: bool
    is_read: bool
    analysis_date: Optional[datetime]
    created_at: datetime
    attachments_count: int = 0
    
    class Config:
        from_attributes = True

class InsightResponse(BaseModel):
    """分析记录响应"""
    id: int
    ticker: str
    asset_name: Optional[str]
    asset_type: Optional[str]
    source_type: str
    source_id: Optional[str]
    crew_name: Optional[str]
    title: str
    summary: Optional[str]
    content: Optional[str]
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    confidence: Optional[float]
    key_metrics: Optional[Dict[str, Any]]
    signal: Optional[str]
    target_price: Optional[float]
    stop_loss: Optional[float]
    raw_data: Optional[Dict[str, Any]]  # 原始数据（news_highlights, price_info 等）
    tags: Optional[List[str]]
    is_favorite: bool
    is_read: bool
    analysis_date: Optional[datetime]
    created_at: datetime
    attachments_count: int = 0

    class Config:
        from_attributes = True

class AssetGroupResponse(BaseModel):
    """资产分组响应"""
    ticker: str
    asset_name: Optional[str]
    asset_type: Optional[str]
    insights_count: int
    last_analysis_at: Optional[datetime]
    latest_sentiment: Optional[str]
    latest_signal: Optional[str]
    insights: List[InsightResponse]

class TimelineEntryResponse(BaseModel):
    """时间轴条目响应"""
    date: str
    insights_count: int
    sources: List[str]
    tickers: List[str]

class InsightDetailResponse(BaseModel):
    """分析详情响应"""
    insight: InsightResponse
    attachments: List[Dict[str, Any]]
    traces: List[Dict[str, Any]]
