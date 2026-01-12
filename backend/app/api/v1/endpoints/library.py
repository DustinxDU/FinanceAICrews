"""
Library API - 资产情报局读取接口

提供分析记录的查询和管理功能：
- 按资产 ticker 聚合查询
- 时间轴查看
- 详情查看
- 附件下载

API Layer - 仅负责路由和参数校验
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from backend.app.security import get_db, get_current_user
from AICrews.database.models import User
from AICrews.schemas.library import (
    AssetGroupResponse, TimelineEntryResponse, InsightDetailResponse, LibraryInsight
)
from AICrews.services.library_service import LibraryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["Library"])

def get_library_service(db: Session = Depends(get_db)) -> LibraryService:
    return LibraryService(db)

@router.get("/assets", response_model=List[AssetGroupResponse])
async def list_assets(
    current_user: User = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
):
    """
    获取用户关注的资产列表（按 ticker 聚合）
    """
    try:
        return await service.list_assets(current_user.id)
    except Exception as e:
        logger.error(f"Error listing assets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timeline", response_model=List[TimelineEntryResponse])
async def get_timeline(
    ticker: Optional[str] = Query(None, description="过滤特定资产"),
    days: int = Query(30, ge=1, le=365, description="时间范围（天）"),
    current_user: User = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
):
    """
    获取分析时间轴
    
    按日期聚合显示每天的分析记录数量和来源
    """
    try:
        return await service.get_timeline(current_user.id, days, ticker)
    except Exception as e:
        logger.error(f"Error getting timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insights", response_model=List[LibraryInsight])
async def list_insights(
    ticker: Optional[str] = Query(None, description="过滤特定资产"),
    source_type: Optional[str] = Query(None, description="过滤来源类型"),
    sentiment: Optional[str] = Query(None, description="过滤情绪"),
    signal: Optional[str] = Query(None, description="过滤信号"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
):
    """
    获取分析洞察列表
    
    支持按资产、来源类型、情绪、信号过滤
    """
    try:
        return await service.list_insights(
            user_id=current_user.id,
            ticker=ticker,
            source_type=source_type,
            sentiment=sentiment,
            signal=signal,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error listing insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insights/{insight_id}", response_model=InsightDetailResponse)
async def get_insight_detail(
    insight_id: int,
    current_user: User = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
):
    """
    获取分析详情

    包含分析记录、附件列表和追溯日志
    """
    try:
        result = await service.get_insight_detail(current_user.id, insight_id)
        if not result:
            raise HTTPException(status_code=404, detail="Insight not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting insight detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/insights/{insight_id}/read")
async def mark_insight_as_read(
    insight_id: int,
    current_user: User = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
):
    """
    标记分析为已读
    """
    try:
        success = await service.mark_as_read(current_user.id, insight_id)
        if not success:
            raise HTTPException(status_code=404, detail="Insight not found")
        return {"status": "ok", "message": "Marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking insight as read: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/insights/{insight_id}/favorite")
async def toggle_insight_favorite(
    insight_id: int,
    is_favorite: bool = Query(..., description="收藏状态"),
    current_user: User = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
):
    """
    切换分析收藏状态
    """
    try:
        success = await service.toggle_favorite(current_user.id, insight_id, is_favorite)
        if not success:
            raise HTTPException(status_code=404, detail="Insight not found")
        return {"status": "ok", "is_favorite": is_favorite}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling favorite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
