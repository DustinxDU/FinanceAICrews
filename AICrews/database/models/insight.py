"""
Insight Domain Models - 资产情报局领域模型

包含用户资产分析记录、附件、追溯日志等 Insight 相关模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
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


class UserAssetInsight(Base):
    """用户资产分析记录表"""
    __tablename__ = 'user_asset_insights'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    asset_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    asset_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # 来源标识
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    crew_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 内容
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 情感与指标
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    key_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 信号与推荐
    signal: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 元数据
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 时间戳
    analysis_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    user: Mapped["User"] = relationship("User")
    attachments: Mapped[List["InsightAttachment"]] = relationship("InsightAttachment", back_populates="insight", cascade="all, delete-orphan")
    traces: Mapped[List["InsightTrace"]] = relationship("InsightTrace", back_populates="insight", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'source_type', 'source_id', name='uq_user_insight_source'),
        Index('ix_user_asset_insights_user_ticker', 'user_id', 'ticker'),
        Index('ix_user_asset_insights_source_date', 'source_type', 'analysis_date'),
    )


class InsightAttachment(Base):
    """分析附件表"""
    __tablename__ = 'insight_attachments'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insight_id: Mapped[int] = mapped_column(ForeignKey('user_asset_insights.id', ondelete='CASCADE'), index=True)
    
    # 文件信息
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sheet_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关联
    insight: Mapped["UserAssetInsight"] = relationship("UserAssetInsight", back_populates="attachments")


class InsightTrace(Base):
    """分析追溯日志表"""
    __tablename__ = 'insight_traces'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insight_id: Mapped[int] = mapped_column(ForeignKey('user_asset_insights.id', ondelete='CASCADE'), index=True)
    
    # 追溯信息
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action_type: Mapped[str] = mapped_column(String(50))
    step_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 内容
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 成本与性能
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    
    # 关联
    insight: Mapped["UserAssetInsight"] = relationship("UserAssetInsight", back_populates="traces")
    
    __table_args__ = (
        Index('ix_insight_traces_agent', 'agent_name'),
        Index('ix_insight_traces_created', 'created_at'),
    )


class UserToolPreference(Base):
    """用户工具偏好设置表
    
    统一存储用户对所有来源工具的启用/禁用偏好。
    tool_key 格式: "source:category:name"
    """
    __tablename__ = 'user_tool_preferences'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tool_key: Mapped[str] = mapped_column(String(200))
    tool_source: Mapped[str] = mapped_column(String(50), index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'tool_key', name='uix_user_tool_pref'),
    )


class BuiltinTool(Base):
    """内置工具注册表
    
    存储 Native Quant 和 CrewAI 内置工具的元数据，
    使它们与 MCP 工具一样可以在 UI 中管理。
    """
    __tablename__ = 'builtin_tools'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tool_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    tier: Mapped[str] = mapped_column(String(20), default="data")
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=False)
    api_key_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    config_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


__all__ = [
    "UserAssetInsight",
    "InsightAttachment",
    "InsightTrace",
    "UserToolPreference",
    "BuiltinTool",
]
