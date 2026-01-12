"""
LLM Policy Router Database Models

This module defines the database tables for the LLM Policy Router system,
which manages LLM access control, BYOK (Bring Your Own Key) profiles,
routing overrides, and virtual keys.

Key tables:
- LLMSystemProfile: System-managed model profiles per scope
- LLMUserByokProfile: User BYOK API key configurations per tier
- LLMRoutingOverride: Admin/user routing mode overrides per scope
- LLMVirtualKey: LiteLLM virtual keys (encrypted) per user
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from AICrews.database.models.base import Base


# Enums for database constraints
import enum


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist Enum members by their `.value` (not `.name`) for DB compatibility."""
    return [e.value for e in enum_cls]


class VirtualKeyStatusEnum(str, enum.Enum):
    """Virtual key status enum for DB constraint."""
    ACTIVE = "active"
    PROVISIONING = "provisioning"
    FAILED = "failed"
    REVOKED = "revoked"


class RoutingModeEnum(str, enum.Enum):
    """Routing mode enum for DB constraint."""
    SYSTEM_ONLY = "SYSTEM_ONLY"
    USER_BYOK_ONLY = "USER_BYOK_ONLY"
    AUTO = "AUTO"


class LLMSystemProfile(Base):
    """
    System-managed LLM profiles for each scope.

    Maps internal scopes (e.g., 'copilot', 'agents_fast') to LiteLLM proxy model aliases
    (e.g., 'sys_copilot_v1', 'sys_agents_fast_v1').

    These are admin-managed and define which upstream models the system uses
    for each business function.
    """

    __tablename__ = "llm_system_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Scope identifier (e.g., 'copilot', 'cockpit_scan', 'agents_fast')
    scope: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # LiteLLM proxy model alias (e.g., 'sys_copilot_v1')
    proxy_model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Enable/disable this profile
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Optional: model parameters override (JSON)
    model_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<LLMSystemProfile(scope={self.scope}, model={self.proxy_model_name})>"


class LLMUserByokProfile(Base):
    """
    User BYOK (Bring Your Own Key) profiles for tiered agent access.

    NEW ARCHITECTURE (v2):
    - References UserLLMConfig via provider_config_id (no duplicate API key storage)
    - References UserModelConfig via model_config_id (specific model selection)
    - Uses 'scenario' instead of 'tier' for clarity
    - Supports volcengine_endpoint for Volcano Engine models

    LEGACY FIELDS (kept for backward compatibility):
    - api_key_encrypted: Now nullable, only used for legacy records
    - tier: Deprecated, use 'scenario' instead
    - provider/model: Deprecated, use provider_config_id/model_config_id instead

    Security:
    - api_key_encrypted: Fernet-encrypted API key (NEVER stored in plaintext)
    - Only decrypted at request time, passed via extra_body.user_config
    - Proxy does NOT persist these keys
    """

    __tablename__ = "llm_user_byok_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User reference
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # NEW: Scenario identifier (e.g., 'agents_fast', 'agents_balanced', 'agents_best')
    scenario: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # LEGACY: Tier identifier (deprecated, use scenario instead)
    tier: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # NEW: Reference to UserLLMConfig (provider + API key)
    provider_config_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user_llm_configs.id", ondelete="SET NULL"), nullable=True
    )

    # NEW: Reference to UserModelConfig (specific model)
    model_config_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user_model_configs.id", ondelete="SET NULL"), nullable=True
    )

    # NEW: Volcano Engine endpoint (for volcengine provider)
    volcengine_endpoint: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # LEGACY: Provider identifier (e.g., 'openai', 'anthropic', 'deepseek')
    # Now nullable - new records should use provider_config_id instead
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # LEGACY: Upstream model name (e.g., 'gpt-4o', 'claude-sonnet-4.5')
    # Now nullable - new records should use model_config_id instead
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # LEGACY: Encrypted API key (Fernet) - now nullable for new records
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Optional: custom API base URL
    api_base: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Optional: API version (for Azure, etc.)
    api_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Enable/disable this profile
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Test results (populated by test endpoint)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_test_status: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 'pass' or 'fail'
    last_test_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # OK, INVALID_KEY, etc.
    last_test_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Unique constraint: one BYOK profile per (user, tier)
    __table_args__ = (
        {"schema": None},  # Use default schema
    )

    # NOTE: no ORM relationship declared here (router queries by user_id directly).

    def mask_api_key(self, decrypted_key: str) -> str:
        """Return masked version of API key for display."""
        if not decrypted_key or len(decrypted_key) < 8:
            return "••••••••"
        return f"{decrypted_key[:4]}••••{decrypted_key[-4:]}"

    def __repr__(self) -> str:
        return f"<LLMUserByokProfile(user_id={self.user_id}, scenario={self.scenario or self.tier}, provider={self.provider})>"


