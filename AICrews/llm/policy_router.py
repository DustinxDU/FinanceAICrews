"""
LLM Policy Router - Pure Decision Engine

This module implements the core routing logic for LLM calls in the FinanceAICrews
platform. It determines which LLM configuration to use based on:
- Scope (business intent: copilot, agents_fast, etc.)
- User context (subscription level, BYOK eligibility)
- Admin overrides (force system or require BYOK)

The router is a pure decision engine that:
- Reads DB state only (no external API calls)
- Returns ResolvedLLMCall contract (stable interface)
- Handles lazy virtual key provisioning with concurrency safety
- Enforces routing priority: override > default rules > eligibility

Key Security Properties:
- Never logs plaintext API keys
- Decrypts keys only in-memory at request time
- Enforces proxy-side ACL via virtual key allowed_models
- Separates system keys (vk_system_on_behalf) from user keys (vk_user)
"""

import uuid
from AICrews.observability.logging import get_logger
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from AICrews.database.models.user import User
from AICrews.database.models.llm_policy import (
    LLMSystemProfile,
    LLMUserByokProfile,
    LLMRoutingOverride,
    LLMVirtualKey,
    RoutingModeEnum,
    VirtualKeyStatusEnum,
)
from AICrews.schemas.llm_policy import (
    UserContext,
    LLMScope,
    RoutingMode,
    ResolvedLLMCall,
    LLMKeyProvisioningError,
    LLMByokProfileNotFoundError,
)
from AICrews.utils.encryption import decrypt_api_key
from AICrews.llm.system_config import get_system_llm_config_store, SystemLLMConfig

logger = get_logger(__name__)


