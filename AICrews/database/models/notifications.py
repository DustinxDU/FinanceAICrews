"""
Notification Domain Models - 通知领域模型

包含用户 Webhook 设置模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserWebhookSettings(Base):
    """用户 Webhook 设置表"""
    __tablename__ = "user_webhook_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    webhook_url: Mapped[str] = mapped_column(String(500))
    shared_secret_encrypted: Mapped[str] = mapped_column(Text)

    last_status: Mapped[str] = mapped_column(String(20), default="never", index=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_delivery_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="webhook_settings")


__all__ = [
    "UserWebhookSettings",
]
