"""Notifications API (system webhook).

This endpoint surface is intentionally lightweight and stable:
- Read-only webhook settings are sourced from environment variables.
- Test delivery delegates to `AICrews.services.notification_service.NotificationService`.

Note: User notification preferences are handled via `/user-preferences/notifications`.
"""

import os

from fastapi import APIRouter, Depends, HTTPException

from AICrews.database.models import User
from AICrews.schemas.notifications import (
    WebhookSettingsRequest,
    WebhookSettingsResponse,
    WebhookTestResponse,
)
from AICrews.services.notification_service import (
    NotificationService,
    WebhookNotConfiguredError,
)
from backend.app.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "/webhook",
    response_model=WebhookSettingsResponse,
    summary="Get system webhook settings",
)
async def get_webhook_settings(
    current_user: User = Depends(get_current_user),
) -> WebhookSettingsResponse:
    """Return system webhook configuration (read-only)."""
    webhook_url = os.getenv("SYSTEM_WEBHOOK_URL", "").strip()
    webhook_enabled = os.getenv("SYSTEM_WEBHOOK_ENABLED", "false").lower() == "true"
    secret_present = bool(os.getenv("SYSTEM_WEBHOOK_SECRET", "").strip())

    status = "configured" if (webhook_enabled and webhook_url and secret_present) else "not_configured"

    return WebhookSettingsResponse(
        webhook_url=webhook_url,
        last_status=status,
        last_error=None,
        last_delivery_at=None,
    )


@router.put(
    "/webhook",
    response_model=WebhookSettingsResponse,
    summary="Update system webhook settings",
)
async def update_webhook_settings(
    body: WebhookSettingsRequest,
    current_user: User = Depends(get_current_user),
) -> WebhookSettingsResponse:
    """Update webhook settings (deprecated; env-configured in this deployment)."""
    raise HTTPException(
        status_code=501,
        detail="System webhook settings are configured via environment variables.",
    )


@router.post(
    "/webhook/test",
    response_model=WebhookTestResponse,
    summary="Send a test webhook",
)
async def send_test_webhook(
    current_user: User = Depends(get_current_user),
) -> WebhookTestResponse:
    """Send a test webhook using current system configuration."""
    svc = NotificationService()
    try:
        result = svc.send_test_webhook(current_user.id)
        return WebhookTestResponse(
            status=str(result.get("status") or "failed"),
            error=result.get("error"),
        )
    except WebhookNotConfiguredError as e:
        return WebhookTestResponse(status="failed", error=str(e))
    except Exception as e:
        return WebhookTestResponse(status="failed", error=str(e))
