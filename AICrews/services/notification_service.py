"""
Notification Service - System Webhook Notifications

Handles system-level webhook notifications using environment variables.
User notification preferences are handled by UserNotificationService.
"""

import hashlib
import hmac
import json
from AICrews.observability.logging import get_logger
import os
from datetime import datetime
from typing import Any, Optional

import httpx

logger = get_logger(__name__)


class WebhookNotConfiguredError(Exception):
    """Raised when attempting to send webhook without configuration."""
    pass


class NotificationService:
    """
    System-level notification service.

    Webhook configuration is read from environment variables:
    - SYSTEM_WEBHOOK_URL: Webhook endpoint URL
    - SYSTEM_WEBHOOK_SECRET: HMAC secret for signing
    - SYSTEM_WEBHOOK_ENABLED: true/false to enable

    Note: User notification preferences are handled by UserNotificationService.
    """

    def __init__(self, db=None):
        """Initialize notification service.

        Args:
            db: Optional database session (not needed for env-based webhooks)
        """
        self.db = db

    def _get_system_webhook_config(self) -> Optional[dict]:
        """
        Get system webhook configuration from environment variables.

        Returns:
            dict with webhook_url and shared_secret, or None if not configured
        """
        webhook_url = os.getenv("SYSTEM_WEBHOOK_URL", "").strip()
        webhook_secret = os.getenv("SYSTEM_WEBHOOK_SECRET", "").strip()
        webhook_enabled = os.getenv("SYSTEM_WEBHOOK_ENABLED", "false").lower() == "true"

        if not webhook_enabled or not webhook_url or not webhook_secret:
            return None

        return {
            "webhook_url": webhook_url,
            "shared_secret": webhook_secret,
        }

    def send_test_webhook(self, user_id: int) -> dict[str, Any]:
        """
        Send a test webhook using system configuration.

        Args:
            user_id: User ID (for logging purposes)

        Returns:
            dict with status and optional error

        Raises:
            WebhookNotConfiguredError: If system webhook not configured
        """
        config = self._get_system_webhook_config()

        if not config:
            logger.warning(f"System webhook not configured for test by user {user_id}")
            raise WebhookNotConfiguredError("System webhook not configured")

        # Create test payload
        payload = {
            "event_type": "notifications.test",
            "occurred_at": datetime.now().isoformat(),
            "data": {
                "message": "Test webhook from FinanceAICrews",
                "triggered_by_user_id": user_id,
            }
        }

        # Deliver with retries
        result = self._deliver_webhook(
            config["webhook_url"],
            config["shared_secret"],
            payload,
            max_retries=2
        )

        logger.info(f"Test webhook {'succeeded' if result['status'] == 'success' else 'failed'} for user {user_id}")
        return result

    def emit_event(self, event_type: str, data: Any, user_id: Optional[int] = None) -> None:
        """Emit an event to system webhook (best-effort).

        This method fails silently if webhook is not configured, making it
        safe to call from any part of the application without error handling.

        Args:
            event_type: Event type (e.g., "billing.invoice_paid", "jobs.analysis_completed")
            data: Event-specific data payload
            user_id: Optional user ID related to event
        """
        config = self._get_system_webhook_config()
        if not config:
            # No webhook configured - silent return (best-effort delivery)
            return

        # Build webhook payload
        payload = {
            "event_type": event_type,
            "occurred_at": datetime.now().isoformat(),
            "data": data,
        }
        if user_id is not None:
            payload["user_id"] = user_id

        # Deliver with retries (best-effort, don't propagate errors)
        try:
            result = self._deliver_webhook(
                config["webhook_url"],
                config["shared_secret"],
                payload,
                max_retries=2
            )
            if result["status"] != "success":
                logger.warning(f"System webhook delivery failed for {event_type}: {result.get('error')}")
        except Exception as e:
            logger.warning(f"System webhook delivery exception for {event_type}: {e}")

    # Helper methods
    def _serialize_payload(self, payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")

    def _sign_payload(self, secret: str, body: bytes) -> str:
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def _should_retry(self, status_code: Optional[int], error: Optional[Exception]) -> bool:
        if error is not None:
            return True
        if status_code is None:
            return True
        if 500 <= status_code <= 599:
            return True
        return False

    def _deliver_webhook(
        self, url: str, secret: str, payload: dict[str, Any], max_retries: int = 2
    ) -> dict[str, Any]:
        """Deliver webhook with signing, timeout, and retries."""
        body = self._serialize_payload(payload)
        signature = self._sign_payload(secret, body)
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        }

        attempts = 0
        last_error: Optional[str] = None

        while attempts <= max_retries:
            attempts += 1
            try:
                resp = httpx.post(url, content=body, headers=headers, timeout=5.0)
                if 200 <= resp.status_code < 300:
                    return {"status": "success"}
                elif self._should_retry(resp.status_code, None) and attempts <= max_retries:
                    last_error = f"HTTP {resp.status_code}"
                    continue
                else:
                    return {"status": "failed", "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                last_error = str(e)
                if attempts <= max_retries:
                    continue
                return {"status": "failed", "error": last_error}

        return {"status": "failed", "error": last_error or "Unknown error"}


__all__ = ["NotificationService", "WebhookNotConfiguredError"]