class LLMPolicyRouter:
    """
    Pure decision engine for LLM routing.

    Routing Priority (strict order):
    1. Admin override (if exists) → wins over everything
    2. Default scope rules:
       - SYSTEM_ONLY scopes → always system profile
       - AUTO scopes → BYOK if eligible + configured, else system
    3. Eligibility check (subscription level)

    Concurrency Safety:
    - Uses SELECT FOR UPDATE to prevent duplicate provisioning
    - Lazy provisioning triggers on first LLM call
    - Idempotent: safe to retry after provisioning failure
    """

    def __init__(
        self,
        proxy_base_url: str,
        encryption_key: bytes,
        grace_period_seconds: int = 300,
    ):
        """
        Initialize router.

        Args:
            proxy_base_url: LiteLLM proxy base URL (e.g., http://litellm:4000/v1)
            encryption_key: Fernet key for decrypting API keys
            grace_period_seconds: Grace period for key rotation (default 300s)
        """
        self.proxy_base_url = proxy_base_url
        self.encryption_key = encryption_key
        self.grace_period_seconds = grace_period_seconds

    def resolve_from_policy(
        self,
        *,
        scope: LLMScope,
        user_id: int,
        db: Session,
        byok_allowed: bool,
        custom_tags: Optional[List[str]] = None,
    ) -> ResolvedLLMCall:
        """
        Resolve using entitlements output (scope + byok_allowed). This is the v1.1 contract.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        # Determine routing mode (override wins, otherwise SYSTEM_ONLY vs AUTO)
        override = self._get_routing_override(user_id, scope.value, db)
        if override:
            routing_mode = override.mode
        else:
            routing_mode = RoutingModeEnum.SYSTEM_ONLY if LLMScope.is_system_only(scope.value) else RoutingModeEnum.AUTO

        if routing_mode == RoutingModeEnum.SYSTEM_ONLY:
            resolved = self._route_to_system_profile(scope, user_id, db)
        elif routing_mode == RoutingModeEnum.USER_BYOK_ONLY:
            resolved = self._route_to_byok_required(scope, user_id, db)
        else:
            # AUTO
            resolved = self._route_auto(scope, user_id, db, byok_allowed=byok_allowed)

        resolved.set_run_id(run_id)
        resolved.add_standard_tags(
            scope=scope.value,
            user_id=user_id,
            product=self._infer_product_from_scope(scope),
            plan="unknown",
        )
        if custom_tags:
            for tag in custom_tags:
                if tag not in resolved.metadata["tags"]:
                    resolved.metadata["tags"].append(tag)

        return resolved

    # Backward compatibility: delegate to resolve_from_policy using byok_allowed from UserContext if provided.
    def resolve(
        self,
        scope: LLMScope,
        user_context: UserContext,
        db: Session,
        custom_tags: Optional[List[str]] = None,
    ) -> ResolvedLLMCall:
        if not getattr(user_context, "is_active", True):
            raise ValueError("User is not active")
        return self.resolve_from_policy(
            scope=scope,
            user_id=user_context.user_id,
            db=db,
            byok_allowed=getattr(user_context, "byok_allowed", False),
            custom_tags=custom_tags,
        )

    # ========================================================================
    # Routing Strategies
    # ========================================================================

    def _route_to_system_profile(
        self, scope: LLMScope, user_id: int, db: Session
    ) -> ResolvedLLMCall:
        """
        Route to system-managed profile (SYSTEM_ONLY mode).

        Always uses:
        - System profile model alias (sys_*)
        - System virtual key (vk_system_on_behalf)
        - No user_config (no BYOK)
        """
        # Get system profile for scope
        system_profile = self._get_system_profile(scope.value, db)
        if not system_profile:
            raise ValueError(f"System profile not found for scope: {scope.value}")

        # Get or provision system virtual key
        virtual_key = self._get_or_provision_virtual_key(
            user_id=user_id,
            key_type="system_on_behalf",
            db=db,
        )

        # Decrypt virtual key
        api_key_plain = decrypt_api_key(
            virtual_key.litellm_key_encrypted, self.encryption_key
        )

        return ResolvedLLMCall(
            base_url=self.proxy_base_url,
            api_key=api_key_plain,
            model=system_profile.proxy_model_name,
            metadata={"tags": [], "run_id": None},
            extra_headers={"x-litellm-enable-message-redaction": "true"},
            extra_body=None,  # No user_config for system profiles
        )

    def _route_to_byok_required(
        self, scope: LLMScope, user_id: int, db: Session
    ) -> ResolvedLLMCall:
        """
        Route to BYOK profile (USER_BYOK_ONLY mode).

        Requires:
        - User has active BYOK profile for tier
        - User is eligible for BYOK (premium subscription)

        Raises:
            LLMByokProfileNotFoundError: If BYOK profile missing/disabled
        """
        # Get BYOK profile for tier
        tier = scope.value  # agents_fast/balanced/best
        byok_profile = self._get_byok_profile(user_id, tier, db)

        if not byok_profile or not byok_profile.enabled:
            raise LLMByokProfileNotFoundError(
                f"BYOK profile not found or disabled for user {user_id}, "
                f"tier {tier}"
            )

        # Get or provision user virtual key
        virtual_key = self._get_or_provision_virtual_key(
            user_id=user_id,
            key_type="user",
            db=db,
        )

        # Decrypt keys
        api_key_plain = decrypt_api_key(
            virtual_key.litellm_key_encrypted, self.encryption_key
        )
        byok_api_key_plain = decrypt_api_key(
            byok_profile.api_key_encrypted, self.encryption_key
        )

        # Build user_config for BYOK
        user_config = {
            "provider": byok_profile.provider,
            "model": byok_profile.model,
            "api_key": byok_api_key_plain,
        }

        if byok_profile.api_base:
            user_config["api_base"] = byok_profile.api_base
        if byok_profile.api_version:
            user_config["api_version"] = byok_profile.api_version

        return ResolvedLLMCall(
            base_url=self.proxy_base_url,
            api_key=api_key_plain,
            model=tier,  # Use tier alias (agents_fast, etc.)
            metadata={"tags": [], "run_id": None},
            extra_headers={"x-litellm-enable-message-redaction": "true"},
            extra_body={"user_config": user_config},
        )

    def _route_auto(
        self, scope: LLMScope, user_id: int, db: Session, *, byok_allowed: bool
    ) -> ResolvedLLMCall:
        """
        AUTO routing: use BYOK only when allowed AND configured AND user enabled; otherwise system.
        
        Decision flow:
        1. Check if scope allows BYOK (byok_allowed)
        2. Check if user has enabled use_own_llm_keys global toggle
        3. Check if user has configured BYOK profile for this scope
        4. Fallback to system profile
        """
        tier = scope.value  # agents_fast/balanced/best

        if byok_allowed:
            # Check if user has enabled BYOK globally
            user = self._get_user(user_id, db)
            if user and user.use_own_llm_keys:
                byok_profile = self._get_byok_profile(user_id, tier, db)
                if byok_profile and byok_profile.enabled:
                    return self._route_to_byok_required(scope, user_id, db)

        return self._route_to_system_profile(scope, user_id, db)

    # ========================================================================
    # Database Queries
    # ========================================================================

    def _get_user(self, user_id: int, db: Session) -> Optional[User]:
        """Get user by ID for checking use_own_llm_keys setting."""
        stmt = select(User).where(User.id == user_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def _get_system_profile(self, scope: str, db: Session) -> Optional[LLMSystemProfile]:
        """Get system profile for scope."""
        stmt = select(LLMSystemProfile).where(
            LLMSystemProfile.scope == scope,
            LLMSystemProfile.enabled == True,
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def _get_byok_profile(
        self, user_id: int, tier: str, db: Session
    ) -> Optional[LLMUserByokProfile]:
        """Get BYOK profile for user and tier."""
        stmt = select(LLMUserByokProfile).where(
            LLMUserByokProfile.user_id == user_id,
            LLMUserByokProfile.tier == tier,
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def _get_routing_override(
        self, user_id: int, scope: str, db: Session
    ) -> Optional[LLMRoutingOverride]:
        """Get routing override for user and scope."""
        stmt = select(LLMRoutingOverride).where(
            LLMRoutingOverride.user_id == user_id,
            LLMRoutingOverride.scope == scope,
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def _get_or_provision_virtual_key(
        self, user_id: int, key_type: str, db: Session
    ) -> LLMVirtualKey:
        """
        Get or provision virtual key for user (lazy provisioning).

        Concurrency-safe implementation:
        1. Check if active key exists
        2. If provisioning in progress → raise error with retry_after
        3. If missing → create provisioning record and raise error

        The actual provisioning (calling LiteLLM Admin API) happens in a
        separate provisioner script, not in the router.

        Args:
            user_id: User ID
            key_type: "user" or "system_on_behalf"
            db: Database session

        Returns:
            Active virtual key

        Raises:
            LLMKeyProvisioningError: Key is being provisioned or failed
        """
        # Use SELECT FOR UPDATE to prevent concurrent provisioning
        stmt = (
            select(LLMVirtualKey)
            .where(
                LLMVirtualKey.user_id == user_id,
                LLMVirtualKey.key_type == key_type,
            )
            .with_for_update()
        )
        result = db.execute(stmt)
        key = result.scalar_one_or_none()

        # Case 1: Active key exists → return immediately
        if key and key.status == VirtualKeyStatusEnum.ACTIVE:
            return key

        # Case 2: Provisioning in progress → tell caller to retry
        if key and key.status == VirtualKeyStatusEnum.PROVISIONING:
            # Check if provisioning is stale (> 60 seconds old)
            if key.created_at:
                age_seconds = (datetime.now() - key.created_at).total_seconds()
                if age_seconds > 60:
                    # Stale provisioning - mark as failed
                    key.status = VirtualKeyStatusEnum.FAILED
                    db.commit()
                    logger.warning(
                        f"Stale provisioning detected for user {user_id}, "
                        f"key_type {key_type} (age: {age_seconds}s)"
                    )

            raise LLMKeyProvisioningError(
                f"Virtual key provisioning in progress for user {user_id}, "
                f"key_type {key_type}. Retry in 5 seconds.",
                retry_after=5,
            )

        # Case 3: Failed provisioning → allow retry
        if key and key.status == VirtualKeyStatusEnum.FAILED:
            # Reset to provisioning for retry
            key.status = VirtualKeyStatusEnum.PROVISIONING
            db.commit()

            raise LLMKeyProvisioningError(
                f"Virtual key provisioning failed previously for user {user_id}, "
                f"key_type {key_type}. Retrying provisioning.",
                retry_after=5,
            )

        # Case 4: No key exists → create provisioning record
        if not key:
            key = LLMVirtualKey(
                user_id=user_id,
                key_type=key_type,
                status=VirtualKeyStatusEnum.PROVISIONING,
                created_at=datetime.now(),
            )
            db.add(key)
            db.commit()

            logger.info(
                f"Triggered lazy provisioning for user {user_id}, key_type {key_type}"
            )

            raise LLMKeyProvisioningError(
                f"Virtual key provisioning triggered for user {user_id}, "
                f"key_type {key_type}. Retry in 5 seconds.",
                retry_after=5,
            )

        # Should never reach here
        raise ValueError(f"Unexpected virtual key state: {key.status}")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _infer_product_from_scope(self, scope: LLMScope) -> str:
        """Infer product name from scope for tagging."""
        if scope == LLMScope.COPILOT:
            return "copilot"
        elif scope == LLMScope.COCKPIT_SCAN:
            return "cockpit"
        elif scope in [LLMScope.CREW_ROUTER, LLMScope.CREW_SUMMARY]:
            return "crew"
        elif scope in [
            LLMScope.AGENTS_FAST,
            LLMScope.AGENTS_BALANCED,
            LLMScope.AGENTS_BEST,
        ]:
            return "agents"
        else:
            return "unknown"

    # ========================================================================
    # Direct LLM Resolution (Env-based, no proxy)
    # ========================================================================

    def resolve_system_direct(
        self,
        scope: LLMScope,
        custom_tags: Optional[List[str]] = None,
    ) -> "DirectLLMCall":
        """
        Resolve system scope to direct LLM call (bypasses LiteLLM Proxy).

        Uses SystemLLMConfigStore to get configuration from environment variables.
        This is the preferred method for system-managed scopes as it:
        - Supports hot updates without service restart
        - Has fewer moving parts (no proxy dependency)
        - Is simpler to configure via environment variables

        Args:
            scope: The LLM scope (e.g., LLMScope.COPILOT)
            custom_tags: Optional custom tags for logging

        Returns:
            DirectLLMCall with all parameters needed to create LLM instance

        Raises:
            ValueError: If no configuration found for scope
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        # Get config from environment
        store = get_system_llm_config_store()
        config = store.get_config(scope.value)

        # Build result
        result = DirectLLMCall(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            metadata={
                "tags": [],
                "run_id": run_id,
            },
        )

        # Add standard tags
        result.add_standard_tags(
            scope=scope.value,
            product=self._infer_product_from_scope(scope),
        )

        if custom_tags:
            for tag in custom_tags:
                if tag not in result.metadata["tags"]:
                    result.metadata["tags"].append(tag)

        logger.debug(
            "Resolved system direct LLM: scope=%s, provider=%s, model=%s",
            scope.value,
            config.provider,
            config.model,
        )

        return result

    @staticmethod
    def is_env_configured(scope: LLMScope) -> bool:
        """
        Check if a scope has environment-based configuration.

        Useful for determining whether to use direct LLM or fall back to proxy.
        """
        store = get_system_llm_config_store()
        return store.is_configured(scope.value)


