"""
Analysis Domain Models - 分析领域模型

包含分析报告、日志、附件等分析相关模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    String,
    Integer,
    Text,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from .base import Base


class AnalysisReport(Base):
    """最终报告表"""
    __tablename__ = 'analysis_reports'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    run_id: Mapped[str] = mapped_column(String(50), index=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    agent_role: Mapped[str] = mapped_column(String(50))
    report_type: Mapped[str] = mapped_column(String(20))
    
    content: Mapped[str] = mapped_column(Text)
    i18n_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    embedding = mapped_column(Vector(384))
    
    # 关联
    user: Mapped["User"] = relationship("User")
    artifacts: Mapped[List["ReportArtifact"]] = relationship("ReportArtifact", back_populates="report", cascade="all, delete-orphan")
    chunks: Mapped[List["ReportChunk"]] = relationship("ReportChunk", back_populates="report", cascade="all, delete-orphan")


class ExecutionLog(Base):
    """流式日志回放表"""
    __tablename__ = 'execution_logs'
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(50), index=True)
    step_number: Mapped[int] = mapped_column(Integer)
    agent_role: Mapped[str] = mapped_column(String(100))
    action_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Usage tracking fields
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Alias for tokens_used
    llm_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    crew_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


class ReportArtifact(Base):
    """报告附件表"""
    __tablename__ = 'report_artifacts'
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("analysis_reports.id"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(50))
    storage_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关联
    report: Mapped["AnalysisReport"] = relationship("AnalysisReport", back_populates="artifacts")


class ReportChunk(Base):
    """RAG 对话切片表"""
    __tablename__ = 'report_chunks'
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("analysis_reports.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1536))
    
    # 关联
    report: Mapped["AnalysisReport"] = relationship("AnalysisReport", back_populates="chunks")


class TradingLesson(Base):
    """系统性记忆/经验表"""
    __tablename__ = 'trading_lessons'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    situation: Mapped[str] = mapped_column(Text)
    outcome_advice: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    embedding = mapped_column(Vector(384))


__all__ = [
    "AnalysisReport",
    "ExecutionLog",
    "ReportArtifact",
    "ReportChunk",
    "TradingLesson",
]