class LLMRoutingOverride(Base):
    """
    Admin/user routing mode overrides per scope.

    Allows forcing specific routing behavior for a user-scope combination:
    - SYSTEM_ONLY: Always use system profile (ignore BYOK)
    - USER_BYOK_ONLY: Require BYOK profile (error if missing)
    - AUTO: Default routing logic (use BYOK if available, else system)

    Use cases:
    - Admin force system model for specific users
    - User explicitly opt out of BYOK for certain scopes
    - Testing/debugging routing logic
    """

    __tablename__ = "llm_routing_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User reference
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Scope identifier
    scope: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Routing mode: SYSTEM_ONLY, USER_BYOK_ONLY, AUTO (enum constraint)
    mode: Mapped[RoutingModeEnum] = mapped_column(
        SQLEnum(
            RoutingModeEnum,
            name="routing_mode_enum",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=False
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Unique constraint: one override per (user, scope)
    __table_args__ = (
        {"schema": None},
    )

    # NOTE: no ORM relationship declared here (router queries by user_id directly).

    def __repr__(self) -> str:
        return f"<LLMRoutingOverride(user_id={self.user_id}, scope={self.scope}, mode={self.mode})>"


class LLMVirtualKey(Base):
    """
    LiteLLM virtual keys for user access control.

    Each user has TWO virtual keys:
    1. vk_user: For BYOK agent tiers (allowed_models: agents_fast/balanced/best)
    2. vk_system_on_behalf: For system scopes (allowed_models: sys_*)

    Keys are:
    - Created by Provisioner via LiteLLM Admin API
    - Stored encrypted in app DB
    - Decrypted only at request time for Authorization header
    - ACL-enforced by LiteLLM Proxy (403 if wrong model for key type)

    Status:
    - active: Key ready to use
    - provisioning: Key creation in progress (lazy provisioning)
    - failed: Key creation failed
    - revoked: Key has been revoked
    """

    __tablename__ = "llm_virtual_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User reference
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Key type: 'user' or 'system_on_behalf'
    key_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Encrypted LiteLLM virtual key (Fernet)
    litellm_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # LiteLLM team ID (optional)
    litellm_team_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Allowed models (JSONB for efficient querying/auditing)
    allowed_models: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Status: active, provisioning, failed, revoked (enum constraint)
    status: Mapped[VirtualKeyStatusEnum] = mapped_column(
        SQLEnum(
            VirtualKeyStatusEnum,
            name="virtual_key_status_enum",
            native_enum=False,
            values_callable=_enum_values,
        ),
        default=VirtualKeyStatusEnum.ACTIVE,
        nullable=False,
        index=True
    )

    # Key alias for idempotency (e.g., "vk:user:123", "vk:obo:123")
    key_alias: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)

    # Provisioning retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    provisioned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Unique constraint: one key per (user, key_type)
    __table_args__ = (
        {"schema": None},
    )

    # NOTE: no ORM relationship declared here (router queries by user_id directly).

    def __repr__(self) -> str:
        return f"<LLMVirtualKey(user_id={self.user_id}, key_type={self.key_type}, status={self.status.value})>"
