from typing import List, Optional
from pydantic import BaseModel

class CockpitAssetPrice(BaseModel):
    """Cockpit 资产价格"""
    ticker: str
    name: Optional[str] = None
    asset_type: Optional[str] = None  # 'US' | 'HK' | 'CRYPTO' | 'MACRO'
    exchange: Optional[str] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    target_price: Optional[float] = None
    price: Optional[float] = None
    price_local: Optional[float] = None
    currency_local: Optional[str] = None
    change_percent: Optional[float] = None
    change_value: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[int] = None
    is_market_open: Optional[bool] = None
    source: str  # "cache", "database", "pending"
    last_updated: Optional[str] = None


class CockpitMarketIndex(BaseModel):
    """Cockpit 市场指数"""
    id: str
    name: str
    value: str
    change: str
    change_percent: float
    trend: str  # "up" | "down"
    critical: bool = False
    type: str  # "index", "commodity", "crypto", "macro"


class CockpitDashboardResponse(BaseModel):
    """Cockpit 仪表盘聚合响应"""
    # 市场指数
    markets: List[CockpitMarketIndex]
    
    # 用户资产价格
    assets: List[CockpitAssetPrice]
    
    # 时间戳
    last_updated: str
    cache_expired: bool


class UserCockpitIndicatorResponse(BaseModel):
    """用户指标响应"""
    id: int
    indicator_id: str
    display_order: int
    is_active: bool


class UserCockpitIndicatorCreate(BaseModel):
    """创建用户指标请求"""
    indicator_id: str
    display_order: Optional[int] = 0


class UserCockpitIndicatorReorder(BaseModel):
    """重排用户指标请求"""
    indicator_ids: List[int]
