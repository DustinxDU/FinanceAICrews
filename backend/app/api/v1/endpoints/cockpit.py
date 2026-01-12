"""
Cockpit 聚合 API

提供统一的 Cockpit 仪表盘接口，一次返回所有必要数据：
- 全局市场指数
- 用户关注资产的实时价格
- 宏观指标数据

设计目标：减少前端并行请求数，提升页面加载速度
业务逻辑已下沉至 AICrews.services.cockpit_service
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.app.security import get_current_user_optional, get_current_user, get_db
from AICrews.database.models import User as DBUser, UserCockpitIndicator
from AICrews.services.cockpit_service import CockpitService
from AICrews.schemas.cockpit import (
    CockpitDashboardResponse, CockpitAssetPrice,
    UserCockpitIndicatorResponse, UserCockpitIndicatorCreate, UserCockpitIndicatorReorder
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cockpit", tags=["Cockpit Dashboard"])

def get_cockpit_service(db: Session = Depends(get_db)) -> CockpitService:
    return CockpitService(db)

@router.get("/dashboard", response_model=CockpitDashboardResponse)
async def get_cockpit_dashboard(
    current_user: Optional[DBUser] = Depends(get_current_user_optional),
    force_refresh: bool = Query(False, description="强制刷新缓存"),
    service: CockpitService = Depends(get_cockpit_service)
):
    """
    获取 Cockpit 仪表盘数据（聚合接口）
    """
    try:
        user_id = current_user.id if current_user else None
        return await service.get_cockpit_dashboard(user_id, force_refresh)
    except Exception as e:
        logger.error(f"Error fetching cockpit dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indicators", response_model=List[UserCockpitIndicatorResponse])
async def get_indicators(
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的 Cockpit 指标"""
    return db.query(UserCockpitIndicator).filter(
        UserCockpitIndicator.user_id == current_user.id
    ).order_by(UserCockpitIndicator.display_order).all()

@router.post("/indicators", response_model=UserCockpitIndicatorResponse)
async def add_indicator(
    request: UserCockpitIndicatorCreate,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加 Cockpit 指标"""
    indicator = UserCockpitIndicator(
        user_id=current_user.id,
        indicator_id=request.indicator_id,
        display_order=request.display_order
    )
    db.add(indicator)
    db.commit()
    db.refresh(indicator)
    return indicator

@router.put("/indicators/reorder")
async def reorder_indicators(
    request: UserCockpitIndicatorReorder,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重排 Cockpit 指标"""
    for index, indicator_id in enumerate(request.indicator_ids):
        db.query(UserCockpitIndicator).filter(
            UserCockpitIndicator.id == indicator_id,
            UserCockpitIndicator.user_id == current_user.id
        ).update({"display_order": index})
    db.commit()
    return {"status": "success"}

@router.delete("/indicators/{indicator_id}")
async def delete_indicator(
    indicator_id: int,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除 Cockpit 指标"""
    db.query(UserCockpitIndicator).filter(
        UserCockpitIndicator.id == indicator_id,
        UserCockpitIndicator.user_id == current_user.id
    ).delete()
    db.commit()
    return {"status": "success"}

@router.get("/assets", response_model=List[CockpitAssetPrice])
async def get_cockpit_assets(
    current_user: DBUser = Depends(get_current_user),
    service: CockpitService = Depends(get_cockpit_service)
):
    """
    获取用户关注的资产价格（独立接口）
    """
    try:
        return await service.get_user_assets(current_user.id)
    except Exception as e:
        logger.error(f"Error fetching cockpit assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assets/{ticker}/price")
async def get_asset_price(
    ticker: str,
    force_refresh: bool = Query(False),
    service: CockpitService = Depends(get_cockpit_service)
) -> Dict[str, Any]:
    """
    获取单个资产价格
    """
    try:
        return await service.get_asset_price(ticker, force_refresh)
    except Exception as e:
        logger.error(f"Error fetching asset price: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/assets/{ticker}/subscribe")
async def subscribe_asset(
    ticker: str,
    current_user: DBUser = Depends(get_current_user),
    service: CockpitService = Depends(get_cockpit_service)
) -> Dict[str, Any]:
    """
    订阅资产（关注并启动实时同步）
    """
    try:
        return await service.subscribe_asset(current_user.id, ticker)
    except Exception as e:
        logger.error(f"Error subscribing asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/assets/{ticker}/subscribe")
async def unsubscribe_asset(
    ticker: str,
    current_user: DBUser = Depends(get_current_user),
    service: CockpitService = Depends(get_cockpit_service)
) -> Dict[str, Any]:
    """
    取消订阅资产（取消关注并可能停止同步）
    """
    try:
        return await service.unsubscribe_asset(current_user.id, ticker)
    except Exception as e:
        logger.error(f"Error unsubscribing asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_cockpit_status(
    service: CockpitService = Depends(get_cockpit_service)
) -> Dict[str, Any]:
    """获取 Cockpit 服务状态"""
    try:
        return await service.get_status()
    except Exception as e:
        logger.error(f"Error fetching cockpit status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh")
async def refresh_cockpit_data(
    service: CockpitService = Depends(get_cockpit_service)
) -> Dict[str, str]:
    """刷新所有 Cockpit 数据"""
    try:
        await service.refresh_data()
        return {"message": "Cockpit data refreshed successfully"}
    except Exception as e:
        logger.error(f"Error refreshing cockpit data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
