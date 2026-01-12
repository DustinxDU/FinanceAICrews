from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from AICrews.database.models.user import User
from AICrews.schemas.entitlements import DenialCode, PolicyAction
from AICrews.services.entitlements.policy_engine import EntitlementPolicyEngine


def require_entitlement(
    *,
    action: PolicyAction,
    request: Request,
    db: Session,
    current_user: User | None,
    requested_mode=None,
):
    """
    Evaluate entitlements once per request and raise a stable HTTP error on deny.

    On allow: attaches PolicyDecision to request.state.entitlements_decision and returns it.
    """
    engine = EntitlementPolicyEngine()
    decision = engine.check(db, current_user, action=action, requested_mode=requested_mode)

    if decision.allowed:
        request.state.entitlements_decision = decision
        return decision

    status = 401 if decision.denial_code == DenialCode.AUTH_REQUIRED else 403
    raise HTTPException(
        status_code=status,
        detail={
            "denial_code": (decision.denial_code.value if decision.denial_code else None),
            "message": decision.denial_message or "Denied",
            "effective_tier": decision.effective_tier.value,
            "effective_tier_reason": decision.effective_tier_reason,
        },
    )
