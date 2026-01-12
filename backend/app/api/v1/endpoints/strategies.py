"""
User Strategies API - 用户自定义策略管理
提供用户策略的 CRUD 操作和执行功能
API Layer - 仅负责路由和参数校验
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from backend.app.security import get_db, get_current_user
from AICrews.database.models import User
from AICrews.schemas.strategy import (
    StrategyCreate, StrategyUpdate, StrategyResponse,
    StrategyValidation, StrategyEvaluation, EvaluationResult
)
from AICrews.services.strategy_service import StrategyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["User Strategies"])

def get_strategy_service(db: Session = Depends(get_db)) -> StrategyService:
    return StrategyService(db)

# ============================================
# CRUD Endpoints
# ============================================

@router.get("", response_model=List[StrategyResponse])
async def list_strategies(
    category: Optional[str] = Query(None, description="按类别筛选"),
    include_public: bool = Query(False, description="是否包含公开策略"),
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取用户的策略列表"""
    return await service.list_strategies(current_user.id, category, include_public)

@router.post("", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    strategy: StrategyCreate,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """创建新策略"""
    try:
        return await service.create_strategy(current_user.id, strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取策略详情"""
    try:
        return await service.get_strategy(current_user.id, strategy_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    update: StrategyUpdate,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """更新策略"""
    try:
        return await service.update_strategy(current_user.id, strategy_id, update)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="Strategy not found")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """删除策略"""
    try:
        await service.delete_strategy(current_user.id, strategy_id)
        return {"message": f"Strategy {strategy_id} deleted"}
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found")

# ============================================
# Validation & Evaluation Endpoints
# ============================================

@router.post("/validate")
async def validate_formula(
    request: StrategyValidation,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """验证策略公式语法和安全性"""
    return await service.validate_formula(request.formula)

@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate_strategy(
    request: StrategyEvaluation,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """评估策略"""
    try:
        return await service.evaluate_strategy(
            user_id=current_user.id,
            ticker=request.ticker,
            strategy_id=request.strategy_id,
            formula=request.formula
        )
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

@router.post("/batch-evaluate")
async def batch_evaluate_strategy(
    strategy_id: int,
    tickers: List[str],
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """批量评估策略（多个股票）"""
    try:
        return await service.batch_evaluate_strategy(current_user.id, strategy_id, tickers)
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

# ============================================
# Strategy Market (Public Strategies)
# ============================================

@router.get("/market/popular")
async def get_popular_strategies(
    category: Optional[str] = None,
    limit: int = Query(10, le=50),
    service: StrategyService = Depends(get_strategy_service)
):
    """获取热门公开策略"""
    return await service.get_popular_strategies(category, limit)

@router.post("/{strategy_id}/clone")
async def clone_strategy(
    strategy_id: int,
    new_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service)
):
    """克隆公开策略到自己的账户"""
    try:
        return await service.clone_strategy(current_user.id, strategy_id, new_name)
    except ValueError:
        raise HTTPException(status_code=404, detail="Public strategy not found")
