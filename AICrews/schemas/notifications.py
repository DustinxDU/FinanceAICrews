from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, HttpUrl

from AICrews.schemas.common import BaseSchema


class WebhookSettingsRequest(BaseSchema):
    webhook_url: HttpUrl = Field(...)
    shared_secret: str = Field(..., min_length=1)


class WebhookSettingsResponse(BaseSchema):
    webhook_url: str
    last_status: str
    last_error: str | None = None
    last_delivery_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WebhookTestResponse(BaseSchema):
    """Response from sending a test webhook."""
    status: str  # "success" or "failed"
    error: str | None = None


class WebhookEventPayload(BaseSchema):
    event_type: str
    occurred_at: datetime
    user_id: int
    data: Any
