from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QuickScanRequest(BaseModel):
    ticker: str
    thesis: Optional[str] = None  # 用户的投资论点，作为上下文

class QuickScanResponse(BaseModel):
    ticker: str
    summary: str  # 3点总结
    sentiment: str  # bullish, bearish, neutral
    news_highlights: List[str]  # 新闻要点
    price_info: Dict[str, Any]  # 价格信息
    execution_time_ms: int

class ChartAnalysisRequest(BaseModel):
    ticker: str
    thesis: Optional[str] = None

class ChartAnalysisResponse(BaseModel):
    ticker: str
    technical_summary: str  # 技术面总结
    indicators: Dict[str, Any]  # 技术指标
    support_resistance: Dict[str, Any]  # 支撑阻力位
    trend_assessment: str  # 趋势判断
    execution_time_ms: int
