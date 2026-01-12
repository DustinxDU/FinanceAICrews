"""
User Preferences Domain Models - 用户偏好设置模型

包含用户通知偏好设置模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, DateTime, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserNotificationPreferences(Base):
    """用户通知偏好设置表"""
    __tablename__ = "user_notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    # Master toggle
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Event-specific toggles
    analysis_completion: Mapped[bool] = mapped_column(Boolean, default=True)
    system_updates: Mapped[bool] = mapped_column(Boolean, default=True)

    # Browser push subscription data (Web Push API)
    push_subscription_endpoint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    push_subscription_p256dh: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    push_subscription_auth: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="notification_preferences")


__all__ = [
    "UserNotificationPreferences",
]
