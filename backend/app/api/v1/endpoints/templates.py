"""
模板目录 API - Template Catalog Endpoints

提供官方模板浏览、导入、个性化编辑等功能。

Endpoints:
- GET /templates - 获取模板目录列表
- GET /templates/{template_id} - 获取模板详情
- POST /templates/{template_id}/import - 导入模板到用户空间
- GET /templates/updates - 获取模板更新通知
- POST /templates/updates/{notification_id}/apply - 应用模板更新
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from AICrews.database.models import User
from backend.app.security import get_db
from AICrews.services.template_service import TemplateService
from AICrews.schemas.template import (
    TemplateListItem,
    TemplateDetail,
    TemplateImportRequest,
    TemplateImportResponse,
    TemplateUpdateNotificationItem,
    ApplyUpdateRequest,
    ApplyUpdateResponse,
    CategoryCount,
    MyImportItem
)
from backend.app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/templates", tags=["Templates"])

def get_template_service(db: Session = Depends(get_db)) -> TemplateService:
    return TemplateService(db)

@router.get("", response_model=List[TemplateListItem])
async def list_templates(
    template_type: Optional[str] = Query(None, description="Filter by type: agent, task, crew"),
    category: Optional[str] = Query(None, description="Filter by category"),
    featured_only: bool = Query(False, description="Only show featured templates"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(get_current_user),
):
    """获取官方模板目录列表"""
    return service.list_templates(
        template_type=template_type,
        category=category,
        featured_only=featured_only,
        search=search,
        limit=limit,
        offset=offset
    )

@router.get("/categories", response_model=List[CategoryCount])
async def list_categories(
    service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(get_current_user),
):
    """获取所有模板分类"""
    return service.list_categories()

@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: int,
    service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(get_current_user),
):
    """获取模板详情"""
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.post("/{template_id}/import", response_model=TemplateImportResponse)
async def import_template(
    template_id: int,
    request: TemplateImportRequest,
    service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(get_current_user),
):
    """
    导入模板到用户空间
    
    将官方模板深拷贝到用户的 agent_definitions/task_definitions/crew_definitions 表中
    """
    try:
        return service.import_template(template_id, current_user.id, request)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to import template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/updates/notifications", response_model=List[TemplateUpdateNotificationItem])
async def get_update_notifications(
    unread_only: bool = Query(True, description="Only show unread notifications"),
    service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(get_current_user),
):
    """获取用户的模板更新通知"""
    return service.get_update_notifications(current_user.id, unread_only)

@router.post("/updates/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(get_current_user),
):
    """标记通知为已读"""
    success = service.mark_notification_read(notification_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True, "message": "Notification marked as read"}

@router.post("/updates/{notification_id}/apply", response_model=ApplyUpdateResponse)
async def apply_template_update(
    notification_id: int,
    request: ApplyUpdateRequest,
    service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(get_current_user),
):
    """
    应用模板更新
    
    将官方模板的新版本合并到用户已导入的资源中
    """
    try:
        return service.apply_template_update(notification_id, current_user.id, request)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to apply update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-imports", response_model=List[MyImportItem])
async def list_my_imports(
    template_type: Optional[str] = Query(None),
    service: TemplateService = Depends(get_template_service),
    current_user: User = Depends(get_current_user),
):
    """获取用户已导入的模板列表"""
    return service.list_my_imports(current_user.id, template_type)
