"""
Privacy Service - Data Export and Account Deletion

Implements GDPR-style data portability (export) and right to erasure (deletion).
"""

import json
from AICrews.observability.logging import get_logger
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from AICrews.database.models.privacy import (
    DataExportJob,
    AccountDeletionRequest,
    ExportStatus,
    DeletionStatus,
)
from AICrews.schemas.privacy import (
    DataExportRequest,
    DataExportJobResponse,
    DataExportListResponse,
    AccountDeletionRequest as AccountDeletionRequestSchema,
    AccountDeletionResponse,
    PrivacyStatusResponse,
)

logger = get_logger(__name__)

# Grace period before account deletion (days)
DELETION_GRACE_PERIOD_DAYS = 30

# Export download URL expiry (days)
EXPORT_DOWNLOAD_EXPIRY_DAYS = 7


class PrivacyService:
    """Service for privacy-related operations."""

    def __init__(self, db: Session):
        self.db = db

    # ============================================
    # Data Export Operations
    # ============================================

    def request_export(
        self, user_id: int, request: DataExportRequest
    ) -> DataExportJobResponse:
        """
        Request a new data export.

        Creates a pending export job. In production, this would trigger
        a background job to generate the export file.
        """
        # Check for existing pending/processing export
        existing = self.db.execute(
            select(DataExportJob).where(
                DataExportJob.user_id == user_id,
                DataExportJob.status.in_([
                    ExportStatus.PENDING.value,
                    ExportStatus.PROCESSING.value,
                ]),
            )
        ).scalar_one_or_none()

        if existing:
            raise ValueError(
                "An export is already in progress. Please wait for it to complete."
            )

        # Create manifest from request
        manifest = json.dumps({
            "include_analysis_reports": request.include_analysis_reports,
            "include_portfolios": request.include_portfolios,
            "include_settings": request.include_settings,
        })

        job = DataExportJob(
            user_id=user_id,
            status=ExportStatus.PENDING.value,
            manifest=manifest,
            requested_at=datetime.now(),
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info("Data export requested for user %s, job_id=%s", user_id, job.id)

        return DataExportJobResponse.model_validate(job)

    def get_export_job(self, user_id: int, job_id: int) -> Optional[DataExportJobResponse]:
        """Get a specific export job for a user."""
        job = self.db.execute(
            select(DataExportJob).where(
                DataExportJob.id == job_id,
                DataExportJob.user_id == user_id,
            )
        ).scalar_one_or_none()

        if not job:
            return None

        return DataExportJobResponse.model_validate(job)

    def list_export_jobs(self, user_id: int, limit: int = 10) -> DataExportListResponse:
        """List export jobs for a user, most recent first."""
        jobs = self.db.execute(
            select(DataExportJob)
            .where(DataExportJob.user_id == user_id)
            .order_by(DataExportJob.requested_at.desc())
            .limit(limit)
        ).scalars().all()

        total = self.db.execute(
            select(DataExportJob).where(DataExportJob.user_id == user_id)
        ).scalars().all()

        return DataExportListResponse(
            jobs=[DataExportJobResponse.model_validate(j) for j in jobs],
            total=len(total),
        )

    # ============================================
    # Account Deletion Operations
    # ============================================

    def request_deletion(
        self, user_id: int, request: AccountDeletionRequestSchema
    ) -> AccountDeletionResponse:
        """
        Schedule account deletion with grace period.

        The account will be marked for deletion after DELETION_GRACE_PERIOD_DAYS.
        User can cancel during this period.
        """
        if not request.confirm:
            raise ValueError("Deletion must be confirmed by setting confirm=True")

        # Check for existing scheduled deletion
        existing = self.db.execute(
            select(AccountDeletionRequest).where(
                AccountDeletionRequest.user_id == user_id,
                AccountDeletionRequest.status == DeletionStatus.SCHEDULED.value,
            )
        ).scalar_one_or_none()

        if existing:
            raise ValueError(
                "Account deletion is already scheduled. "
                "Cancel the existing request to create a new one."
            )

        scheduled_for = datetime.now() + timedelta(days=DELETION_GRACE_PERIOD_DAYS)

        deletion_request = AccountDeletionRequest(
            user_id=user_id,
            status=DeletionStatus.SCHEDULED.value,
            reason=request.reason,
            scheduled_for=scheduled_for,
            requested_at=datetime.now(),
        )
        self.db.add(deletion_request)
        self.db.commit()
        self.db.refresh(deletion_request)

        logger.info(
            "Account deletion scheduled for user %s, scheduled_for=%s",
            user_id,
            scheduled_for,
        )

        return self._to_deletion_response(deletion_request)

    def cancel_deletion(self, user_id: int) -> Optional[AccountDeletionResponse]:
        """Cancel a scheduled account deletion."""
        deletion_request = self.db.execute(
            select(AccountDeletionRequest).where(
                AccountDeletionRequest.user_id == user_id,
                AccountDeletionRequest.status == DeletionStatus.SCHEDULED.value,
            )
        ).scalar_one_or_none()

        if not deletion_request:
            return None

        deletion_request.status = DeletionStatus.CANCELLED.value
        deletion_request.cancelled_at = datetime.now()
        self.db.commit()
        self.db.refresh(deletion_request)

        logger.info("Account deletion cancelled for user %s", user_id)

        return self._to_deletion_response(deletion_request)

    def get_deletion_status(self, user_id: int) -> Optional[AccountDeletionResponse]:
        """Get the current deletion request status for a user."""
        deletion_request = self.db.execute(
            select(AccountDeletionRequest)
            .where(AccountDeletionRequest.user_id == user_id)
            .order_by(AccountDeletionRequest.requested_at.desc())
        ).scalar_one_or_none()

        if not deletion_request:
            return None

        return self._to_deletion_response(deletion_request)

    # ============================================
    # Privacy Status
    # ============================================

    def get_privacy_status(self, user_id: int) -> PrivacyStatusResponse:
        """Get overall privacy status for a user."""
        # Check for pending exports
        pending_export = self.db.execute(
            select(DataExportJob).where(
                DataExportJob.user_id == user_id,
                DataExportJob.status.in_([
                    ExportStatus.PENDING.value,
                    ExportStatus.PROCESSING.value,
                ]),
            )
        ).scalar_one_or_none()

        # Get last completed export
        last_export = self.db.execute(
            select(DataExportJob)
            .where(
                DataExportJob.user_id == user_id,
                DataExportJob.status == ExportStatus.COMPLETED.value,
            )
            .order_by(DataExportJob.completed_at.desc())
        ).scalar_one_or_none()

        # Check for scheduled deletion
        scheduled_deletion = self.db.execute(
            select(AccountDeletionRequest).where(
                AccountDeletionRequest.user_id == user_id,
                AccountDeletionRequest.status == DeletionStatus.SCHEDULED.value,
            )
        ).scalar_one_or_none()

        deletion_days_remaining = None
        if scheduled_deletion:
            delta = scheduled_deletion.scheduled_for - datetime.now()
            deletion_days_remaining = max(0, delta.days)

        return PrivacyStatusResponse(
            has_pending_export=pending_export is not None,
            has_scheduled_deletion=scheduled_deletion is not None,
            deletion_scheduled_for=(
                scheduled_deletion.scheduled_for if scheduled_deletion else None
            ),
            deletion_days_remaining=deletion_days_remaining,
            last_export_at=last_export.completed_at if last_export else None,
        )

    # ============================================
    # Internal Helpers
    # ============================================

    def _to_deletion_response(
        self, deletion_request: AccountDeletionRequest
    ) -> AccountDeletionResponse:
        """Convert deletion request to response with computed fields."""
        delta = deletion_request.scheduled_for - datetime.now()
        days_remaining = max(0, delta.days)

        return AccountDeletionResponse(
            id=deletion_request.id,
            status=deletion_request.status,
            reason=deletion_request.reason,
            scheduled_for=deletion_request.scheduled_for,
            cancelled_at=deletion_request.cancelled_at,
            completed_at=deletion_request.completed_at,
            requested_at=deletion_request.requested_at,
            days_remaining=days_remaining,
        )


__all__ = ["PrivacyService"]
