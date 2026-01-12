import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.security import get_db, get_current_user_optional
from AICrews.database.models import User
from AICrews.services.entitlements.policy_engine import EntitlementPolicyEngine
from AICrews.schemas.entitlements import EntitlementsSnapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/entitlements", tags=["Entitlements"])


@router.get("/me", response_model=EntitlementsSnapshot)
async def entitlements_me(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> EntitlementsSnapshot:
    """
    Frontend gating snapshot: returns declarative capabilities for the current user (or anonymous).
    """
    engine = EntitlementPolicyEngine()
    snapshot = engine.snapshot(db, current_user)
    return snapshot
