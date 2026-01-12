"""
Cockpit Domain Models - Cockpit 领域模型

包含宏观指标、缓存、策略等 Cockpit 相关模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    Index,
    UniqueConstraint,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class MacroIndicatorCache(Base):
    """全局宏观指标缓存表"""
    __tablename__ = 'macro_indicator_cache'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    indicator_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    indicator_name: Mapped[str] = mapped_column(String(100))
    symbol: Mapped[str] = mapped_column(String(50))
    current_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    change_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    change_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trend: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    indicator_type: Mapped[str] = mapped_column(String(20))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), default="mcp")
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    fetch_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AssetSearchCache(Base):
    """资产搜索结果缓存表"""
    __tablename__ = 'asset_search_cache'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    search_query: Mapped[str] = mapped_column(String(200))
    asset_type_filter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    results: Mapped[dict] = mapped_column(JSON)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


__all__ = [
    "MacroIndicatorCache",
    "AssetSearchCache",
]
