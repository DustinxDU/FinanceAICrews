"""
Privacy Schemas - Data Export and Account Deletion

Pydantic v2 schemas for privacy-related API operations.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================
# Data Export Schemas
# ============================================


class DataExportRequest(BaseModel):
    """Request to initiate a data export."""

    include_analysis_reports: bool = Field(
        default=True,
        description="Include analysis reports in export",
    )
    include_portfolios: bool = Field(
        default=True,
        description="Include portfolio data in export",
    )
    include_settings: bool = Field(
        default=True,
        description="Include user settings and preferences",
    )

    model_config = {"extra": "forbid"}


class DataExportJobResponse(BaseModel):
    """Response for a data export job."""

    id: int
    status: str
    error_message: Optional[str] = None
    manifest: Optional[str] = None
    download_url: Optional[str] = None
    download_expires_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    requested_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "extra": "forbid"}


class DataExportListResponse(BaseModel):
    """List of data export jobs."""

    jobs: List[DataExportJobResponse]
    total: int

    model_config = {"extra": "forbid"}


# ============================================
# Account Deletion Schemas
# ============================================


class AccountDeletionRequest(BaseModel):
    """Request to schedule account deletion."""

    reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional reason for account deletion",
    )
    confirm: bool = Field(
        ...,
        description="Must be True to confirm deletion request",
    )

    model_config = {"extra": "forbid"}


class AccountDeletionResponse(BaseModel):
    """Response for an account deletion request."""

    id: int
    status: str
    reason: Optional[str] = None
    scheduled_for: datetime
    cancelled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requested_at: datetime
    days_remaining: int = Field(
        description="Days remaining before deletion is executed",
    )

    model_config = {"from_attributes": True, "extra": "forbid"}


class AccountDeletionCancelRequest(BaseModel):
    """Request to cancel a scheduled account deletion."""

    confirm: bool = Field(
        ...,
        description="Must be True to confirm cancellation",
    )

    model_config = {"extra": "forbid"}


# ============================================
# Privacy Status Summary
# ============================================


class PrivacyStatusResponse(BaseModel):
    """Overall privacy status for a user."""

    has_pending_export: bool = Field(
        description="Whether there's a pending/processing export job",
    )
    has_scheduled_deletion: bool = Field(
        description="Whether account deletion is scheduled",
    )
    deletion_scheduled_for: Optional[datetime] = Field(
        default=None,
        description="When the account is scheduled for deletion",
    )
    deletion_days_remaining: Optional[int] = Field(
        default=None,
        description="Days until account deletion",
    )
    last_export_at: Optional[datetime] = Field(
        default=None,
        description="When the last export was completed",
    )

    model_config = {"extra": "forbid"}


__all__ = [
    "DataExportRequest",
    "DataExportJobResponse",
    "DataExportListResponse",
    "AccountDeletionRequest",
    "AccountDeletionResponse",
    "AccountDeletionCancelRequest",
    "PrivacyStatusResponse",
]
