"""
API Routes - FastAPI 路由定义
提供 RESTful API 接口
业务逻辑已下沉至 AICrews.services.analysis_service
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from AICrews.infrastructure.jobs.job_manager import JobStatus
from backend.app.security import get_current_user_optional, get_db
from AICrews.database.models import User
from AICrews.services.analysis_service import AnalysisService
from AICrews.services.entitlements.policy_engine import EntitlementPolicyEngine
from AICrews.schemas.entitlements import PolicyAction
from AICrews.application.crew.run_context import RunContext, run_context_scope
from AICrews.schemas.analysis import (
    AnalysisRequest,
    ChatRequest,
    ChatResponse,
    CrewInfo,
    CrewListResponse,
    JobResponse,
    JobStatusResponse,
    JobListResponse,
)
from AICrews.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])

def get_analysis_service() -> AnalysisService:
    return AnalysisService()

# ============================================
# 分析任务 API
# ============================================

@router.post(
    "/analysis/start",
    response_model=JobResponse,
    responses={400: {"model": ErrorResponse}},
    summary="启动分析任务",
    description="提交股票分析任务，返回任务ID用于后续查询",
)
async def start_analysis(
    request: AnalysisRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: AnalysisService = Depends(get_analysis_service),
    db: Session = Depends(get_db),
):
    """启动一个新的分析任务"""
    try:
        # 验证 crew 是否存在
        available_crews = service.list_available_crews()
        if request.crew_name not in available_crews:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown crew: {request.crew_name}. Available: {available_crews}"
            )
        
        user_id = current_user.id if current_user else None

        policy_engine = EntitlementPolicyEngine()
        decision = policy_engine.check(
            db,
            current_user,
            action=PolicyAction.RUN_OFFICIAL_CREW,
        )

        if not decision.allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "deny_code": decision.denial_code.value if decision.denial_code else None,
                    "message": decision.denial_message or "Forbidden",
                    "effective_tier": decision.effective_tier.value,
                    "effective_tier_reason": decision.effective_tier_reason,
                },
            )

        run_ctx = RunContext(
            entitlements_decision=decision,
            effective_scope=decision.effective_scope.value,
            byok_allowed=decision.limits.byok_allowed,
            runtime_limits=decision.limits,
        )

        analysis_date = request.date or datetime.now().strftime("%Y-%m-%d")

        def run_crew(job_id: str = None):
            with run_context_scope(run_ctx):
                result_dict = service.run_analysis(
                    ticker=request.ticker,
                    date=analysis_date,
                    crew_name=request.crew_name,
                    analysts=request.selected_analysts,
                    debate_rounds=request.debate_rounds or 1,
                    user_id=user_id,
                    run_id=job_id,
                )
                return str(result_dict.get("result", ""))

        job_id = service.job_manager.submit(
            run_crew,
            ticker=request.ticker,
            crew_name=request.crew_name,
            user_id=user_id,
        )
        
        return JobResponse(
            job_id=job_id,
            message="分析任务已提交",
            status="pending",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/analysis/status/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="查询任务状态",
    description="通过任务ID查询分析任务的执行状态",
)
async def get_analysis_status(
    job_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: AnalysisService = Depends(get_analysis_service),
):
    """查询分析任务状态"""
    user_id = current_user.id if current_user else None
    job = service.get_job_status(job_id, user_id=user_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    # 解析引用元数据 (调用 Service)
    structured_result = None
    result_text = job.result if job.status == JobStatus.COMPLETED else None
    
    if result_text:
        structured_result = service.process_job_result(result_text)
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        progress_message=job.progress_message,
        result=result_text,
        structured_result=structured_result,
        error=job.error if job.status == JobStatus.FAILED else None,
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        ticker=job.ticker,
        crew_name=job.crew_name,
    )


@router.get(
    "/analysis/list",
    response_model=JobListResponse,
    summary="列出任务历史",
    description="获取分析任务列表",
)
async def list_analysis_jobs(
    status: Optional[str] = Query(None, description="过滤状态"),
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: AnalysisService = Depends(get_analysis_service),
):
    """列出分析任务历史"""
    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid: {[s.value for s in JobStatus]}"
            )
    
    user_id = current_user.id if current_user else None
    jobs = service.list_jobs(status=status_filter, limit=limit, user_id=user_id)
    
    job_responses = [
        JobStatusResponse(
            job_id=job.job_id,
            status=job.status.value,
            progress=job.progress,
            progress_message=job.progress_message,
            result=None,
            error=job.error if job.status == JobStatus.FAILED else None,
            created_at=job.created_at.isoformat() if job.created_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            ticker=job.ticker,
            crew_name=job.crew_name,
        )
        for job in jobs
    ]
    
    return JobListResponse(jobs=job_responses, total=len(job_responses))


@router.delete(
    "/analysis/{job_id}",
    summary="取消任务",
    description="取消正在运行的分析任务",
)
async def cancel_analysis(
    job_id: str,
    service: AnalysisService = Depends(get_analysis_service)
):
    """取消分析任务"""
    cancelled = service.cancel_job(job_id)
    
    if cancelled:
        return {"message": f"Job {job_id} cancelled"}
    else:
        return {"message": f"Job {job_id} could not be cancelled"}



# ============================================
# Copilot 聊天 API
# ============================================

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="与 AI 助手对话",
)
async def chat_with_copilot(
    request: ChatRequest,
    service: AnalysisService = Depends(get_analysis_service)
):
    """与 AI Copilot 对话"""
    job = service.get_job_status(request.job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {request.job_id}")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Analysis not completed yet")
    
    # 记录用户消息
    service.add_chat_message(request.job_id, "user", request.message)
    
    # 生成回复 (调用 Service)
    reply = service.generate_chat_reply(request.message, job.result)
    
    # 记录 AI 回复
    service.add_chat_message(request.job_id, "assistant", reply)
    
    # 获取聊天历史
    # 这里我们直接从 job 对象中获取，或者 Service 可以提供一个 get_chat_history 方法
    # 目前 job 对象已经包含了 chat_history (如果它是从 JobManager 获取的 Job 对象)
    chat_history = [
        {"role": msg["role"], "content": msg["content"], "timestamp": msg.get("timestamp")}
        for msg in job.chat_history
    ]
    
    return ChatResponse(
        reply=reply,
        job_id=request.job_id,
        chat_history=chat_history,
    )
