"""
Security Domain Models - 安全领域模型

包含 2FA、会话管理和登录审计模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, Boolean, JSON, DateTime, Index
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserSecurity(Base):
    """用户安全设置表 - 2FA 和备份码管理

    TODO: 加密 totp_secret 和 backup_codes (使用 Fernet 或类似方案)
    当前为 MVP，明文存储，将在安全加固阶段实现加密。
    """
    __tablename__ = "user_security"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # 2FA TOTP Settings
    totp_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # TODO: Encrypt
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Backup Codes
    backup_codes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # TODO: Encrypt, list of str
    backup_codes_used: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # List of used backup codes

    # Phone Verification (for SMS 2FA - future)
    phone_number_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="security")


class LoginSession(Base):
    """登录会话表 - 活跃会话管理和设备跟踪

    每次成功登录创建一个会话记录。用于：
    - 设备管理（查看所有登录设备）
    - 会话撤销（远程登出）
    - 活跃度跟踪（last_active 更新）
    """
    __tablename__ = "login_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Session Token (JWT or session ID)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Device Information
    device_info: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # e.g., "Chrome 120 on macOS"
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # e.g., "San Francisco, CA, US"

    # Session State
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="login_sessions")


class LoginEvent(Base):
    """登录事件表 - 登录审计日志

    记录所有登录尝试（成功/失败），用于：
    - 安全审计（查看登录历史）
    - 异常检测（多次失败尝试）
    - 合规报告（访问日志）
    """
    __tablename__ = "login_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Event Details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # login_success, login_failed, 2fa_failed, password_reset, etc.
    device_info: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Status and Failure Info
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # success, failed, suspicious
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # wrong password, invalid 2FA, account locked, etc.

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="login_events")


__all__ = [
    "UserSecurity",
    "LoginSession",
    "LoginEvent",
]
