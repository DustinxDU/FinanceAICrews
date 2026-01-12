"""
Skill Catalog Models - Unified skill definitions.

Contains:
- SkillCatalog: Master catalog of all skills (capabilities, presets, strategies, skillsets)
- UserSkillPreference: User-level enable/disable and config per skill
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List

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
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class SkillKind(str, Enum):
    """Skill type enumeration."""
    capability = "capability"  # cap:* - atomic capability tool
    preset = "preset"          # preset:* - preset with defaults
    strategy = "strategy"      # strategy:* - user formula
    skillset = "skillset"      # skillset:* - multi-capability bundle

    @classmethod
    def _missing_(cls, value):
        """Handle legacy 'workflow' value for backward compatibility."""
        if value == "workflow":
            return cls.skillset
        return super()._missing_(value)


class SkillCatalog(Base):
    """
    Skill Catalog - Master table for all skill definitions.

    skill_key format:
    - cap:{capability_id} (e.g., cap:equity_quote)
    - preset:{pack}:{name} (e.g., preset:quant:rsi_14)
    - strategy:{id} (e.g., strategy:123)
    - skillset:{pack}:{name} (e.g., skillset:fundamental_analysis_skillset)
    """
    __tablename__ = "skill_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Unique skill identifier
    skill_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)

    # Skill type
    kind: Mapped[SkillKind] = mapped_column(SQLEnum(SkillKind), nullable=False)

    # Capability this skill maps to (for dependency resolution)
    capability_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # UI grouping (market_data, compute, external_io) - display only
    group_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Display metadata
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Invocation configuration (JSON)
    # - capability: {"capability_id": "equity_quote"}
    # - preset: {"capability_id": "indicator_calc", "defaults": {"indicator": "rsi", "period": 14}}
    # - strategy: {"capability_id": "strategy_eval", "strategy_id": 123, "formula": "..."}
    # - skillset: {"required_capabilities": ["equity_quote", "equity_fundamentals"]}
    invocation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Parameter schema for the wrapper tool
    args_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Skill cards content
    examples: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    failure_modes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # System vs user-created
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # Active status (system-level)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ordering for UI
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("ix_skill_catalog_kind", "kind"),
        Index("ix_skill_catalog_capability", "capability_id"),
        Index("ix_skill_catalog_group", "group_name"),
    )

    def __repr__(self) -> str:
        return f"<SkillCatalog(skill_key='{self.skill_key}', kind={self.kind.value})>"


class UserSkillPreference(Base):
    """
    User Skill Preference - User-level enable/disable and config per skill.

    Combines the old user_tool_preferences functionality with skill_key references.
    """
    __tablename__ = "user_skill_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # User reference
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Skill reference (by skill_key, not FK to allow legacy keys)
    skill_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # User preference
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # User-specific config (e.g., API keys, custom defaults)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "skill_key", name="uix_user_skill_preference"),
        Index("ix_user_skill_pref_user_enabled", "user_id", "is_enabled"),
    )

    def __repr__(self) -> str:
        return f"<UserSkillPreference(user_id={self.user_id}, skill_key='{self.skill_key}', enabled={self.is_enabled})>"


__all__ = [
    "SkillKind",
    "SkillCatalog",
    "UserSkillPreference",
]
