"""System status endpoints for backend operations.

SECURITY: All endpoints require authentication.
Admin-only operations require require_admin dependency.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from AICrews.database.models import User
from AICrews.services.daily_archiver_service import get_daily_archiver_service
from AICrews.services.unified_sync_service import get_unified_sync_service
from backend.app.security import get_current_user, require_admin

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/sync-status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get unified sync service status. Requires authentication."""
    return get_unified_sync_service().get_status()


@router.get("/archiver-status")
async def get_archiver_status(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get daily archiver service status. Requires authentication."""
    return await get_daily_archiver_service().get_archival_status()


@router.post("/force-archive/{market}")
async def force_archive_market(
    market: str,
    admin_user: User = Depends(require_admin),
) -> Dict[str, Any]:
    """Manually trigger market archival. Requires admin privileges."""
    return await get_daily_archiver_service().force_archive_market(market)

