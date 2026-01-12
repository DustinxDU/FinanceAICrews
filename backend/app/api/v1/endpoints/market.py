"""
全球市场数据 API

通过 MarketService 获取全球主要市场指数数据和宏观经济指标
业务逻辑已完全下沉至 AICrews.services.market_service
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.security import get_current_user, get_db
from AICrews.database.models import User
from AICrews.services.market_service import MarketService
from AICrews.schemas.market import MarketDataResponse, CockpitMacroResponse, AvailableIndicatorResponse
from AICrews.schemas.cockpit import UserCockpitIndicatorResponse, UserCockpitIndicatorCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["Global Market Data"])

def get_market_service(db: Session = Depends(get_db)) -> MarketService:
    return MarketService(db)

@router.get("/global", response_model=MarketDataResponse)
async def get_global_market_data(
    force_refresh: bool = False,
    service: MarketService = Depends(get_market_service)
):
    """
    获取全球主要市场指数数据
    """
    try:
        return await service.get_global_market_data(force_refresh=force_refresh)
    except Exception as e:
        logger.error(f"Error fetching global market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cockpit/macro", response_model=CockpitMacroResponse)
async def get_cockpit_macro_data(
    force_refresh: bool = False,
    service: MarketService = Depends(get_market_service)
):
    """
    获取 Cockpit 宏观经济指标数据
    """
    try:
        return await service.get_cockpit_macro_data(force_refresh=force_refresh)
    except Exception as e:
        logger.error(f"Error fetching cockpit macro data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cockpit/macro/personalized", response_model=CockpitMacroResponse)
async def get_personalized_cockpit_data(
    current_user: User = Depends(get_current_user),
    service: MarketService = Depends(get_market_service)
):
    """
    获取用户个性化的 Cockpit 宏观指标
    基于用户设置的 UserCockpitIndicator 过滤显示的指标
    """
    try:
        return await service.get_personalized_cockpit_data(user_id=current_user.id)
    except Exception as e:
        logger.error(f"Error fetching personalized cockpit data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cockpit/available-indicators", response_model=List[AvailableIndicatorResponse])
async def get_available_indicators(
    current_user: User = Depends(get_current_user),
    service: MarketService = Depends(get_market_service)
):
    """
    获取所有可用的 Cockpit 宏观指标
    返回指标列表，并标记用户已选择的指标
    """
    try:
        return await service.get_available_indicators(user_id=current_user.id)
    except Exception as e:
        logger.error(f"Error fetching available indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cockpit/user-indicators", response_model=List[UserCockpitIndicatorResponse])
async def get_user_indicators(
    current_user: User = Depends(get_current_user),
    service: MarketService = Depends(get_market_service)
):
    """获取用户选择的 Cockpit 宏观指标列表"""
    try:
        return await service.get_user_indicators(user_id=current_user.id)
    except Exception as e:
        logger.error(f"Error fetching user indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cockpit/user-indicators")
async def add_user_indicator(
    request: UserCockpitIndicatorCreate,
    current_user: User = Depends(get_current_user),
    service: MarketService = Depends(get_market_service)
) -> Dict[str, Any]:
    """添加用户 Cockpit 宏观指标"""
    try:
        return await service.add_user_indicator(
            user_id=current_user.id,
            indicator_id=request.indicator_id,
            display_order=request.display_order or 0
        )
    except Exception as e:
        logger.error(f"Error adding user indicator: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cockpit/user-indicators/{indicator_id}")
async def remove_user_indicator(
    indicator_id: str,
    current_user: User = Depends(get_current_user),
    service: MarketService = Depends(get_market_service)
) -> Dict[str, str]:
    """移除用户 Cockpit 宏观指标"""
    try:
        return await service.remove_user_indicator(
            user_id=current_user.id,
            indicator_id=indicator_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing user indicator: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cockpit/user-indicators/{indicator_id}/order")
async def update_indicator_order(
    indicator_id: str,
    new_order: int,
    current_user: User = Depends(get_current_user),
    service: MarketService = Depends(get_market_service)
) -> Dict[str, str]:
    """更新用户 Cockpit 宏观指标顺序"""
    try:
        return await service.update_indicator_order(
            user_id=current_user.id,
            indicator_id=indicator_id,
            new_order=new_order
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating indicator order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_market_status(
    service: MarketService = Depends(get_market_service)
) -> Dict[str, Any]:
    """获取全球市场服务状态"""
    try:
        return await service.get_status()
    except Exception as e:
        logger.error(f"Error fetching market status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh")
async def refresh_market_data(
    service: MarketService = Depends(get_market_service)
) -> Dict[str, str]:
    """刷新所有市场数据"""
    try:
        await service.refresh_data()
        return {"message": "Market data refreshed successfully"}
    except Exception as e:
        logger.error(f"Error refreshing market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
