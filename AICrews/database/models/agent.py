"""
Agent Domain Models - Agent 领域模型

包含 Agent、Task、Crew、Template 等相关模型。
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
    Index,
    UniqueConstraint,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AgentDefinition(Base):
    """Agent 定义表"""
    __tablename__ = "agent_definitions"
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uix_user_agent_name'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    goal: Mapped[str] = mapped_column(Text)
    backstory: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    llm_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    allow_delegation: Mapped[bool] = mapped_column(Boolean, default=False)
    verbose: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 【旧】扁平工具列表 - 向后兼容
    tool_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    knowledge_source_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    mcp_server_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # 【新】4-Tier Loadout 配置
    loadout_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 【新】Memory Policy: run_only, user_shared, disabled
    memory_policy: Mapped[str] = mapped_column(String(50), default="run_only")
    
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class TaskDefinition(Base):
    """Task 定义表"""
    __tablename__ = "task_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text)

    agent_definition_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_definitions.id"), nullable=True)
    async_execution: Mapped[bool] = mapped_column(Boolean, default=False)
    context_task_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # === Task Output Spec (v1.8: structured outputs + guardrails) ===
    # output_mode: raw | native_json | native_pydantic | soft_json | soft_pydantic
    output_mode: Mapped[str] = mapped_column(String(20), default="raw", nullable=False)
    # schema key referencing task_output_registry (e.g., "finance_report_v1")
    output_schema_key: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # List of guardrail keys (e.g., ["non_empty", "json_parseable"])
    guardrail_keys: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Max retries for guardrail failures (maps from deprecated max_retries)
    guardrail_max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    # If True, missing schema/guardrail keys cause runtime error; else warning + fallback
    strict_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class CrewDefinition(Base):
    """Crew 定义表"""
    __tablename__ = "crew_definitions"
    __table_args__ = (UniqueConstraint('user_id', 'name', name='uix_user_crew_name'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    process: Mapped[str] = mapped_column(String(50), default="sequential")
    
    structure: Mapped[List] = mapped_column(JSON, default=list)
    
    # 【V1.1 核心补充】前端状态
    ui_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    input_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    router_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cache_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 【新】Memory Policy: run_only, user_shared, disabled
    memory_policy: Mapped[str] = mapped_column(String(50), default="run_only")
    
    verbose: Mapped[bool] = mapped_column(Boolean, default=True)
    max_iter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    manager_llm_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    default_variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class CrewVersion(Base):
    """Crew 版本表"""
    __tablename__ = "crew_versions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crew_definitions.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structure_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("crew_id", "version_number", name="uix_crew_versions_crew_id_version"),
    )


class TemplateCatalog(Base):
    """模板目录表"""
    __tablename__ = "template_catalog"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    template_key: Mapped[str] = mapped_column(String(100), index=True)
    template_type: Mapped[str] = mapped_column(String(20), index=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    source_file: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    import_count: Mapped[int] = mapped_column(Integer, default=0)
    published_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        UniqueConstraint('template_key', 'template_type', 'version', name='uix_template_key_type_version'),
        Index('ix_template_type_category', 'template_type', 'category'),
    )


class TemplateImportLog(Base):
    """模板导入日志表"""
    __tablename__ = "template_import_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("template_catalog.id"), index=True)
    
    imported_resource_type: Mapped[str] = mapped_column(String(20))
    imported_resource_id: Mapped[int] = mapped_column(Integer)
    imported_version: Mapped[str] = mapped_column(String(20))
    is_customized: Mapped[bool] = mapped_column(Boolean, default=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关联
    user: Mapped["User"] = relationship("User")
    template: Mapped["TemplateCatalog"] = relationship("TemplateCatalog")
    
    __table_args__ = (
        Index('ix_user_template_import', 'user_id', 'template_id'),
    )


class TemplateUpdateNotification(Base):
    """模板更新通知表"""
    __tablename__ = "template_update_notifications"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("template_catalog.id"), index=True)
    import_log_id: Mapped[int] = mapped_column(ForeignKey("template_import_logs.id"), index=True)
    
    old_version: Mapped[str] = mapped_column(String(20))
    new_version: Mapped[str] = mapped_column(String(20))
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关联
    user: Mapped["User"] = relationship("User")
    template: Mapped["TemplateCatalog"] = relationship("TemplateCatalog")
    import_log: Mapped["TemplateImportLog"] = relationship("TemplateImportLog")


__all__ = [
    "AgentDefinition",
    "TaskDefinition",
    "CrewDefinition",
    "CrewVersion",
    "TemplateCatalog",
    "TemplateImportLog",
    "TemplateUpdateNotification",
]
