"""
Market Domain Models - 市场数据领域模型

包含资产、行情、价格、基本面等市场数据模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Float,
    DateTime,
    Text,
    Boolean,
    UniqueConstraint,
    Index,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from .base import Base


class Asset(Base):
    """资产基础信息表"""
    __tablename__ = 'assets'
    
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(20), index=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    portfolios: Mapped[List["UserPortfolio"]] = relationship(
        "UserPortfolio",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    realtime_quote: Mapped[Optional["RealtimeQuote"]] = relationship("RealtimeQuote", back_populates="asset", uselist=False)
    active_monitoring: Mapped[Optional["ActiveMonitoring"]] = relationship("ActiveMonitoring", back_populates="asset", uselist=False)


class RealtimeQuote(Base):
    """实时行情快照表"""
    __tablename__ = 'realtime_quotes'
    
    ticker: Mapped[str] = mapped_column(ForeignKey("assets.ticker"), primary_key=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_local: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency_local: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    change_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    market_cap: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    open_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prev_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trade_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    data_source: Mapped[str] = mapped_column(String(50), default="mcp", index=True)
    fetch_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_market_open: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # 关系
    asset: Mapped["Asset"] = relationship(back_populates="realtime_quote")


class StockPrice(Base):
    """K线数据表"""
    __tablename__ = 'market_prices'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    
    resolution: Mapped[str] = mapped_column(String(5), default="1d") 
    source: Mapped[str] = mapped_column(String(50)) 
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    __table_args__ = (UniqueConstraint('ticker', 'date', 'resolution', name='uix_ticker_date_res'),)


class FundamentalData(Base):
    """基本面数据表"""
    __tablename__ = 'fundamental_data'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    data_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    
    # 基础信息
    company_name: Mapped[str] = mapped_column(String(200), nullable=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(50), nullable=True)
    exchange: Mapped[str] = mapped_column(String(50), nullable=True)
    
    # 关键指标
    market_cap: Mapped[float] = mapped_column(Float, nullable=True)
    pe_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    forward_pe: Mapped[float] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    dividend_yield: Mapped[float] = mapped_column(Float, nullable=True)
    beta: Mapped[float] = mapped_column(Float, nullable=True)
    
    # 财务健康
    current_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float] = mapped_column(Float, nullable=True)
    return_on_equity: Mapped[float] = mapped_column(Float, nullable=True)
    profit_margins: Mapped[float] = mapped_column(Float, nullable=True)
    
    week_52_high: Mapped[float] = mapped_column(Float, nullable=True)
    week_52_low: Mapped[float] = mapped_column(Float, nullable=True)
    
    source: Mapped[str] = mapped_column(String(50))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (UniqueConstraint('ticker', 'data_date', 'source', name='uix_ticker_funddate_src'),)


class FinancialStatement(Base):
    """财务报表表"""
    __tablename__ = 'financial_statements'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    statement_type: Mapped[str] = mapped_column(String(20), index=True) 
    period_end_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    
    frequency: Mapped[str] = mapped_column(String(10)) 
    data: Mapped[dict] = mapped_column(JSON) 
    
    source: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    __table_args__ = (
        UniqueConstraint('ticker', 'statement_type', 'period_end_date', 'frequency', name='uix_ticker_stmt_period'),
    )


class TechnicalIndicator(Base):
    """技术指标表"""
    __tablename__ = 'technical_indicators'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    indicator_name: Mapped[str] = mapped_column(String(20), index=True) 
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    
    value: Mapped[float] = mapped_column(Float, nullable=True) 
    values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) 
    
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    __table_args__ = (
        UniqueConstraint('ticker', 'indicator_name', 'date', name='uix_ticker_indicator_date'),
    )


class MarketNews(Base):
    """新闻表"""
    __tablename__ = 'market_news'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(10), index=True, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(500), unique=True)
    source: Mapped[str] = mapped_column(String(50))
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    embedding = mapped_column(Vector(384), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class InsiderActivity(Base):
    """内部交易表"""
    __tablename__ = 'insider_activity'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    activity_type: Mapped[str] = mapped_column(String(20)) 
    
    transaction_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    insider_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    insider_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    transaction_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    shares: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    source: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('ix_ticker_activity_date', 'ticker', 'activity_type', 'transaction_date'),
    )


class ActiveMonitoring(Base):
    """活跃监控表"""
    __tablename__ = 'active_monitoring'
    
    ticker: Mapped[str] = mapped_column(ForeignKey("assets.ticker"), primary_key=True)
    subscriber_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=5)
    task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关系
    asset: Mapped["Asset"] = relationship(back_populates="active_monitoring")


__all__ = [
    "Asset",
    "UserPortfolio",
    "RealtimeQuote",
    "StockPrice",
    "FundamentalData",
    "FinancialStatement",
    "TechnicalIndicator",
    "MarketNews",
    "InsiderActivity",
    "ActiveMonitoring",
]
