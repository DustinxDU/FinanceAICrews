"""
Portfolio Management API - 3层架构重构版本
API Layer - 仅负责路由和参数校验
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from AICrews.services.portfolio_service import PortfolioService
from AICrews.schemas.portfolio import (
    AddAssetRequest, UpdateAssetRequest, UserAssetResponse,
    PortfolioSummary, AssetSearchRequest, AssetSearchResult
)
from AICrews.schemas.common import SuccessResponse
from backend.app.security import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["Portfolio Management"])

def get_portfolio_service(db: Session = Depends(get_db)) -> PortfolioService:
    return PortfolioService(db)

@router.post("/search", response_model=List[AssetSearchResult])
async def search_assets(
    request: AssetSearchRequest,
    service: PortfolioService = Depends(get_portfolio_service)
):
    """搜索资产"""
    return await service.search_assets(request)

@router.post("/assets", response_model=UserAssetResponse)
async def add_asset(
    request: AddAssetRequest,
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """添加资产到投资组合"""
    try:
        user_id = current_user.id
        return await service.add_user_asset(user_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding asset: {e}")
        raise HTTPException(status_code=500, detail="Failed to add asset")

@router.get("/assets", response_model=List[UserAssetResponse])
async def get_my_assets(
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """获取我的投资组合"""
    return await service.get_user_assets(current_user.id)

@router.delete("/assets/{ticker}", response_model=SuccessResponse)
async def remove_asset(
    ticker: str,
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """移除资产"""
    success = await service.remove_user_asset(current_user.id, ticker)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    return SuccessResponse(message=f"Asset {ticker} removed")

@router.put("/assets/{ticker}", response_model=UserAssetResponse)
async def update_asset(
    ticker: str,
    request: UpdateAssetRequest,
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """更新资产备注或目标价"""
    try:
        return await service.update_user_asset(current_user.id, ticker, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """获取投资组合摘要"""
    return await service.get_portfolio_summary(current_user.id)
