from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TierType(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"


class ComputingMode(str, Enum):
    ECO = "eco"
    STANDARD = "standard"
    EXTREME = "extreme"


class PolicyAction(str, Enum):
    RUN_QUICK_SCAN = "run_quick_scan"
    RUN_CHART_SCAN = "run_chart_scan"
    RUN_OFFICIAL_CREW = "run_official_crew"
    RUN_CUSTOM_CREW = "run_custom_crew"
    EDIT_CUSTOM_CREW = "edit_custom_crew"
    SET_BYOK_KEY = "set_byok_key"
    ATTACH_KNOWLEDGE_PACK = "attach_knowledge_pack"
    USE_PREMIUM_TOOL = "use_premium_tool"


class PolicyScope(str, Enum):
    QUICK_SCAN = "quick_scan"
    CHART_SCAN = "chart_scan"
    AGENTS_FAST = "agents_fast"
    AGENTS_BALANCED = "agents_balanced"
    AGENTS_BEST = "agents_best"


class DenialCode(str, Enum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    MODE_NOT_ALLOWED = "MODE_NOT_ALLOWED"
    SUBSCRIPTION_INACTIVE_DOWNGRADED = "SUBSCRIPTION_INACTIVE_DOWNGRADED"
    KNOWLEDGE_NOT_ALLOWED = "KNOWLEDGE_NOT_ALLOWED"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"


class RuntimeLimits(BaseModel):
    max_iterations: int
    timeout_seconds: int
    max_parallel_tools: int
    byok_allowed: bool = Field(
        ...,
        description=(
            "Permission flag: whether BYOK routing is allowed for this run intent. "
            "NOTE: byok_allowed != 'this run actually used BYOK'."
        ),
    )

    class Config:
        extra = "forbid"


class BillingHint(BaseModel):
    credits_rate_hint: int
    credits_charge_decision_source: Literal["llm_router"] = "llm_router"

    class Config:
        extra = "forbid"


class PolicyDecision(BaseModel):
    allowed: bool
    denial_code: Optional[DenialCode] = None
    denial_message: Optional[str] = None

    raw_tier: TierType
    effective_tier: TierType
    effective_tier_reason: Literal[
        "active",
        "subscription_inactive",
        "expired",
        "missing_subscription",
        "invalid_period_end",
        "community_edition",
    ]

    effective_mode: ComputingMode
    effective_scope: PolicyScope

    limits: RuntimeLimits
    billing_hint: BillingHint
    byok_used: Optional[bool] = Field(
        None,
        description=(
            "Execution result flag (optional) indicating whether BYOK was actually used. "
            "Policy decision sets permission only; runtime populates this."
        ),
    )

    class Config:
        extra = "forbid"


class EntitlementsSnapshot(BaseModel):
    raw_tier: TierType
    effective_tier: TierType
    effective_tier_reason: Literal[
        "active",
        "subscription_inactive",
        "expired",
        "missing_subscription",
        "invalid_period_end",
        "community_edition",
    ]
    downgraded: bool

    allowed_actions: List[str]
    allowed_modes: List[str]
    default_mode: ComputingMode

    limits: RuntimeLimits
    config_fingerprint: str
    evaluated_at_utc: datetime

    class Config:
        extra = "forbid"
