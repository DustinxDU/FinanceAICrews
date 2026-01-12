"""
MCP Domain Models - MCP 领域模型

包含 MCP 服务器、工具、订阅等 MCP 相关模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Text,
    Float,
    DateTime,
    Index,
    UniqueConstraint,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from .base import Base


class MCPServer(Base):
    """MCP 服务器表"""
    __tablename__ = 'mcp_servers'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    transport_type: Mapped[str] = mapped_column(String(20))
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    command: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    args: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    requires_auth: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    default_api_key_env: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    capabilities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_subscription: Mapped[bool] = mapped_column(Boolean, default=False)
    price_monthly: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    subscription_level_required: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    documentation_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    subscriber_count: Mapped[int] = mapped_column(Integer, default=0)
    tools_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    tools: Mapped[List["MCPTool"]] = relationship("MCPTool", back_populates="server", cascade="all, delete-orphan")
    subscriptions: Mapped[List["UserMCPSubscription"]] = relationship("UserMCPSubscription", back_populates="server")


class UserMCPServer(Base):
    """用户 MCP 服务器表"""
    __tablename__ = 'user_mcp_servers'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    server_key: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    transport_type: Mapped[str] = mapped_column(String(20))
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    command: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    args: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    env_vars: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    auth_headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    connection_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    discovered_tools_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    tools: Mapped[List["UserMCPTool"]] = relationship("UserMCPTool", back_populates="server", cascade="all, delete-orphan")
    
    __table_args__ = (UniqueConstraint('user_id', 'server_key', name='uix_user_mcp_server'),)


class MCPTool(Base):
    """MCP 工具表"""
    __tablename__ = 'mcp_tools'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("mcp_servers.id"), index=True)

    tool_name: Mapped[str] = mapped_column(String(100), index=True)
    namespaced_name: Mapped[Optional[str]] = mapped_column(String(255), index=True, unique=True, nullable=True)
    legacy_name: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="custom")
    
    input_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    required_params: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=False)
    api_key_param_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    api_key_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    api_key_env: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    rate_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cache_ttl: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    description_embedding = mapped_column(Vector(384), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    server: Mapped["MCPServer"] = relationship("MCPServer", back_populates="tools")
    
    __table_args__ = (
        UniqueConstraint('server_id', 'tool_name', name='uix_server_tool'),
        Index('ix_mcp_tool_category', 'category'),
    )


class UserMCPTool(Base):
    """用户 MCP 工具表"""
    __tablename__ = 'user_mcp_tools'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("user_mcp_servers.id"), index=True)
    
    tool_name: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="custom")
    
    input_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关联
    server: Mapped["UserMCPServer"] = relationship("UserMCPServer", back_populates="tools")
    
    __table_args__ = (UniqueConstraint('user_id', 'server_id', 'tool_name', name='uix_user_server_tool'),)


class UserToolConfig(Base):
    """用户工具配置表"""
    __tablename__ = 'user_tool_configs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tool_id: Mapped[int] = mapped_column(ForeignKey("mcp_tools.id"), index=True)
    
    api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_key_source: Mapped[str] = mapped_column(String(20), default="manual")
    
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    tool: Mapped["MCPTool"] = relationship("MCPTool")
    
    __table_args__ = (UniqueConstraint('user_id', 'tool_id', name='uix_user_tool_config'),)


class UserMCPSubscription(Base):
    """用户 MCP 订阅表"""
    __tablename__ = 'user_mcp_subscriptions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("mcp_servers.id"), index=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    is_authenticated: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    tools_enabled_count: Mapped[int] = mapped_column(Integer, default=0)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    server: Mapped["MCPServer"] = relationship("MCPServer", back_populates="subscriptions")
    
    __table_args__ = (UniqueConstraint('user_id', 'server_id', name='uix_user_mcp_subscription'),)


class AgentToolBinding(Base):
    """Agent 工具绑定表"""
    __tablename__ = 'agent_tool_bindings'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crew_name: Mapped[str] = mapped_column(String(100), index=True)
    agent_role: Mapped[str] = mapped_column(String(100), index=True)
    
    binding_mode: Mapped[str] = mapped_column(String(20), default="explicit")
    tool_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    categories: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    excluded_tool_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (UniqueConstraint('user_id', 'crew_name', 'agent_role', name='uix_agent_tool_binding'),)


__all__ = [
    "MCPServer",
    "UserMCPServer",
    "MCPTool",
    "UserMCPTool",
    "UserToolConfig",
    "UserMCPSubscription",
    "AgentToolBinding",
]
