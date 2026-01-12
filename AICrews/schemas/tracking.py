from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class ToolEventRequest(BaseModel):
    """工具事件请求"""
    job_id: str
    tool_name: str
    agent_name: str
    status: str = "pending"
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Any] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None

class LLMEventRequest(BaseModel):
    """LLM 事件请求"""
    job_id: str
    agent_name: str
    llm_provider: str
    model_name: str
    status: str = "pending"
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None

class ActivityEventRequest(BaseModel):
    """活动事件请求"""
    job_id: str
    agent_name: str
    activity_type: str
    message: str
    details: Optional[Dict[str, Any]] = None

class LiveStatusResponse(BaseModel):
    """实时状态响应"""
    job_id: str
    status: str
    ticker: str
    crew_name: str
    started_at: Optional[str] = None
    elapsed_ms: Optional[int] = None
    current_agent: Optional[str] = None
    current_activity: Optional[str] = None
    tool_call_count: int = 0
    llm_call_count: int = 0
    total_tokens: int = 0
    recent_activities: List[Dict[str, Any]] = []

class CompletionReportResponse(BaseModel):
    """完成报告响应"""
    job_id: str
    ticker: str
    crew_name: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    tools_summary: Dict[str, Any] = {}
    llm_summary: Dict[str, Any] = {}
    tool_calls: List[Dict[str, Any]] = []
    llm_calls: List[Dict[str, Any]] = []

class TrackingHistoryItem(BaseModel):
    """历史统计项"""
    job_id: str
    ticker: str
    crew_name: str
    status: str
    started_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    tool_calls: int
    llm_calls: int
    total_tokens: int
