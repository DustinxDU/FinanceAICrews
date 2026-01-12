from __future__ import annotations

import hashlib
from AICrews.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from AICrews.database.models.billing import Subscription
from AICrews.database.models.user import User

from .community_edition import get_community_tier_info, is_self_hosted

logger = get_logger(__name__)


def resolve_effective_tier(
    db: Session,
    user: Optional[User],
    *,
    now_utc: Optional[datetime] = None,
) -> Tuple[str, str, bool, str]:
    """
    Decide effective tier with strong-consistency downgrade (fail closed).

    Community edition: all users automatically receive Pro-tier access.

    Returns (raw_tier, effective_tier, downgraded, reason)
    reason ∈ {"active","subscription_inactive","expired","missing_subscription",
              "invalid_period_end","community_edition"}
    """
    # Community edition: bypass all subscription checks
    if is_self_hosted():
        return get_community_tier_info()

    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # anonymous users are treated as free
    if user is None:
        return "free", "free", False, "missing_subscription"

    raw_tier = (getattr(user, "subscription_level", None) or "free").strip().lower()
    if raw_tier == "free":
        return "free", "free", False, "active"

    if raw_tier not in ("starter", "pro"):
        # Unknown tier → fail closed
        return raw_tier, "free", True, "missing_subscription"

    sub = db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    ).scalar_one_or_none()
    if not sub:
        return raw_tier, "free", True, "missing_subscription"

    status = (getattr(sub, "status", None) or "").lower()
    if status != "active":
        return raw_tier, "free", True, "subscription_inactive"

    period_end = getattr(sub, "current_period_end", None)
    if not isinstance(period_end, datetime):
        return raw_tier, "free", True, "invalid_period_end"
    if period_end.tzinfo is None:
        # v1 policy: treat naive as UTC to avoid surprising downgrades when DB stores naive
        user_hash = None
        if user and getattr(user, "id", None) is not None:
            user_hash = hashlib.sha256(str(user.id).encode("utf-8")).hexdigest()[:8]
        logger.warning(
            "Entitlements: naive current_period_end encountered; treating as UTC",
            extra={"user_id_hash": user_hash},
        )
        period_end = period_end.replace(tzinfo=timezone.utc)
    period_end_utc = period_end.astimezone(timezone.utc)

    if now >= period_end_utc:
        return raw_tier, "free", True, "expired"

    return raw_tier, raw_tier, False, "active"
