from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from AICrews.database.models.user import User
from AICrews.schemas.entitlements import (
    BillingHint,
    ComputingMode,
    DenialCode,
    PolicyAction,
    PolicyDecision,
    PolicyScope,
    EntitlementsSnapshot,
    RuntimeLimits,
    TierType,
)
from AICrews.services.entitlements.config_loader import EntitlementsConfigLoader
from AICrews.services.entitlements.effective_tier import resolve_effective_tier


class EntitlementPolicyEngine:
    def __init__(self, *, config_path: str = "config/entitlements.yaml"):
        self._loader = EntitlementsConfigLoader(config_path)

    def check(
        self,
        db: Session,
        user: Optional[User],
        *,
        action: PolicyAction,
        requested_mode: Optional[ComputingMode] = None,
        now_utc: Optional[datetime] = None,
    ) -> PolicyDecision:
        cfg = self._loader.get()
        raw_tier, effective_tier, downgraded, tier_reason = resolve_effective_tier(db, user, now_utc=now_utc)

        raw_tier_norm = raw_tier if raw_tier in ("free", "starter", "pro") else "free"
        eff_tier_norm = effective_tier if effective_tier in ("free", "starter", "pro") else "free"

        tier_cfg = cfg.tiers[eff_tier_norm]

        # Auth / Account
        if user is None and action not in (PolicyAction.RUN_QUICK_SCAN, PolicyAction.RUN_CHART_SCAN):
            return self._deny(
                raw_tier_norm, eff_tier_norm, tier_reason, action, DenialCode.AUTH_REQUIRED, "Login required", tier_cfg, cfg
            )
        if user is not None and getattr(user, "is_active", True) is False:
            return self._deny(
                raw_tier_norm,
                eff_tier_norm,
                tier_reason,
                action,
                DenialCode.ACCOUNT_INACTIVE,
                "Account inactive",
                tier_cfg,
                cfg,
            )

        # Mode resolution + scope mapping
        effective_mode = requested_mode or tier_cfg.default_mode
        if action in (PolicyAction.RUN_QUICK_SCAN, PolicyAction.RUN_CHART_SCAN):
            effective_mode = ComputingMode.ECO
            effective_scope = PolicyScope.QUICK_SCAN if action == PolicyAction.RUN_QUICK_SCAN else PolicyScope.CHART_SCAN
        else:
            if requested_mode and requested_mode not in tier_cfg.allowed_modes:
                return self._deny(
                    raw_tier_norm, eff_tier_norm, tier_reason, action, DenialCode.MODE_NOT_ALLOWED, "Mode not allowed", tier_cfg, cfg
                )
            effective_scope = cfg.mode_mappings[effective_mode]

        # Action permission (with downgrade denial semantics)
        allowed_actions = tier_cfg.allowed_actions
        action_allowed = "*" in allowed_actions or action.value in allowed_actions
        if not action_allowed:
            # only use downgrade code when the rejection is caused by downgrade
            if downgraded and raw_tier_norm != eff_tier_norm:
                raw_cfg = cfg.tiers.get(raw_tier_norm)
                raw_allowed = raw_cfg.allowed_actions if raw_cfg else []
                would_allow_in_raw = "*" in raw_allowed or action.value in raw_allowed
                if would_allow_in_raw:
                    return self._deny(
                        raw_tier_norm,
                        eff_tier_norm,
                        tier_reason,
                        action,
                        DenialCode.SUBSCRIPTION_INACTIVE_DOWNGRADED,
                        "Subscription inactive",
                        tier_cfg,
                        cfg,
                    )
            return self._deny(
                raw_tier_norm, eff_tier_norm, tier_reason, action, DenialCode.ACTION_NOT_ALLOWED, "Upgrade required", tier_cfg, cfg
            )

        # BYOK allowed (permission only)
        byok_allowed = bool(tier_cfg.byok.allowed)
        if effective_scope in (PolicyScope.QUICK_SCAN, PolicyScope.CHART_SCAN):
            byok_allowed = False

        limits = RuntimeLimits(
            max_iterations=int(tier_cfg.limits.max_iterations),
            timeout_seconds=int(tier_cfg.limits.timeout_seconds),
            max_parallel_tools=int(tier_cfg.limits.max_parallel_tools),
            byok_allowed=byok_allowed,
        )

        billing = BillingHint(
            credits_rate_hint=int(cfg.mode_rates[effective_mode]),
            credits_charge_decision_source="llm_router",
        )

        return PolicyDecision(
            allowed=True,
            raw_tier=TierType(raw_tier_norm),
            effective_tier=TierType(eff_tier_norm),
            effective_tier_reason=tier_reason,
            effective_mode=effective_mode,
            effective_scope=effective_scope,
            limits=limits,
            billing_hint=billing,
            byok_used=None,
        )

    def snapshot(
        self,
        db: Session,
        user: Optional[User],
        *,
        now_utc: Optional[datetime] = None,
    ) -> EntitlementsSnapshot:
        cfg = self._loader.get()
        raw_tier, effective_tier, downgraded, tier_reason = resolve_effective_tier(db, user, now_utc=now_utc)
        raw_tier_norm = raw_tier if raw_tier in ("free", "starter", "pro") else "free"
        eff_tier_norm = effective_tier if effective_tier in ("free", "starter", "pro") else "free"

        tier_cfg = cfg.tiers[eff_tier_norm]
        byok_allowed = bool(tier_cfg.byok.allowed)
        limits = RuntimeLimits(
            max_iterations=int(tier_cfg.limits.max_iterations),
            timeout_seconds=int(tier_cfg.limits.timeout_seconds),
            max_parallel_tools=int(tier_cfg.limits.max_parallel_tools),
            byok_allowed=byok_allowed,
        )

        evaluated_at = now_utc or datetime.now(timezone.utc)
        if evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)

        return EntitlementsSnapshot(
            raw_tier=TierType(raw_tier_norm),
            effective_tier=TierType(eff_tier_norm),
            effective_tier_reason=tier_reason,
            downgraded=raw_tier_norm != eff_tier_norm,
            allowed_actions=list(tier_cfg.allowed_actions),
            allowed_modes=[mode.value for mode in tier_cfg.allowed_modes],
            default_mode=tier_cfg.default_mode,
            limits=limits,
            config_fingerprint=self._loader.fingerprint(),
            evaluated_at_utc=evaluated_at,
        )

    def _deny(
        self,
        raw_tier: str,
        effective_tier: str,
        tier_reason: str,
        action: PolicyAction,
        code: DenialCode,
        message: str,
        tier_cfg,
        cfg,
    ) -> PolicyDecision:
        # For denied decisions, still populate effective_mode/scope/limits with safe defaults.
        effective_mode = tier_cfg.default_mode
        if action == PolicyAction.RUN_QUICK_SCAN:
            effective_scope = PolicyScope.QUICK_SCAN
            effective_mode = ComputingMode.ECO
        elif action == PolicyAction.RUN_CHART_SCAN:
            effective_scope = PolicyScope.CHART_SCAN
            effective_mode = ComputingMode.ECO
        else:
            effective_scope = cfg.mode_mappings[effective_mode]

        byok_allowed = bool(tier_cfg.byok.allowed)
        if effective_scope in (PolicyScope.QUICK_SCAN, PolicyScope.CHART_SCAN):
            byok_allowed = False

        limits = RuntimeLimits(
            max_iterations=int(tier_cfg.limits.max_iterations),
            timeout_seconds=int(tier_cfg.limits.timeout_seconds),
            max_parallel_tools=int(tier_cfg.limits.max_parallel_tools),
            byok_allowed=byok_allowed,
        )
        billing = BillingHint(
            credits_rate_hint=int(cfg.mode_rates[effective_mode]),
            credits_charge_decision_source="llm_router",
        )

        return PolicyDecision(
            allowed=False,
            denial_code=code,
            denial_message=message,
            raw_tier=TierType(raw_tier if raw_tier in ("free", "starter", "pro") else "free"),
            effective_tier=TierType(effective_tier if effective_tier in ("free", "starter", "pro") else "free"),
            effective_tier_reason=tier_reason,
            effective_mode=effective_mode,
            effective_scope=effective_scope,
            limits=limits,
            billing_hint=billing,
            byok_used=None,
        )
