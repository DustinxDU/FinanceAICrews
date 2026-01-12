from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import Field

from AICrews.schemas.common import BaseSchema


class ExecutionGraph(BaseSchema):
    structure: List[Dict[str, Any]] = Field(default_factory=list)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_config: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

