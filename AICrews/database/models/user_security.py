"""User Security Model - 2FA and security settings"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class UserSecurity(Base):
    """User security settings and 2FA configuration"""
    __tablename__ = "user_security"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    totp_secret_encrypted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    backup_codes_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="security")


__all__ = ["UserSecurity"]
