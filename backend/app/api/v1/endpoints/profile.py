"""
Profile API Routes - User profile management endpoints

Provides GET/PUT endpoints for user profile management.
Business logic is in AICrews.services.user_service.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from AICrews.schemas.profile import (
    ProfileUpdateRequest,
    ProfileResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
)
from AICrews.schemas.common import ErrorResponse
from AICrews.services.user_service import UserService
from backend.app.security import get_db, get_current_user
from AICrews.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["Profile"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance"""
    return UserService(db)


# ============================================
# Profile Management Endpoints
# ============================================

@router.get(
    "",
    response_model=ProfileResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Get current user profile",
    description="Retrieve the current authenticated user's profile information",
)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user profile

    Requires authentication via Bearer token:
    `Authorization: Bearer <token>`

    Returns:
        ProfileResponse: Complete user profile including:
        - Basic info (id, email, username)
        - Profile fields (full_name, avatar_url, phone_number)
        - Email verification status (email_verified, pending_email)
        - Account metadata (subscription_level, is_active, timestamps)
        - Security indicators (last_password_change)
    """
    return ProfileResponse.model_validate(current_user)


@router.put(
    "",
    response_model=ProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse}
    },
    summary="Update user profile",
    description="Update the current authenticated user's profile information",
)
async def update_profile(
    update_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """
    Update user profile

    **Field Update Rules**:
    - **Non-sensitive fields** (full_name, avatar_url): Can update WITHOUT password
    - **Sensitive fields** (email, phone_number, new_password): REQUIRES current_password

    **Email Change Flow**:
    1. Provide new email + current_password
    2. Email is set to `pending_email` (not `email`)
    3. Verification email is sent (future implementation)
    4. After verification, `pending_email` → `email`

    **Password Change Flow**:
    1. Provide current_password + new_password
    2. Password is validated and hashed
    3. `last_password_change` timestamp is updated

    Args:
        update_data: Profile update request (see ProfileUpdateRequest schema)
        current_user: Authenticated user (injected by dependency)
        service: UserService instance (injected by dependency)

    Returns:
        ProfileResponse: Updated user profile

    Raises:
        HTTPException 400:
            - Missing current_password for sensitive fields
            - Invalid current_password
            - Email already exists
        HTTPException 401: Unauthenticated request
        HTTPException 422: Validation errors (invalid phone, avatar URL, etc.)
    """
    try:
        # Call service layer to update profile
        updated_user = service.update_user_profile(current_user.id, update_data)

        logger.info(f"Profile updated for user {current_user.id}")

        return ProfileResponse.model_validate(updated_user)

    except ValueError as e:
        # Service layer raises ValueError for business logic errors:
        # - Missing/wrong password
        # - Duplicate email
        # - User not found
        error_msg = str(e)
        logger.warning(f"Profile update failed for user {current_user.id}: {error_msg}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error updating profile for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.post(
    "/verify-email",
    response_model=EmailVerificationResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Verify pending email change",
    description="Verify a pending email change using a verification token",
)
async def verify_email(
    request: EmailVerificationRequest,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Verify pending email change for the current user."""
    try:
        result = service.verify_email_change(current_user.id, request.token)
        logger.info("Email verified for user %s", current_user.id)
        return result
    except ValueError as e:
        error_msg = str(e)
        logger.warning("Email verification failed for user %s: %s", current_user.id, error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    except Exception as e:
        logger.error("Unexpected error verifying email for user %s: %s", current_user.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        )
