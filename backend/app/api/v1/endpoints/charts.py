"""
图表数据API - 混合模式实现

按照您的架构设计：

方案A：Cockpit轻量级展示
- 策略：只读realtime_quotes表
- 实现：后台Job每5分钟更新，前端读数据库

方案B：图表详情页（需要细颗粒度数据）
- 策略：透传(Pass-through)，不存库
- 实现：前端请求 -> 后端收到 -> 不查数据库 -> 直接调用MCP -> 返回前端
- 优化：短暂Redis缓存5分钟，防止重复API调用

数据流：
GET /api/chart?ticker=AAPL&resolution=5m
1. 检查Redis缓存
2. 没有 -> 调用MCP API -> 存Redis -> 返回
3. 有 -> 直接返回

业务逻辑已完全下沉至 AICrews.services.chart_service
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from AICrews.schemas.chart import ChartDataRequest, ChartDataResponse, SparklineResponse
from AICrews.services.chart_service import ChartDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/charts", tags=["Chart Data"])

def get_chart_service() -> ChartDataService:
    return ChartDataService()

@router.post("/data", response_model=ChartDataResponse)
async def get_chart_data(
    request: ChartDataRequest,
    service: ChartDataService = Depends(get_chart_service)
):
    """
    获取图表数据
    """
    try:
        result = await service.get_chart_data(request)
        if not result:
            raise HTTPException(status_code=404, detail=f"No data found for {request.ticker}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sparkline/{ticker}", response_model=SparklineResponse)
async def get_sparkline_data(
    ticker: str,
    period: str = Query("5d", description="时间周期: 5d, 1m, 3m, 1y, 5y"),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    service: ChartDataService = Depends(get_chart_service)
):
    """
    获取资产简略行情（用于前端组件展示）
    """
    try:
        result = await service.get_sparkline(ticker, period, force_refresh)
        if not result:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sparkline data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
