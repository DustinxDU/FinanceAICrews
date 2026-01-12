"""
Knowledge Domain Models - 知识领域模型

包含知识源、订阅、绑定等知识相关模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    UniqueConstraint,
    Index,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class KnowledgeSource(Base):
    """系统级知识源表"""
    __tablename__ = 'knowledge_sources'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    source_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    category: Mapped[str] = mapped_column(String(100), default="general")
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    knowledge_scope: Mapped[str] = mapped_column(String(20), default="both")
    
    scope: Mapped[str] = mapped_column(String(20), default="system")
    tier: Mapped[str] = mapped_column(String(20), default="free")
    price: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    subscriber_count: Mapped[int] = mapped_column(Integer, default=0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    
    chunk_size: Mapped[int] = mapped_column(Integer, default=4000)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=200)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    owner: Mapped[Optional["User"]] = relationship("User")
    subscriptions: Mapped[List["UserKnowledgeSubscription"]] = relationship("UserKnowledgeSubscription", back_populates="source")


class UserKnowledgeSubscription(Base):
    """用户知识订阅表"""
    __tablename__ = 'user_knowledge_subscriptions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_sources.id"), index=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关联
    user: Mapped["User"] = relationship("User")
    source: Mapped["KnowledgeSource"] = relationship("KnowledgeSource", back_populates="subscriptions")
    
    __table_args__ = (UniqueConstraint('user_id', 'source_id', name='uix_user_knowledge_subscription'),)


class UserKnowledgeSource(Base):
    """用户自定义知识源表"""
    __tablename__ = 'user_knowledge_sources'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    source_key: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    source_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    category: Mapped[str] = mapped_column(String(100), default="custom")
    scope: Mapped[str] = mapped_column(String(20), default="both")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    chunk_size: Mapped[int] = mapped_column(Integer, default=4000)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=200)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (UniqueConstraint('user_id', 'source_key', name='uix_user_source_key'),)


class CrewKnowledgeBinding(Base):
    """Crew 知识绑定表"""
    __tablename__ = 'crew_knowledge_bindings'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crew_name: Mapped[str] = mapped_column(String(100), index=True)
    
    binding_mode: Mapped[str] = mapped_column(String(50), default="explicit")
    
    source_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    user_source_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    scope: Mapped[str] = mapped_column(String(20), default="crew")
    
    categories: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    excluded_source_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    include_trading_lessons: Mapped[bool] = mapped_column(Boolean, default=True)
    max_lessons: Mapped[int] = mapped_column(Integer, default=5)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (UniqueConstraint('user_id', 'crew_name', name='uix_crew_knowledge_binding'),)


class AgentKnowledgeBinding(Base):
    """Agent 知识绑定表"""
    __tablename__ = 'agent_knowledge_bindings'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crew_name: Mapped[str] = mapped_column(String(100), index=True)
    agent_name: Mapped[str] = mapped_column(String(100), index=True)
    
    source_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    user_source_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    scope: Mapped[str] = mapped_column(String(20), default="agent")
    
    include_trading_lessons: Mapped[bool] = mapped_column(Boolean, default=True)
    max_lessons: Mapped[int] = mapped_column(Integer, default=5)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (UniqueConstraint('user_id', 'crew_name', 'agent_name', name='uix_agent_knowledge_binding'),)


class KnowledgeSourceVersion(Base):
    """知识源版本表"""
    __tablename__ = 'knowledge_source_versions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_sources.id"), index=True)
    version: Mapped[str] = mapped_column(String(20))
    
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关联
    source: Mapped["KnowledgeSource"] = relationship("KnowledgeSource")
    
    __table_args__ = (UniqueConstraint('source_id', 'version', name='uix_source_version'),)


class KnowledgeUsageLog(Base):
    """知识使用日志表"""
    __tablename__ = 'knowledge_usage_logs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("knowledge_sources.id"), nullable=True, index=True)
    user_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user_knowledge_sources.id"), nullable=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    
    crew_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    usage_type: Mapped[str] = mapped_column(String(50), default="crew_run")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关联
    source: Mapped[Optional["KnowledgeSource"]] = relationship("KnowledgeSource")
    user_source: Mapped[Optional["UserKnowledgeSource"]] = relationship("UserKnowledgeSource")
    user: Mapped[Optional["User"]] = relationship("User")


__all__ = [
    "KnowledgeSource",
    "UserKnowledgeSubscription",
    "UserKnowledgeSource",
    "CrewKnowledgeBinding",
    "AgentKnowledgeBinding",
    "KnowledgeSourceVersion",
    "KnowledgeUsageLog",
]
