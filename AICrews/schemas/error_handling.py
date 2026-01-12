from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field

from AICrews.schemas.common import BaseSchema


class ErrorStrategy(str, Enum):
    STOP = "STOP"
    RETRY = "RETRY"
    CONTINUE = "CONTINUE"
    FALLBACK = "FALLBACK"
    ERROR_OUTPUT = "ERROR_OUTPUT"


class ErrorConfig(BaseSchema):
    strategy: ErrorStrategy = Field(default=ErrorStrategy.STOP)
    max_retries: int = Field(default=0, ge=0)
    retry_delay: float = Field(default=0.0, ge=0.0)
    error_output: Optional[str] = Field(
        default=None, description="Optional fallback text when using ERROR_OUTPUT"
    )

