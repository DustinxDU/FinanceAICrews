"""
Task Output Spec - Platform abstraction for task output contracts.

This module defines the output specification that governs how a Task
produces structured outputs and applies guardrails.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class TaskOutputMode(str, Enum):
    """Task output mode determines how structured output is handled.

    - raw: No structured output; agent returns free-form text.
    - native_json: Use CrewAI's built-in output_json (requires provider support).
    - native_pydantic: Use CrewAI's built-in output_pydantic (requires provider support).
    - soft_json: Don't use native output_*; apply json guardrails instead.
    - soft_pydantic: Don't use native output_*; apply pydantic validation guardrails.
    """

    RAW = "raw"
    NATIVE_JSON = "native_json"
    NATIVE_PYDANTIC = "native_pydantic"
    SOFT_JSON = "soft_json"
    SOFT_PYDANTIC = "soft_pydantic"

    @classmethod
    def requires_schema(cls, mode: "TaskOutputMode") -> bool:
        """Check if the mode requires a schema key."""
        return mode != cls.RAW

    @classmethod
    def is_native(cls, mode: "TaskOutputMode") -> bool:
        """Check if the mode uses CrewAI native structured output."""
        return mode in (cls.NATIVE_JSON, cls.NATIVE_PYDANTIC)

    @classmethod
    def is_soft(cls, mode: "TaskOutputMode") -> bool:
        """Check if the mode uses guardrail-based (soft) structured output."""
        return mode in (cls.SOFT_JSON, cls.SOFT_PYDANTIC)


class TaskOutputSpec(BaseModel):
    """Platform abstraction for Task output contract.

    This spec is compiled from TaskDefinition database rows and used by
    the task runtime builder to inject appropriate CrewAI Task kwargs.
    """

    output_mode: TaskOutputMode = Field(
        default=TaskOutputMode.RAW,
        description="Output mode: raw, native_json, native_pydantic, soft_json, soft_pydantic",
    )
    output_schema_key: Optional[str] = Field(
        default=None,
        description="Registry key for the output schema (e.g., 'finance_report_v1')",
    )
    guardrail_keys: List[str] = Field(
        default_factory=list,
        description="List of guardrail keys to apply (e.g., ['non_empty', 'json_parseable'])",
    )
    guardrail_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Max retries on guardrail failure",
    )
    strict_mode: bool = Field(
        default=False,
        description="If True, missing schema/guardrail keys cause errors; else warnings",
    )

    @model_validator(mode="after")
    def validate_schema_required(self) -> "TaskOutputSpec":
        """Validate that schema_key is provided when output_mode requires it."""
        if TaskOutputMode.requires_schema(self.output_mode) and not self.output_schema_key:
            if self.strict_mode:
                raise ValueError(
                    f"output_schema_key is required for output_mode={self.output_mode.value}"
                )
            # In non-strict mode, we'll log a warning at runtime and fall back to raw
        return self

    @classmethod
    def from_task_definition(cls, task_def) -> "TaskOutputSpec":
        """Create TaskOutputSpec from a TaskDefinition database row.

        Args:
            task_def: TaskDefinition SQLAlchemy model instance

        Returns:
            TaskOutputSpec instance
        """
        return cls(
            output_mode=TaskOutputMode(getattr(task_def, "output_mode", "raw") or "raw"),
            output_schema_key=getattr(task_def, "output_schema_key", None),
            guardrail_keys=getattr(task_def, "guardrail_keys", []) or [],
            guardrail_max_retries=getattr(task_def, "guardrail_max_retries", 3) or 3,
            strict_mode=getattr(task_def, "strict_mode", False) or False,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "TaskOutputSpec":
        """Create TaskOutputSpec from a dictionary (e.g., compiled_data).

        Args:
            data: Dictionary with output spec fields

        Returns:
            TaskOutputSpec instance
        """
        return cls(
            output_mode=TaskOutputMode(data.get("output_mode", "raw") or "raw"),
            output_schema_key=data.get("output_schema_key"),
            guardrail_keys=data.get("guardrail_keys", []) or [],
            guardrail_max_retries=data.get("guardrail_max_retries", 3) or 3,
            strict_mode=data.get("strict_mode", False) or False,
        )

    def to_compiled_dict(self) -> dict:
        """Export to a dictionary for storage in compiled_data.

        Returns:
            Dictionary representation suitable for JSON storage
        """
        return {
            "output_mode": self.output_mode.value,
            "output_schema_key": self.output_schema_key,
            "guardrail_keys": self.guardrail_keys,
            "guardrail_max_retries": self.guardrail_max_retries,
            "strict_mode": self.strict_mode,
        }
