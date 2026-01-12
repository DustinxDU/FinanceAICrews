"""
Privacy API Routes - Data Export and Account Deletion

Provides GDPR-style privacy controls:
- Data export (portability)
- Account deletion (right to erasure)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.security import get_current_user, get_db
from AICrews.database.models import User
from AICrews.schemas.privacy import (
    DataExportRequest,
    DataExportJobResponse,
    DataExportListResponse,
    AccountDeletionRequest,
    AccountDeletionResponse,
    PrivacyStatusResponse,
)
from AICrews.schemas.common import ErrorResponse
from AICrews.services.privacy_service import PrivacyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/privacy", tags=["Privacy"])


def get_privacy_service(db: Session = Depends(get_db)) -> PrivacyService:
    """Dependency to get PrivacyService instance."""
    return PrivacyService(db)


# ============================================
# Privacy Status
# ============================================


@router.get(
    "/status",
    response_model=PrivacyStatusResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Get privacy status",
    description="Get overall privacy status including pending exports and deletion requests",
)
async def get_privacy_status(
    current_user: User = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
) -> PrivacyStatusResponse:
    """Get privacy status for the authenticated user."""
    try:
        return service.get_privacy_status(current_user.id)
    except Exception as e:
        logger.exception("Failed to get privacy status for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get privacy status",
        )


# ============================================
# Data Export Endpoints
# ============================================


@router.post(
    "/export",
    response_model=DataExportJobResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Request data export",
    description="Request a new data export. Returns a job that can be tracked.",
)
async def request_export(
    request: DataExportRequest,
    current_user: User = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
) -> DataExportJobResponse:
    """Request a new data export for the authenticated user."""
    try:
        return service.request_export(current_user.id, request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Failed to request export for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request data export",
        )


@router.get(
    "/export",
    response_model=DataExportListResponse,
    responses={401: {"model": ErrorResponse}},
    summary="List export jobs",
    description="List all data export jobs for the authenticated user",
)
async def list_export_jobs(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
) -> DataExportListResponse:
    """List export jobs for the authenticated user."""
    try:
        return service.list_export_jobs(current_user.id, limit=limit)
    except Exception as e:
        logger.exception("Failed to list exports for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list export jobs",
        )


@router.get(
    "/export/{job_id}",
    response_model=DataExportJobResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    summary="Get export job",
    description="Get details of a specific export job",
)
async def get_export_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
) -> DataExportJobResponse:
    """Get a specific export job for the authenticated user."""
    try:
        job = service.get_export_job(current_user.id, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found",
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get export job %s for user %s", job_id, current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get export job",
        )


# ============================================
# Account Deletion Endpoints
# ============================================


@router.post(
    "/deletion",
    response_model=AccountDeletionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Request account deletion",
    description="Schedule account deletion with 30-day grace period",
)
async def request_deletion(
    request: AccountDeletionRequest,
    current_user: User = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
) -> AccountDeletionResponse:
    """Schedule account deletion for the authenticated user."""
    try:
        return service.request_deletion(current_user.id, request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Failed to request deletion for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request account deletion",
        )


@router.get(
    "/deletion",
    response_model=AccountDeletionResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    summary="Get deletion status",
    description="Get current account deletion request status",
)
async def get_deletion_status(
    current_user: User = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
) -> AccountDeletionResponse:
    """Get deletion status for the authenticated user."""
    try:
        result = service.get_deletion_status(current_user.id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No deletion request found",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get deletion status for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get deletion status",
        )


@router.delete(
    "/deletion",
    response_model=AccountDeletionResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    summary="Cancel account deletion",
    description="Cancel a scheduled account deletion during the grace period",
)
async def cancel_deletion(
    current_user: User = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
) -> AccountDeletionResponse:
    """Cancel scheduled deletion for the authenticated user."""
    try:
        result = service.cancel_deletion(current_user.id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No scheduled deletion to cancel",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to cancel deletion for user %s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel account deletion",
        )