class DirectLLMCall:
    """
    Direct LLM call contract (bypasses proxy).

    Unlike ResolvedLLMCall which targets LiteLLM Proxy, this class
    contains parameters for direct LLM creation via UnifiedLLMManager.

    Usage:
        call = router.resolve_system_direct(LLMScope.COPILOT)
        llm = unified_manager.create_default_llm(
            provider_key=call.provider,
            model_key=call.model,
            api_key=call.api_key,
            base_url=call.base_url,
            temperature=call.temperature,
            max_tokens=call.max_tokens,
        )
    """

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[dict] = None,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.metadata = metadata or {"tags": [], "run_id": None}

    def add_standard_tags(self, scope: str, product: str) -> None:
        """Add standard tags for logging."""
        if "tags" not in self.metadata:
            self.metadata["tags"] = []

        standard_tags = [
            f"scope:{scope}",
            f"product:{product}",
            "routing:direct",
        ]

        for tag in standard_tags:
            if tag not in self.metadata["tags"]:
                self.metadata["tags"].append(tag)

    def to_llm_params(self) -> dict:
        """
        Convert to parameters for UnifiedLLMManager.create_default_llm().

        Returns:
            Dict with all LLM creation parameters
        """
        params = {
            "provider_key": self.provider,
            "model_key": self.model,
            "api_key": self.api_key,
            "temperature": self.temperature,
        }
        if self.base_url:
            params["base_url"] = self.base_url
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        return params

    def __repr__(self) -> str:
        return (
            f"DirectLLMCall(provider={self.provider!r}, model={self.model!r}, "
            f"base_url={self.base_url!r}, temperature={self.temperature})"
        )
