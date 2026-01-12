from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ChartDataRequest(BaseModel):
    ticker: str
    resolution: str = Field(default="1d", description="时间分辨率: 1m, 5m, 15m, 1h, 1d")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: Optional[int] = Field(default=100, description="返回数据点数量")

class OHLCVData(BaseModel):
    """OHLCV数据点"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None

class ChartDataResponse(BaseModel):
    """图表数据响应"""
    ticker: str
    resolution: str
    data: List[OHLCVData]
    data_source: str = "mcp"
    cached: bool = False
    last_updated: datetime

class SparklineResponse(BaseModel):
    """简略行情数据响应（用于前端组件展示）"""
    ticker: str
    period: str = ""
    current_price: float = 0.0  # 历史数据的最后收盘价（非实时价格）
    change_percent: float = 0.0
    sparkline_data: List[float] = Field(default_factory=list, description="简化的价格数据点")
    last_updated: Optional[datetime] = None
    # Frontend compatibility fields
    data: List[float] = Field(default_factory=list, description="Alias for sparkline_data")
    timestamps: List[str] = Field(default_factory=list, description="Timestamp labels")
    high: float = 0.0
    low: float = 0.0
    cached: bool = False
    # 明确标识收盘价日期，帮助前端区分实时价格和历史收盘价
    last_close_date: Optional[str] = Field(default=None, description="最后收盘价的日期 (YYYY-MM-DD)")
