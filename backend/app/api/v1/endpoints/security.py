"""
Security API - 2FA, sessions, and login history endpoints
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from backend.app.security import get_current_user, get_db
from AICrews.database.models.user import User
from AICrews.services.security_service import TwoFactorAuthService, SessionService
from AICrews.schemas.security import (
    Setup2FARequest,
    Verify2FASetupRequest,
    Disable2FARequest,
    RevokeSessionRequest,
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    SessionsResponse,
    LoginSessionResponse,
    LoginHistoryResponse,
    LoginHistoryItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["Security"])


def get_2fa_service(db: Session = Depends(get_db)) -> TwoFactorAuthService:
    return TwoFactorAuthService(db)


def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    return SessionService(db)


def extract_token_from_request(request: Request) -> str | None:
    """
    Extract JWT token from Authorization header

    Args:
        request: FastAPI Request object

    Returns:
        Token string or None
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    # Format: "Bearer <token>"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


# ============================================================================
# 2FA Endpoints
# ============================================================================

@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_user),
    service: TwoFactorAuthService = Depends(get_2fa_service)
) -> TwoFactorStatusResponse:
    """
    Get current 2FA status

    Returns whether 2FA is enabled, the method used, and backup codes remaining.
    """
    return service.get_2fa_status(current_user.id)


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    request: Setup2FARequest,
    current_user: User = Depends(get_current_user),
    service: TwoFactorAuthService = Depends(get_2fa_service)
) -> TwoFactorSetupResponse:
    """
    Start 2FA setup

    Generates:
    - TOTP secret
    - QR code for authenticator app
    - 10 backup recovery codes

    Note: Does NOT enable 2FA until verified with /2fa/verify
    """
    try:
        # Currently only TOTP is supported
        if request.method != "totp":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only TOTP method is supported"
            )

        return service.setup_totp(current_user.id, app_name="FinanceAICrews")
    except HTTPException:
        # Pass through explicit HTTP errors
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"2FA setup failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup 2FA"
        )


@router.post("/2fa/verify", response_model=TwoFactorStatusResponse)
async def verify_2fa(
    request: Verify2FASetupRequest,
    current_user: User = Depends(get_current_user),
    service: TwoFactorAuthService = Depends(get_2fa_service)
) -> TwoFactorStatusResponse:
    """
    Verify TOTP code and enable 2FA

    After successful verification, 2FA will be required for future logins.
    """
    try:
        return service.verify_and_enable_totp(current_user.id, request.code)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"2FA verification failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify 2FA"
        )


@router.post("/2fa/disable", response_model=TwoFactorStatusResponse)
async def disable_2fa(
    request: Disable2FARequest,
    current_user: User = Depends(get_current_user),
    service: TwoFactorAuthService = Depends(get_2fa_service)
) -> TwoFactorStatusResponse:
    """
    Disable 2FA

    Requires:
    - Current password
    - Current TOTP code or backup code

    This is a sensitive operation requiring re-authentication.
    """
    try:
        return service.disable_totp(current_user.id, request.password, request.code)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"2FA disable failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA"
        )


# ============================================================================
# Session Management Endpoints
# ============================================================================

@router.get("/sessions", response_model=SessionsResponse)
async def get_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service)
) -> SessionsResponse:
    """
    Get all active sessions

    Returns list of all non-revoked sessions with device info, IP, location, etc.
    The current session is marked with is_current=True.
    """
    # Get current token from request
    current_token = extract_token_from_request(request)

    sessions = service.get_active_sessions(current_user.id, current_token)

    # Convert to response format
    session_responses = []
    for session in sessions:
        session_responses.append(
            LoginSessionResponse(
                id=session.id,
                device_info=session.device_info or "Unknown device",
                ip_address=session.ip_address or "Unknown IP",
                location=session.location,
                is_current=(session.token == current_token) if current_token else False,
                created_at=session.created_at,
                last_active=session.last_active,
                expires_at=session.expires_at
            )
        )

    return SessionsResponse(
        sessions=session_responses,
        total=len(session_responses)
    )


@router.post("/sessions/revoke")
async def revoke_session(
    request: RevokeSessionRequest,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    Revoke a specific session

    The session will be immediately invalid and cannot be used for API access.
    """
    try:
        success = service.revoke_session(request.session_id, user_id=current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        # Audit log
        service.create_login_event(
            user_id=current_user.id,
            event_type="session_revoked",
            status="success",
            device_info=None,
            ip_address=None,
            location=None,
            failure_reason=None,
        )

        return {
            "success": True,
            "message": "Session revoked successfully"
        }
    except HTTPException:
        # pass through
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Session revocation failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session"
        )


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service)
) -> Dict[str, Any]:
    """
    Revoke all other sessions (keep current)

    Useful for:
    - Logging out from all other devices
    - Security response to suspicious activity

    The current session will remain active.
    """
    try:
        # Get current token to exclude from revocation
        current_token = extract_token_from_request(request)

        count = service.revoke_all_sessions(current_user.id, except_token=current_token)

        # Audit log
        service.create_login_event(
            user_id=current_user.id,
            event_type="sessions_revoked_all",
            status="success",
            device_info=None,
            ip_address=None,
            location=None,
            failure_reason=None,
        )

        return {
            "success": True,
            "revoked_count": count
        }
    except Exception as e:
        logger.error(f"Revoke all sessions failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions"
        )


# ============================================================================
# Login History Endpoint
# ============================================================================

@router.get("/login-history", response_model=LoginHistoryResponse)
async def get_login_history(
    limit: int = Query(30, ge=1, le=100, description="Number of events to return"),
    current_user: User = Depends(get_current_user),
    service: SessionService = Depends(get_session_service)
) -> LoginHistoryResponse:
    """
    Get login history

    Returns recent login events (successful, failed, 2FA failures, etc.)
    for security audit and suspicious activity detection.
    """
    try:
        events = service.get_login_history(current_user.id, limit=limit)

        history_items = [
            LoginHistoryItem(
                id=event.id,
                timestamp=event.created_at,
                device_info=event.device_info or "Unknown device",
                ip_address=event.ip_address or "Unknown IP",
                location=event.location,
                status=event.status,
                failure_reason=event.failure_reason
            )
            for event in events
        ]

        return LoginHistoryResponse(
            history=history_items,
            total=len(history_items)
        )
    except Exception as e:
        logger.error(f"Get login history failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get login history"
        )
