"""
User Notification Service - 用户通知服务

Manages user notification preferences and Web Push subscriptions.
"""

from AICrews.observability.logging import get_logger
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from AICrews.database.models.user_preferences import UserNotificationPreferences
from AICrews.schemas.user_preferences import (
    UserNotificationPreferencesRequest,
    UserNotificationPreferencesResponse,
    PushSubscriptionData,
)

logger = get_logger(__name__)


class UserNotificationService:
    """Service for managing user notification preferences"""

    def __init__(self, db: Session):
        self.db = db

    def get_preferences(self, user_id: int) -> UserNotificationPreferencesResponse:
        """
        Get user notification preferences.
        Creates default preferences if none exist.

        Args:
            user_id: User ID

        Returns:
            UserNotificationPreferencesResponse
        """
        # Try to fetch existing preferences
        stmt = select(UserNotificationPreferences).where(
            UserNotificationPreferences.user_id == user_id
        )
        result = self.db.execute(stmt)
        prefs = result.scalar_one_or_none()

        # Create default preferences if none exist
        if not prefs:
            prefs = UserNotificationPreferences(
                user_id=user_id,
                enabled=False,
                analysis_completion=True,
                system_updates=True,
            )
            self.db.add(prefs)
            self.db.commit()
            self.db.refresh(prefs)
            logger.info(f"Created default notification preferences for user {user_id}")

        return UserNotificationPreferencesResponse.from_orm(prefs)

    def update_preferences(
        self,
        user_id: int,
        request: UserNotificationPreferencesRequest
    ) -> UserNotificationPreferencesResponse:
        """
        Update user notification preferences.

        Args:
            user_id: User ID
            request: Update request with new preferences

        Returns:
            Updated preferences
        """
        # Fetch or create preferences
        stmt = select(UserNotificationPreferences).where(
            UserNotificationPreferences.user_id == user_id
        )
        result = self.db.execute(stmt)
        prefs = result.scalar_one_or_none()

        if not prefs:
            prefs = UserNotificationPreferences(user_id=user_id)
            self.db.add(prefs)

        # Update preferences
        prefs.enabled = request.enabled
        prefs.analysis_completion = request.analysis_completion
        prefs.system_updates = request.system_updates

        # Update push subscription if provided
        if request.push_subscription:
            prefs.push_subscription_endpoint = request.push_subscription.endpoint
            prefs.push_subscription_p256dh = request.push_subscription.keys.p256dh
            prefs.push_subscription_auth = request.push_subscription.keys.auth
            logger.info(f"Updated push subscription for user {user_id}")

        self.db.commit()
        self.db.refresh(prefs)
        logger.info(f"Updated notification preferences for user {user_id}")

        return UserNotificationPreferencesResponse.from_orm(prefs)

    def unsubscribe_push(self, user_id: int) -> UserNotificationPreferencesResponse:
        """
        Remove push subscription for user.

        Args:
            user_id: User ID

        Returns:
            Updated preferences
        """
        stmt = select(UserNotificationPreferences).where(
            UserNotificationPreferences.user_id == user_id
        )
        result = self.db.execute(stmt)
        prefs = result.scalar_one_or_none()

        if prefs:
            prefs.push_subscription_endpoint = None
            prefs.push_subscription_p256dh = None
            prefs.push_subscription_auth = None
            self.db.commit()
            self.db.refresh(prefs)
            logger.info(f"Removed push subscription for user {user_id}")

        return self.get_preferences(user_id)


__all__ = ["UserNotificationService"]
