"""
Task Tracking API - 任务跟踪接口
业务逻辑已下沉至 AICrews.services.tracking_service

SECURITY: All endpoints require authentication to prevent
unauthorized injection of fake tracking data.
"""
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends

from backend.app.security import get_current_user
from AICrews.infrastructure.storage import get_storage
from backend.app.ws.run_log_manager import manager as ws_manager
from AICrews.database.models import User
from AICrews.services.tracking_service import TrackingService
from AICrews.schemas.stats import (
    ToolUsageEvent,
    LLMCallEvent,
    AgentActivityEvent
)
from AICrews.schemas.tracking import (
    ToolEventRequest,
    LLMEventRequest,
    ActivityEventRequest,
    LiveStatusResponse,
    CompletionReportResponse,
    TrackingHistoryItem
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["Task Tracking"])

# ============================================
# Service Dependency
# ============================================

_service = TrackingService()

def get_tracking_service() -> TrackingService:
    if not _service.storage:
        _service.set_dependencies(get_storage(), ws_manager)
    return _service

# ============================================
# API Routes
# ============================================

@router.post("/init/{job_id}", summary="初始化任务跟踪")
async def init_tracking(
    job_id: str,
    ticker: str,
    crew_name: str,
    current_user: User = Depends(get_current_user),
    service: TrackingService = Depends(get_tracking_service)
) -> Dict[str, str]:
    """Initialize job tracking. Requires authentication."""
    service.init_job(job_id, ticker, crew_name)
    return {"message": f"Tracking initialized for job {job_id}"}


@router.post("/tool-event", summary="记录工具使用事件")
async def record_tool_event(
    request: ToolEventRequest,
    current_user: User = Depends(get_current_user),
    service: TrackingService = Depends(get_tracking_service)
) -> Dict[str, str]:
    """Record tool usage event. Requires authentication."""
    event = ToolUsageEvent(
        tool_name=request.tool_name,
        agent_name=request.agent_name,
        status=request.status,
        input_data=request.input_data,
        output_data=request.output_data,
        duration_ms=request.duration_ms,
        error_message=request.error_message,
    )
    service.add_tool_event(request.job_id, event)
    return {"message": "Tool event recorded"}


@router.post("/llm-event", summary="记录 LLM 调用事件")
async def record_llm_event(
    request: LLMEventRequest,
    current_user: User = Depends(get_current_user),
    service: TrackingService = Depends(get_tracking_service)
) -> Dict[str, str]:
    """Record LLM call event. Requires authentication."""
    event = LLMCallEvent(
        agent_name=request.agent_name,
        llm_provider=request.llm_provider,
        model_name=request.model_name,
        status=request.status,
        prompt_tokens=request.prompt_tokens,
        completion_tokens=request.completion_tokens,
        total_tokens=request.total_tokens,
        duration_ms=request.duration_ms,
        error_message=request.error_message,
    )
    service.add_llm_event(request.job_id, event)
    return {"message": "LLM event recorded"}


@router.post("/activity", summary="记录 Agent 活动")
async def record_activity(
    request: ActivityEventRequest,
    current_user: User = Depends(get_current_user),
    service: TrackingService = Depends(get_tracking_service)
) -> Dict[str, str]:
    """Record agent activity event. Requires authentication."""
    event = AgentActivityEvent(
        agent_name=request.agent_name,
        activity_type=request.activity_type,
        message=request.message,
        details=request.details,
    )
    service.add_activity(request.job_id, event)
    return {"message": "Activity recorded"}


@router.post("/complete/{job_id}", summary="标记任务完成")
async def complete_tracking(
    job_id: str,
    status: str = "completed",
    error: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: TrackingService = Depends(get_tracking_service)
) -> Dict[str, str]:
    """Mark job tracking as complete. Requires authentication."""
    service.complete_job(job_id, status, error)
    return {"message": f"Tracking completed for job {job_id}"}


@router.get("/live/{job_id}", summary="获取实时状态", response_model=LiveStatusResponse)
async def get_live_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    service: TrackingService = Depends(get_tracking_service)
) -> LiveStatusResponse:
    """Get live execution status. Requires authentication."""
    status = service.get_live_status_data(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return status


@router.get("/report/{job_id}", summary="获取完成报告", response_model=CompletionReportResponse)
async def get_completion_report(
    job_id: str,
    current_user: User = Depends(get_current_user),
    service: TrackingService = Depends(get_tracking_service)
) -> CompletionReportResponse:
    """Get completion report. Requires authentication."""
    report = service.get_completion_report_data(job_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report not found: {job_id}")
    return report


@router.get("/history", summary="获取历史统计列表", response_model=List[TrackingHistoryItem])
async def list_tracking_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    service: TrackingService = Depends(get_tracking_service)
) -> List[TrackingHistoryItem]:
    """Get tracking history list. Requires authentication."""
    return service.list_tracking_history(limit)
