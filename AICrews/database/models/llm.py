"""
LLM Domain Models - LLM 领域模型

包含 LLM 提供商、模型、用户配置等 LLM 相关模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class LLMProvider(Base):
    """LLM 提供商表"""
    __tablename__ = 'llm_providers'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    provider_type: Mapped[str] = mapped_column(String(20))
    
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_base_url: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_custom_model_name: Mapped[bool] = mapped_column(Boolean, default=False)
    default_base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    models: Mapped[List["LLMModel"]] = relationship("LLMModel", back_populates="provider", cascade="all, delete-orphan")
    user_configs: Mapped[List["UserLLMConfig"]] = relationship("UserLLMConfig", back_populates="provider", cascade="all, delete-orphan")


class LLMModel(Base):
    """LLM 模型表"""
    __tablename__ = 'llm_models'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("llm_providers.id"), index=True)
    model_key: Mapped[str] = mapped_column(String(100), index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    
    context_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_streaming: Mapped[bool] = mapped_column(Boolean, default=True)
    
    cost_per_million_input_tokens: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_per_million_output_tokens: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    model_category: Mapped[str] = mapped_column(String(20), default="general")
    recommended_for: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    performance_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_thinking: Mapped[bool] = mapped_column(Boolean, default=False)
    
    volcengine_endpoint_template: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    last_updated_from_api: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    provider: Mapped["LLMProvider"] = relationship("LLMProvider", back_populates="models")
    user_model_configs: Mapped[List["UserModelConfig"]] = relationship("UserModelConfig", back_populates="model", cascade="all, delete-orphan")
    
    __table_args__ = (UniqueConstraint('provider_id', 'model_key', name='uix_provider_model'),)


class UserLLMConfig(Base):
    """用户 LLM 配置表"""
    __tablename__ = 'user_llm_configs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("llm_providers.id"), index=True)
    
    config_name: Mapped[str] = mapped_column(String(100))
    api_key: Mapped[str] = mapped_column(String(500)) 
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    default_temperature: Mapped[float] = mapped_column(Float, default=0.7)
    default_max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    provider: Mapped["LLMProvider"] = relationship("LLMProvider", back_populates="user_configs")
    model_configs: Mapped[List["UserModelConfig"]] = relationship("UserModelConfig", back_populates="llm_config", cascade="all, delete-orphan")
    
    __table_args__ = (UniqueConstraint('user_id', 'provider_id', 'config_name', name='uix_user_provider_config'),)


class UserModelConfig(Base):
    """用户模型配置表"""
    __tablename__ = 'user_model_configs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    llm_config_id: Mapped[int] = mapped_column(ForeignKey("user_llm_configs.id"), index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("llm_models.id"), index=True)
    
    volcengine_endpoint_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    custom_model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    llm_config: Mapped["UserLLMConfig"] = relationship("UserLLMConfig", back_populates="model_configs")
    model: Mapped["LLMModel"] = relationship("LLMModel", back_populates="user_model_configs")
    
    __table_args__ = (UniqueConstraint('user_id', 'llm_config_id', 'model_id', 'volcengine_endpoint_id', name='uix_user_llm_model'),)


class CrewAgentLLMConfig(Base):
    """Crew Agent LLM 配置表"""
    __tablename__ = 'crew_agent_llm_configs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crew_name: Mapped[str] = mapped_column(String(100), index=True)
    agent_role: Mapped[str] = mapped_column(String(100), index=True)
    
    user_model_config_id: Mapped[int] = mapped_column(ForeignKey("user_model_configs.id"), index=True)
    
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    top_k: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    top_p: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    verbose: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_delegation: Mapped[bool] = mapped_column(Boolean, default=False)
    max_iter: Mapped[int] = mapped_column(Integer, default=3)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    user_model_config: Mapped["UserModelConfig"] = relationship("UserModelConfig")
    
    __table_args__ = (UniqueConstraint('user_id', 'crew_name', 'agent_role', name='uix_user_crew_agent'),)


__all__ = [
    "LLMProvider",
    "LLMModel",
    "UserLLMConfig",
    "UserModelConfig",
    "CrewAgentLLMConfig",
]
