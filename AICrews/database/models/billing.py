"""
Billing Domain Models - 计费领域模型

包含 Stripe 订阅、发票和 Webhook 事件模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, Boolean, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Subscription(Base):
    """订阅表 - Stripe 订阅管理"""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50))  # active, canceled, past_due, etc.
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="subscription")


class Invoice(Base):
    """发票表 - Stripe 发票记录"""
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stripe_invoice_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(Integer)  # Amount in cents
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    status: Mapped[str] = mapped_column(String(50))  # draft, open, paid, void, uncollectible
    invoice_pdf: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hosted_invoice_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="invoices")


class StripeEvent(Base):
    """Stripe Webhook 事件表 - 用于幂等性处理"""
    __tablename__ = "stripe_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


__all__ = [
    "Subscription",
    "Invoice",
    "StripeEvent",
]
