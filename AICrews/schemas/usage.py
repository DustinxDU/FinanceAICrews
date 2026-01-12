from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class UsageStatsResponse(BaseModel):
    """使用统计响应"""
    total_tokens_current_month: int
    total_tokens_previous_month: int
    token_growth_percentage: float
    reports_generated_current_month: int
    estimated_cost_current_month: float
    currency: str = "USD"

class UsageActivityItem(BaseModel):
    """使用活动项目"""
    id: int
    date: str
    time: str
    activity: str
    model: str
    reports: int
    tokens: int

class UsageActivityResponse(BaseModel):
    """使用活动响应"""
    items: List[UsageActivityItem]
    total_count: int
    current_page: int
    total_pages: int

class ExportUsageRequest(BaseModel):
    """导出使用数据请求"""
    start_date: str
    end_date: str
    format: str = "csv"
