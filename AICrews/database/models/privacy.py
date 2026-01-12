"""
Privacy Domain Models - Data Export and Account Deletion

Implements GDPR-style data portability (export) and right to erasure (deletion).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ExportStatus(str, Enum):
    """Data export job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class DeletionStatus(str, Enum):
    """Account deletion request status."""

    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    PROCESSING = "processing"
    COMPLETED = "completed"


class DataExportJob(Base):
    """Data export job tracking table.

    Tracks user data export requests with status transitions.
    Download URLs expire after a configurable period (default 7 days).
    """

    __tablename__ = "data_export_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    status: Mapped[str] = mapped_column(
        String(20), default=ExportStatus.PENDING.value, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Export manifest (JSON blob with included data types)
    manifest: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Download info (populated when completed)
    download_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    download_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="data_export_jobs")


class AccountDeletionRequest(Base):
    """Account deletion request tracking table.

    Implements 30-day grace period before actual deletion.
    Users can cancel the request during the grace period.
    """

    __tablename__ = "account_deletion_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    status: Mapped[str] = mapped_column(
        String(20), default=DeletionStatus.SCHEDULED.value, index=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Grace period
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, index=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="deletion_requests")


__all__ = [
    "ExportStatus",
    "DeletionStatus",
    "DataExportJob",
    "AccountDeletionRequest",
]
