from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from AICrews.schemas.common import BaseSchema


class ExecutionCheckpoint(BaseSchema):
    run_id: str = Field(..., description="Execution run identifier")
    checkpoint_id: str = Field(..., description="Checkpoint identifier")
    data: Dict[str, Any] = Field(default_factory=dict, description="Checkpoint payload")
    created_at: datetime = Field(default_factory=datetime.now)


class TaskStatus(BaseSchema):
    run_id: str = Field(..., description="Execution run identifier")
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Status string (e.g. pending/running/success/failed)")
    detail: Optional[str] = Field(None, description="Optional status detail")
    updated_at: datetime = Field(default_factory=datetime.now)


class ExecutionState(BaseSchema):
    run_id: str = Field(..., description="Execution run identifier")
    data: Dict[str, Any] = Field(default_factory=dict, description="Execution state payload")
    updated_at: datetime = Field(default_factory=datetime.now)

