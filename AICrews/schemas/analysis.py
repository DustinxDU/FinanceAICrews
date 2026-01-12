from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from AICrews.schemas.common import BaseSchema

class AnalysisRequest(BaseSchema):
    """分析请求"""
    ticker: str = Field(..., description="股票代码")
    crew_name: str = Field(default="standard", description="策略/战队名称")
    date: Optional[str] = Field(default=None, description="分析日期")
    selected_analysts: Optional[List[str]] = Field(default=None, description="选择的分析师")
    debate_rounds: Optional[int] = Field(default=None, description="辩论轮数")

class JobResponse(BaseSchema):
    """任务提交响应"""
    job_id: str
    message: str
    status: str

class CitationInfo(BaseSchema):
    """引用信息"""
    source_name: str = Field(..., description="知识源文件名")
    display_name: Optional[str] = Field(None, description="知识源显示名称")
    description: Optional[str] = Field(None, description="知识源描述")
    category: Optional[str] = Field(None, description="知识源分类")
    is_valid: bool = Field(True, description="引用是否有效")

class StructuredResult(BaseSchema):
    """结构化任务结果"""
    text: str = Field(..., description="原始结果文本")
    citations: List[CitationInfo] = Field(default_factory=list, description="引用列表")
    citation_count: int = Field(0, description="引用数量")
    has_citations: bool = Field(False, description="是否包含引用")

from AICrews.schemas.stats import RunEvent, TaskExecutionStats

class RunSummary(BaseSchema):
    """运行执行摘要"""
    total_duration_ms: int = Field(0, description="总耗时(ms)")
    total_tokens: int = Field(0, description="总 Token 数")
    prompt_tokens: int = Field(0, description="Prompt Token 数")
    completion_tokens: int = Field(0, description="Completion Token 数")
    tool_calls_count: int = Field(0, description="工具调用次数")
    agent_count: int = Field(0, description="Agent 数量")
    task_count: int = Field(0, description="Task 数量")
    status: str = Field(..., description="执行状态")

class TaskOutputSummary(BaseSchema):
    """Task output summary for API response"""
    task_id: Optional[str] = Field(None, description="Task ID")
    agent_name: Optional[str] = Field(None, description="Agent that produced the output")
    raw_preview: Optional[str] = Field(None, description="Truncated raw output preview")
    validation_passed: bool = Field(True, description="Whether validation passed")
    citation_count: int = Field(0, description="Number of citations extracted")
    output_mode: Optional[str] = Field(None, description="Output mode used")
    schema_key: Optional[str] = Field(None, description="Schema key if structured")


class JobStatusResponse(BaseSchema):
    """任务状态响应"""
    job_id: str
    status: str
    progress: int
    progress_message: str
    result: Optional[str] = None
    structured_result: Optional[StructuredResult] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    ticker: Optional[str] = None
    crew_name: Optional[str] = None

    # v3 扩展字段
    events: List[RunEvent] = Field(default_factory=list, description="运行事件序列")
    summary: Optional[RunSummary] = Field(None, description="执行统计摘要")
    hints: List[str] = Field(default_factory=list, description="针对错误或警告的建议动作")
    task_outputs: List[Dict[str, Any]] = Field(
        default_factory=list, description="TASK_OUTPUT event summaries"
    )


class JobListResponse(BaseSchema):
    """任务列表响应"""
    jobs: List[JobStatusResponse]
    total: int

class ChatMessage(BaseSchema):
    """聊天消息"""
    role: str = Field(..., description="角色: user 或 assistant")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[str] = None

class ChatRequest(BaseSchema):
    """聊天请求"""
    job_id: str = Field(..., description="关联的任务ID")
    message: str = Field(..., description="用户消息")

class ChatResponse(BaseSchema):
    """聊天响应"""
    reply: str
    job_id: str
    chat_history: List[ChatMessage]

class CrewInfo(BaseSchema):
    """Crew 信息"""
    name: str
    description: str
    phases: List[str]
    debate_rounds: int
    optional_analysts: Optional[List[Dict[str, Any]]] = None
    style_config: Optional[Dict[str, Any]] = None

class CrewListResponse(BaseSchema):
    """Crew 列表响应"""
    crews: List[str]
