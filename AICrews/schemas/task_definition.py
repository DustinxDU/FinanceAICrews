"""
TaskDefinition Pydantic Schemas - Centralized API schemas for TaskDefinition.

This module provides the single source of truth for TaskDefinition
request/response schemas, including the output spec fields and
deprecated max_retries alias handling.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class TaskDefinitionBase(BaseModel):
    """Base schema with shared TaskDefinition fields."""

    name: str = Field(..., min_length=1, max_length=200, description="Task name")
    description: str = Field(..., min_length=1, description="Task description with {variables}")
    expected_output: str = Field(..., min_length=1, description="Expected output description")
    agent_definition_id: Optional[int] = Field(default=None, description="Bound agent ID")
    async_execution: bool = Field(default=False, description="Execute asynchronously")
    context_task_ids: Optional[List[int]] = Field(
        default=None, description="IDs of tasks that provide context"
    )

    # === Task Output Spec ===
    output_mode: str = Field(
        default="raw",
        pattern="^(raw|native_json|native_pydantic|soft_json|soft_pydantic)$",
        description="Output mode: raw, native_json, native_pydantic, soft_json, soft_pydantic",
    )
    output_schema_key: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Registry key for output schema (e.g., 'finance_report_v1')",
    )
    guardrail_keys: List[str] = Field(
        default_factory=list,
        description="List of guardrail keys (e.g., ['non_empty', 'json_parseable'])",
    )
    guardrail_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Max retries on guardrail failure",
    )
    strict_mode: bool = Field(
        default=False,
        description="If True, missing schema/guardrail keys cause errors",
    )

    # Deprecated alias for backward compatibility
    max_retries: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="[DEPRECATED] Use guardrail_max_retries instead",
    )

    @model_validator(mode="after")
    def handle_deprecated_max_retries(self) -> "TaskDefinitionBase":
        """Map deprecated max_retries to guardrail_max_retries if provided."""
        if self.max_retries is not None:
            # Only use max_retries if guardrail_max_retries was not explicitly set
            # (i.e., is still at default value of 3)
            # We check object.__getattribute__ to see raw value
            if self.guardrail_max_retries == 3:  # default
                self.guardrail_max_retries = self.max_retries
            # Clear max_retries so it's not persisted
            self.max_retries = None
        return self


class TaskDefinitionCreate(TaskDefinitionBase):
    """Schema for creating a new TaskDefinition."""

    pass


class TaskDefinitionUpdate(BaseModel):
    """Schema for updating an existing TaskDefinition.

    All fields are optional to support partial updates.
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1)
    expected_output: Optional[str] = Field(default=None, min_length=1)
    agent_definition_id: Optional[int] = None
    async_execution: Optional[bool] = None
    context_task_ids: Optional[List[int]] = None

    # === Task Output Spec ===
    output_mode: Optional[str] = Field(
        default=None,
        pattern="^(raw|native_json|native_pydantic|soft_json|soft_pydantic)$",
    )
    output_schema_key: Optional[str] = Field(default=None, max_length=200)
    guardrail_keys: Optional[List[str]] = None
    guardrail_max_retries: Optional[int] = Field(default=None, ge=0, le=10)
    strict_mode: Optional[bool] = None

    # Deprecated alias
    max_retries: Optional[int] = Field(default=None, ge=0, le=10)

    @model_validator(mode="after")
    def handle_deprecated_max_retries(self) -> "TaskDefinitionUpdate":
        """Map deprecated max_retries to guardrail_max_retries if provided."""
        if self.max_retries is not None and self.guardrail_max_retries is None:
            self.guardrail_max_retries = self.max_retries
            self.max_retries = None
        return self


class TaskDefinitionResponse(BaseModel):
    """Schema for TaskDefinition API responses."""

    id: int
    user_id: Optional[int] = None
    name: str
    description: str
    expected_output: str
    agent_definition_id: Optional[int] = None
    async_execution: bool = False
    context_task_ids: Optional[List[int]] = None

    # === Task Output Spec ===
    output_mode: str = "raw"
    output_schema_key: Optional[str] = None
    guardrail_keys: List[str] = Field(default_factory=list)
    guardrail_max_retries: int = 3
    strict_mode: bool = False

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskDefinitionBrief(BaseModel):
    """Brief schema for task listings (minimal fields)."""

    id: int
    name: str
    description: str
    output_mode: str = "raw"

    model_config = {"from_attributes": True}
