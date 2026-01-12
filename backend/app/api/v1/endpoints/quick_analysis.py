"""
Quick Analysis API - 3层架构重构版本
API Layer - 仅负责路由和参数校验

Entitlements:
- run_quick_scan / run_chart_scan are free tier actions
- Always use SYSTEM_ONLY scope (eco mode, never BYOK)
- Anonymous users can call these endpoints
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from AICrews.database.models import User
from AICrews.schemas.quick_analysis import (
    QuickScanRequest, QuickScanResponse,
    ChartAnalysisRequest, ChartAnalysisResponse
)
from AICrews.schemas.entitlements import PolicyAction
from AICrews.services.quick_analysis_service import QuickAnalysisService
from backend.app.security import get_current_user_optional, get_db
from backend.app.api.v1.utils.entitlements_http import require_entitlement

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Quick Analysis"])

def get_quick_analysis_service(db: Session = Depends(get_db)) -> QuickAnalysisService:
    return QuickAnalysisService(db)

@router.post("/quick-scan", response_model=QuickScanResponse)
async def run_quick_scan(
    request: Request,
    body: QuickScanRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
    service: QuickAnalysisService = Depends(get_quick_analysis_service)
):
    """运行Quick Scan快速扫描

    硬编码Pipeline，不使用CrewAI
    目标：3-5秒内完成
    使用系统默认LLM配置 (SYSTEM_ONLY scope, eco mode)
    分析完成后自动写入 Library

    Entitlements:
    - Free tier action: anonymous and all users can call
    - Always uses system LLM (never BYOK)
    """
    # Entitlements check (free tier action, SYSTEM_ONLY scope)
    # Note: requested_mode=None forces eco mode per policy
    require_entitlement(
        action=PolicyAction.RUN_QUICK_SCAN,
        request=request,
        db=db,
        current_user=current_user,
        requested_mode=None,  # Force eco mode
    )

    try:
        logger.info(f"开始Quick Scan分析: {body.ticker}")

        result = await service.run_quick_scan(
            ticker=body.ticker,
            thesis=body.thesis,
            user=current_user
        )

        logger.info(f"Quick Scan分析完成: {body.ticker}, 耗时: {result.execution_time_ms}ms")
        return result

    except Exception as e:
        logger.error(f"Quick Scan分析失败: {body.ticker} - {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"分析失败: {str(e)}",
                "error_type": type(e).__name__,
                "ticker": body.ticker,
                "timestamp": datetime.now().isoformat()
            }
        )

@router.post("/chart-analysis", response_model=ChartAnalysisResponse)
async def run_chart_analysis(
    request: Request,
    body: ChartAnalysisRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
    service: QuickAnalysisService = Depends(get_quick_analysis_service)
):
    """运行 Chart Analysis 技术分析

    先用算法计算技术指标，再用LLM解释
    目标：<1分钟完成

    Entitlements:
    - Free tier action: anonymous and all users can call
    - Always uses system LLM (never BYOK)
    """
    # Entitlements check (free tier action, SYSTEM_ONLY scope)
    require_entitlement(
        action=PolicyAction.RUN_CHART_SCAN,
        request=request,
        db=db,
        current_user=current_user,
        requested_mode=None,  # Force eco mode
    )

    try:
        logger.info(f"开始Chart Analysis: {body.ticker}")

        result = await service.run_chart_analysis(
            ticker=body.ticker,
            thesis=body.thesis,
            user=current_user
        )

        logger.info(f"Chart Analysis完成: {body.ticker}, 耗时: {result.execution_time_ms}ms")
        return result

    except Exception as e:
        logger.error(f"Chart Analysis失败: {body.ticker} - {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"分析失败: {str(e)}",
                "error_type": type(e).__name__,
                "ticker": body.ticker,
                "timestamp": datetime.now().isoformat()
            }
        )
