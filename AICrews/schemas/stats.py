"""
Stats Schemas - 任务执行统计相关模型

定义任务执行、工具调用、LLM 调用和 Agent 活动的统计事件模型。
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import Field
from datetime import datetime

from AICrews.schemas.common import BaseSchema


from enum import Enum

class RunEventType(str, Enum):
    """运行事件类型"""
    ACTIVITY = "activity"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    LLM_CALL = "llm_call"
    TASK_STATE = "task_state"
    TASK_OUTPUT = "task_output"  # Structured task output with diagnostics
    SYSTEM = "system"

class RunEvent(BaseSchema):
    """统一运行事件信封"""
    event_id: str = Field(default_factory=lambda: str(datetime.now().timestamp()), description="事件唯一标识")
    run_id: str = Field(..., description="运行(Job) ID")
    event_type: RunEventType = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    agent_name: Optional[str] = Field(None, description="相关 Agent 名称")
    task_id: Optional[str] = Field(None, description="相关 Task ID")
    severity: str = Field("info", description="严重程度: debug, info, warning, error")
    payload: Dict[str, Any] = Field(..., description="类型化数据负载")

class ToolUsageEvent(BaseSchema):
    """工具使用事件"""
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    tool_name: str = Field(..., description="工具名称")
    agent_name: str = Field(..., description="Agent 名称")
    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")
    output_data: Optional[Any] = Field(None, description="输出数据")
    status: str = Field("pending", description="状态: pending, running, success, failed")
    duration_ms: Optional[int] = Field(None, description="耗时(ms)")
    error_message: Optional[str] = Field(None, description="错误信息")


class LLMCallEvent(BaseSchema):
    """LLM 调用事件

    Enhanced for detailed debug logging:
    - prompt_preview: First N chars of the prompt sent to LLM
    - response_preview: First N chars of the LLM response
    """
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    agent_name: str = Field(..., description="Agent 名称")
    llm_provider: str = Field(..., description="LLM 提供商")
    model_name: str = Field(..., description="模型名称")
    prompt_tokens: Optional[int] = Field(None, description="Prompt tokens")
    completion_tokens: Optional[int] = Field(None, description="Completion tokens")
    total_tokens: Optional[int] = Field(None, description="Total tokens")
    duration_ms: Optional[int] = Field(None, description="耗时(ms)")
    status: str = Field("pending", description="状态: pending, running, success, failed")
    error_message: Optional[str] = Field(None, description="错误信息")
    # Enhanced debug fields
    prompt_preview: Optional[str] = Field(None, description="Prompt 预览（截断）")
    response_preview: Optional[str] = Field(None, description="Response 预览（截断）")
    serialized_info: Optional[Dict[str, Any]] = Field(None, description="序列化的模型信息")
    # Cost/telemetry
    estimated_cost_usd: Optional[float] = Field(
        None, description="Estimated USD cost for this call (pricing.yaml)"
    )
    pricing_version: Optional[str] = Field(
        None, description="Pricing config version used for cost estimation"
    )
    pricing_updated: Optional[str] = Field(
        None, description="Pricing config updated timestamp used for cost estimation"
    )


class AgentActivityEvent(BaseSchema):
    """Agent 活动事件"""
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    agent_name: str = Field(..., description="Agent 名称")
    activity_type: str = Field(..., description="活动类型: thinking, tool_call, llm_call, delegation, output")
    message: str = Field(..., description="活动消息")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class TaskExecutionStats(BaseSchema):
    """任务执行统计"""
    job_id: str = Field(..., description="任务 ID")
    ticker: str = Field(..., description="股票代码")
    crew_name: str = Field(..., description="Crew 名称")
    
    # 时间统计
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    total_duration_ms: Optional[int] = Field(None, description="总耗时(ms)")
    
    # 工具统计
    tool_calls: List[ToolUsageEvent] = Field(default_factory=list, description="工具调用列表")
    tool_call_count: int = Field(0, description="工具调用总数")
    tool_success_count: int = Field(0, description="工具调用成功数")
    tool_failure_count: int = Field(0, description="工具调用失败数")
    
    # LLM 统计
    llm_calls: List[LLMCallEvent] = Field(default_factory=list, description="LLM 调用列表")
    llm_call_count: int = Field(0, description="LLM 调用总数")
    total_prompt_tokens: int = Field(0, description="Prompt tokens 总数")
    total_completion_tokens: int = Field(0, description="Completion tokens 总数")
    total_tokens: int = Field(0, description="Tokens 总数")
    
    # Agent 活动
    agent_activities: List[AgentActivityEvent] = Field(default_factory=list, description="Agent 活动列表")
    
    # 状态
    status: str = Field("pending", description="状态: pending, running, completed, failed")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    def to_summary(self) -> Dict[str, Any]:
        """生成执行摘要"""
        tool_summary = {}
        for call in self.tool_calls:
            if call.tool_name not in tool_summary:
                tool_summary[call.tool_name] = {"count": 0, "success": 0, "failed": 0, "total_ms": 0}
            tool_summary[call.tool_name]["count"] += 1
            if call.status == "success":
                tool_summary[call.tool_name]["success"] += 1
            elif call.status == "failed":
                tool_summary[call.tool_name]["failed"] += 1
            if call.duration_ms:
                tool_summary[call.tool_name]["total_ms"] += call.duration_ms
        
        llm_summary = {}
        for call in self.llm_calls:
            key = f"{call.llm_provider}/{call.model_name}"
            if key not in llm_summary:
                llm_summary[key] = {"count": 0, "tokens": 0, "total_ms": 0}
            llm_summary[key]["count"] += 1
            if call.total_tokens:
                llm_summary[key]["tokens"] += call.total_tokens
            if call.duration_ms:
                llm_summary[key]["total_ms"] += call.duration_ms
        
        return {
            "job_id": self.job_id,
            "ticker": self.ticker,
            "crew_name": self.crew_name,
            "status": self.status,
            "duration_ms": self.total_duration_ms,
            "tools": {
                "total_calls": self.tool_call_count,
                "success": self.tool_success_count,
                "failed": self.tool_failure_count,
                "by_tool": tool_summary
            },
            "llm": {
                "total_calls": self.llm_call_count,
                "total_tokens": self.total_tokens,
                "prompt_tokens": self.total_prompt_tokens,
                "completion_tokens": self.total_completion_tokens,
                "by_model": llm_summary
            }
        }
