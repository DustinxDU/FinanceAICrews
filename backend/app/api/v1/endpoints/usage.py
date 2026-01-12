"""Usage Activity API - 用户使用活动统计接口

统计用户的 token 使用量、报告生成数、API 成本等
API Layer - 仅负责路由和参数校验
"""

import logging
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.security import get_current_user, get_db
from AICrews.database.models import User
from AICrews.schemas.usage import UsageStatsResponse, UsageActivityResponse, ExportUsageRequest
from AICrews.services.usage_service import UsageService
from AICrews.services.export_service import ExportService, ExportFormat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usage", tags=["Usage Activity"])

def get_usage_service(db: Session = Depends(get_db)) -> UsageService:
    return UsageService(db)

@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    service: UsageService = Depends(get_usage_service)
):
    """获取用户使用统计"""
    return await service.get_usage_stats(current_user.id)

@router.get("/activity", response_model=UsageActivityResponse)
async def get_activity_log(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: UsageService = Depends(get_usage_service)
):
    """获取活动日志"""
    return await service.get_activity_log(current_user.id, page, limit)

@router.post("/export")
async def export_usage_data(
    request: ExportUsageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """导出使用数据为 CSV 文件

    Returns streaming CSV file download.
    """
    export_service = ExportService()

    # Parse dates
    start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))

    # Get activity data from usage service
    service = UsageService(db)
    activity = await service.get_activity_log(
        user_id=current_user.id,
        page=1,
        page_size=10000  # Large page for export
    )

    # Generate CSV
    content = export_service.generate_csv(activity["items"])
    filename = export_service.generate_filename(ExportFormat.CSV, start_date, end_date)

    # Return streaming response
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
