"""User preferences endpoints.

Unified preferences management including:
- General preferences (theme, locale, timezone)
- Notification preferences (push, email, in-app)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.security import get_current_user, get_db
from AICrews.database.models import User
from AICrews.database.models.preferences import UserPreferences
from AICrews.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate
from AICrews.schemas.user_preferences import (
    UserNotificationPreferencesRequest,
    UserNotificationPreferencesResponse,
)
from AICrews.services.user_notification_service import UserNotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preferences", tags=["Preferences"])


# ============================================
# General Preferences
# ============================================


@router.get("/general", response_model=UserPreferencesResponse)
def get_general_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreferencesResponse:
    """Get general preferences (theme, locale, timezone) for the authenticated user."""
    try:
        prefs = (
            db.query(UserPreferences)
            .filter(UserPreferences.user_id == current_user.id)
            .first()
        )
        if not prefs:
            prefs = UserPreferences(user_id=current_user.id)
            db.add(prefs)
            db.commit()
            db.refresh(prefs)

        return UserPreferencesResponse.model_validate(prefs)
    except Exception:
        logger.exception("Failed to load preferences for user %s", current_user.id)
        raise HTTPException(status_code=500, detail="Failed to load preferences")


@router.put("/general", response_model=UserPreferencesResponse)
def update_general_preferences(
    request: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreferencesResponse:
    """Update general preferences (theme, locale, timezone) for the authenticated user."""
    try:
        prefs = (
            db.query(UserPreferences)
            .filter(UserPreferences.user_id == current_user.id)
            .first()
        )
        if not prefs:
            prefs = UserPreferences(user_id=current_user.id)
            db.add(prefs)

        if request.theme is not None:
            prefs.theme = request.theme
        if request.locale is not None:
            prefs.locale = request.locale
        if request.timezone is not None:
            prefs.timezone = request.timezone

        db.commit()
        db.refresh(prefs)
        return UserPreferencesResponse.model_validate(prefs)
    except Exception:
        logger.exception("Failed to update preferences for user %s", current_user.id)
        raise HTTPException(status_code=500, detail="Failed to update preferences")


# ============================================
# Notification Preferences
# ============================================


@router.get("/notifications", response_model=UserNotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserNotificationPreferencesResponse:
    """Get current user's notification preferences."""
    try:
        service = UserNotificationService(db)
        return service.get_preferences(current_user.id)
    except Exception:
        logger.exception(f"Failed to get notification preferences for user {current_user.id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve notification preferences"
        )


@router.put("/notifications", response_model=UserNotificationPreferencesResponse)
async def update_notification_preferences(
    request: UserNotificationPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserNotificationPreferencesResponse:
    """Update current user's notification preferences."""
    try:
        service = UserNotificationService(db)
        return service.update_preferences(current_user.id, request)
    except Exception:
        logger.exception(f"Failed to update notification preferences for user {current_user.id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update notification preferences"
        )


@router.delete("/notifications/push-subscription", response_model=UserNotificationPreferencesResponse)
async def unsubscribe_push_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserNotificationPreferencesResponse:
    """Remove push notification subscription."""
    try:
        service = UserNotificationService(db)
        return service.unsubscribe_push(current_user.id)
    except Exception:
        logger.exception(f"Failed to unsubscribe push for user {current_user.id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to unsubscribe from push notifications"
        )

