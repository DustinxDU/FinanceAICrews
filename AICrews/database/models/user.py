"""
User Domain Models - 用户领域模型

包含用户、投资组合、凭证等用户相关模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Integer, Text, Boolean, Float, JSON, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))

    # NEW FIELDS for v2.0.0 Profile Support
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    pending_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_password_change: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    subscription_level: Mapped[str] = mapped_column(String(20), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 历史遗留配置 (建议逐渐迁移到 UserCredential)
    env_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 用户偏好设置
    default_llm_config_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # deprecated, use default_model_config_id
    default_model_config_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # UserModelConfig.id for precise model selection
    tools_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # BYOK 全局开关 - 付费用户可选择使用自己的 API Key 还是官方模型
    use_own_llm_keys: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 关联
    portfolios: Mapped[List["UserPortfolio"]] = relationship("UserPortfolio", back_populates="user", foreign_keys="UserPortfolio.user_id")
    credentials: Mapped[List["UserCredential"]] = relationship("UserCredential", back_populates="user", cascade="all, delete-orphan")
    uploads: Mapped[List["UserUpload"]] = relationship("UserUpload", back_populates="user", cascade="all, delete-orphan")
    cockpit_indicators: Mapped[List["UserCockpitIndicator"]] = relationship("UserCockpitIndicator", back_populates="user", cascade="all, delete-orphan")
    asset_cache: Mapped[List["UserAssetCache"]] = relationship("UserAssetCache", back_populates="user", cascade="all, delete-orphan")
    strategies: Mapped[List["UserStrategy"]] = relationship("UserStrategy", back_populates="user", cascade="all, delete-orphan")
    # Billing relationships
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription", back_populates="user", uselist=False)
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="user")

    # Security relationships
    security: Mapped[Optional["UserSecurity"]] = relationship(
        "UserSecurity",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    login_sessions: Mapped[List["LoginSession"]] = relationship(
        "LoginSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    login_events: Mapped[List["LoginEvent"]] = relationship(
        "LoginEvent",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Notifications relationships
    webhook_settings: Mapped[Optional["UserWebhookSettings"]] = relationship(
        "UserWebhookSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    notification_preferences: Mapped[Optional["UserNotificationPreferences"]] = relationship(
        "UserNotificationPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Privacy relationships
    data_export_jobs: Mapped[List["DataExportJob"]] = relationship(
        "DataExportJob",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    deletion_requests: Mapped[List["AccountDeletionRequest"]] = relationship(
        "AccountDeletionRequest",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserPortfolio(Base):
    """用户投资组合关系表"""
    __tablename__ = 'user_portfolios'
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("assets.ticker"), primary_key=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="portfolios", foreign_keys=[user_id])
    asset: Mapped["Asset"] = relationship("Asset", back_populates="portfolios")


class UserCredential(Base):
    """用户凭证表"""
    __tablename__ = 'user_credentials'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_id: Mapped[str] = mapped_column(String(50)) 
    credential_type: Mapped[str] = mapped_column(String(50))
    encrypted_value: Mapped[str] = mapped_column(String(500))
    display_mask: Mapped[str] = mapped_column(String(100))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="credentials")


class UserUpload(Base):
    """用户上传文件表"""
    __tablename__ = 'user_uploads'
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    parsing_status: Mapped[str] = mapped_column(String(20), default="pending") 
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="uploads")


class UserCockpitIndicator(Base):
    """用户 Cockpit 宏观指标偏好表"""
    __tablename__ = 'user_cockpit_indicators'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    indicator_id: Mapped[str] = mapped_column(String(50), index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="cockpit_indicators")


class UserAssetCache(Base):
    """用户资产实时数据缓存表"""
    __tablename__ = 'user_asset_cache'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    asset_type: Mapped[str] = mapped_column(String(20), index=True)
    asset_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_change_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_cap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), default="mcp")
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    fetch_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="asset_cache")


class UserStrategy(Base):
    """用户自定义策略 (Level 2 表达式引擎)
    
    用户可以编写简单的量化公式，如：
    - "MA(20) > MA(60) AND RSI(14) < 30"
    - "CLOSE > MA(50) AND VOL > VOL_MA(20)"
    - "MACD_HIST > 0 AND RSI(14) < 70"
    
    系统会安全解析并执行这些公式，返回 True/False 信号
    """
    __tablename__ = 'user_strategies'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    formula: Mapped[str] = mapped_column(Text)
    
    category: Mapped[str] = mapped_column(String(50), default="custom")
    variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="strategies")


__all__ = [
    "User",
    "UserPortfolio",
    "UserCredential",
    "UserUpload",
    "UserCockpitIndicator",
    "UserAssetCache",
    "UserStrategy",
]
