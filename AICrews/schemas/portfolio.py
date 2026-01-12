from typing import Optional, List, Dict
from datetime import datetime
from pydantic import Field
from AICrews.schemas.common import BaseSchema

class AddAssetRequest(BaseSchema):
    """添加资产请求"""
    ticker: str = Field(..., description="资产代码")
    asset_type: str = Field(..., description="资产类型")
    notes: Optional[str] = Field(None, description="备注")
    target_price: Optional[float] = Field(None, description="目标价")

class UpdateAssetRequest(BaseSchema):
    """更新资产请求"""
    notes: Optional[str] = Field(None, description="备注")
    target_price: Optional[float] = Field(None, description="目标价")

class UserAssetResponse(BaseSchema):
    """用户资产响应"""
    ticker: str = Field(..., description="资产代码")
    asset_type: str = Field(..., description="资产类型")
    asset_name: Optional[str] = Field(None, description="资产名称")
    current_price: Optional[float] = Field(None, description="当前价格（美元）")
    price_local: Optional[float] = Field(None, description="本地货币价格")
    currency_local: Optional[str] = Field(None, description="本地货币代码")
    price_change: Optional[float] = Field(None, description="价格变化")
    price_change_percent: Optional[float] = Field(None, description="价格变化百分比")
    market_cap: Optional[int] = Field(None, description="市值")
    volume: Optional[int] = Field(None, description="成交量")
    exchange: Optional[str] = Field(None, description="交易所")
    currency: Optional[str] = Field(None, description="货币")
    notes: Optional[str] = Field(None, description="备注")
    target_price: Optional[float] = Field(None, description="目标价")
    added_at: datetime = Field(..., description="添加时间")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")
    is_market_open: Optional[bool] = Field(None, description="市场是否开放")
    trade_time: Optional[datetime] = Field(None, description="交易时间")

class PortfolioSummary(BaseSchema):
    """投资组合摘要"""
    total_assets: int = Field(..., description="总资产数")
    asset_types: Dict[str, int] = Field(..., description="各类型资产数")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")

class AssetSearchRequest(BaseSchema):
    """资产搜索请求"""
    query: str = Field(..., description="搜索关键词")
    asset_types: Optional[List[str]] = Field(None, description="资产类型列表")
    limit: Optional[int] = Field(20, description="返回数量限制")

class AssetSearchResult(BaseSchema):
    """资产搜索结果"""
    ticker: str = Field(..., description="资产代码")
    name: str = Field(..., description="资产名称")
    asset_type: str = Field(..., description="资产类型")
    exchange: Optional[str] = Field(None, description="交易所")
    currency: Optional[str] = Field(None, description="货币")
    market_cap: Optional[int] = Field(None, description="市值")
    description: Optional[str] = Field(None, description="描述")
