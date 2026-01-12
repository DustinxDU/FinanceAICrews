"""
Billing Schemas - Pydantic v2 models for billing/subscription APIs

Provides comprehensive schemas for Stripe integration including:
- Subscription management
- Invoice records
- Checkout session creation
- Billing portal access
- Webhook event handling
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, HttpUrl

from AICrews.schemas.common import BaseSchema


class SubscriptionResponse(BaseSchema):
    """
    User subscription details

    Returned by GET /api/v1/billing/subscription
    Maps to Subscription database model
    """
    id: int = Field(..., description="Subscription record ID")
    user_id: int = Field(..., description="User ID")
    stripe_customer_id: str = Field(..., description="Stripe customer ID (cus_*)")
    stripe_subscription_id: Optional[str] = Field(None, description="Stripe subscription ID (sub_*)")
    stripe_price_id: Optional[str] = Field(None, description="Stripe price ID (price_*)")
    status: str = Field(..., description="Subscription status: active, canceled, past_due, trialing, incomplete, incomplete_expired, unpaid")
    current_period_start: Optional[datetime] = Field(None, description="Current billing period start timestamp")
    current_period_end: Optional[datetime] = Field(None, description="Current billing period end timestamp")
    cancel_at_period_end: bool = Field(False, description="Whether subscription will cancel at period end")
    canceled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    created_at: datetime = Field(..., description="Subscription creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 123,
                "stripe_customer_id": "cus_ABC123XYZ",
                "stripe_subscription_id": "sub_XYZ789ABC",
                "stripe_price_id": "price_1MonthlyPlan",
                "status": "active",
                "current_period_start": "2026-01-01T00:00:00Z",
                "current_period_end": "2026-02-01T00:00:00Z",
                "cancel_at_period_end": False,
                "canceled_at": None,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T12:30:00Z"
            }
        }
    )


class InvoiceResponse(BaseSchema):
    """
    Invoice details

    Returned by GET /api/v1/billing/invoices
    Maps to Invoice database model
    """
    id: int = Field(..., description="Invoice record ID")
    user_id: int = Field(..., description="User ID")
    stripe_invoice_id: str = Field(..., description="Stripe invoice ID (in_*)")
    stripe_subscription_id: Optional[str] = Field(None, description="Associated subscription ID (sub_*)")
    amount: int = Field(..., description="Invoice amount in cents (e.g., 2999 = $29.99)")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    status: str = Field(..., description="Invoice status: draft, open, paid, void, uncollectible")
    invoice_pdf: Optional[str] = Field(None, description="URL to invoice PDF")
    hosted_invoice_url: Optional[str] = Field(None, description="URL to hosted invoice page")
    period_start: Optional[datetime] = Field(None, description="Billing period start timestamp")
    period_end: Optional[datetime] = Field(None, description="Billing period end timestamp")
    created_at: datetime = Field(..., description="Invoice creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 42,
                "user_id": 123,
                "stripe_invoice_id": "in_1A2B3C4D5E6F",
                "stripe_subscription_id": "sub_XYZ789ABC",
                "amount": 2999,
                "currency": "usd",
                "status": "paid",
                "invoice_pdf": "https://pay.stripe.com/invoice/acct_xxx/invst_xxx/pdf",
                "hosted_invoice_url": "https://invoice.stripe.com/i/acct_xxx/invst_xxx",
                "period_start": "2026-01-01T00:00:00Z",
                "period_end": "2026-02-01T00:00:00Z",
                "created_at": "2026-01-01T00:00:00Z"
            }
        }
    )


class CheckoutSessionRequest(BaseSchema):
    """
    Request to create Stripe checkout session

    Used by POST /api/v1/billing/checkout
    """
    price_id: str = Field(
        ...,
        min_length=1,
        description="Stripe price ID (must start with 'price_')"
    )
    success_url: str = Field(
        ...,
        description="Full URL to redirect after successful payment"
    )
    cancel_url: str = Field(
        ...,
        description="Full URL to redirect if user cancels"
    )

    @field_validator('price_id')
    @classmethod
    def validate_price_id(cls, v: str) -> str:
        """Validate Stripe price ID format"""
        if not v.startswith('price_'):
            raise ValueError("price_id must start with 'price_' (e.g., 'price_1MonthlyPlan')")
        return v

    @field_validator('success_url', 'cancel_url')
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price_id": "price_1MonthlyPlan",
                "success_url": "https://example.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": "https://example.com/billing/cancel"
            }
        }
    )


class CheckoutSessionResponse(BaseSchema):
    """
    Checkout session response with redirect URL

    Returned by POST /api/v1/billing/checkout
    Frontend should redirect user to this URL
    """
    url: str = Field(..., description="Stripe checkout session URL for redirect")
    session_id: str = Field(..., description="Checkout session ID for tracking")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://checkout.stripe.com/c/pay/cs_test_abc123xyz789",
                "session_id": "cs_test_abc123xyz789"
            }
        }
    )


class PortalSessionRequest(BaseSchema):
    """
    Request to create Stripe billing portal session

    Used by POST /api/v1/billing/portal
    """
    return_url: str = Field(
        ...,
        description="Full URL to return to after portal exit"
    )

    @field_validator('return_url')
    @classmethod
    def validate_return_url(cls, v: str) -> str:
        """Validate return URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("return_url must start with http:// or https://")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "return_url": "https://example.com/settings/billing"
            }
        }
    )


class PortalSessionResponse(BaseSchema):
    """
    Portal session response with redirect URL

    Returned by POST /api/v1/billing/portal
    Frontend should redirect user to Stripe billing portal
    """
    url: str = Field(..., description="Stripe billing portal URL for redirect")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://billing.stripe.com/p/session/test_abc123xyz789"
            }
        }
    )


class WebhookEventRequest(BaseSchema):
    """
    Stripe webhook event payload

    Used by POST /api/v1/billing/webhook (for API documentation only)
    Note: Actual webhook validation uses raw request body + Stripe signature
    This schema is for documentation purposes
    """
    id: str = Field(..., description="Unique event ID (evt_*)")
    type: str = Field(..., description="Event type (e.g., 'customer.subscription.updated')")
    data: Dict[str, Any] = Field(..., description="Event data object")
    created: int = Field(..., description="Event creation timestamp (Unix)")
    livemode: bool = Field(..., description="Whether event is from live mode")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "evt_1A2B3C4D5E6F",
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        "id": "sub_XYZ789ABC",
                        "status": "active",
                        "customer": "cus_ABC123XYZ"
                    }
                },
                "created": 1704153600,
                "livemode": False
            }
        }
    )


class SubscriptionCancelRequest(BaseSchema):
    """
    Request to cancel subscription

    Used by POST /api/v1/billing/subscription/cancel
    """
    cancel_at_period_end: bool = Field(
        True,
        description="If True, cancel at period end; if False, cancel immediately"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cancel_at_period_end": True
            }
        }
    )


class SubscriptionCancelResponse(BaseSchema):
    """
    Response after subscription cancellation

    Returned by POST /api/v1/billing/subscription/cancel
    """
    message: str = Field(..., description="Success message")
    subscription: SubscriptionResponse = Field(..., description="Updated subscription details")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Subscription will be canceled at the end of the current billing period",
                "subscription": {
                    "id": 1,
                    "user_id": 123,
                    "stripe_customer_id": "cus_ABC123XYZ",
                    "stripe_subscription_id": "sub_XYZ789ABC",
                    "stripe_price_id": "price_1MonthlyPlan",
                    "status": "active",
                    "current_period_start": "2026-01-01T00:00:00Z",
                    "current_period_end": "2026-02-01T00:00:00Z",
                    "cancel_at_period_end": True,
                    "canceled_at": "2026-01-15T12:00:00Z",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-15T12:00:00Z"
                }
            }
        }
    )


class InvoiceListResponse(BaseSchema):
    """
    Paginated list of invoices

    Returned by GET /api/v1/billing/invoices
    """
    invoices: list[InvoiceResponse] = Field(..., description="List of invoices")
    total: int = Field(..., description="Total number of invoices")
    has_more: bool = Field(False, description="Whether more invoices are available")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "invoices": [
                    {
                        "id": 42,
                        "user_id": 123,
                        "stripe_invoice_id": "in_1A2B3C4D5E6F",
                        "stripe_subscription_id": "sub_XYZ789ABC",
                        "amount": 2999,
                        "currency": "usd",
                        "status": "paid",
                        "invoice_pdf": "https://pay.stripe.com/invoice/pdf",
                        "hosted_invoice_url": "https://invoice.stripe.com/i/...",
                        "period_start": "2026-01-01T00:00:00Z",
                        "period_end": "2026-02-01T00:00:00Z",
                        "created_at": "2026-01-01T00:00:00Z"
                    }
                ],
                "total": 12,
                "has_more": True
            }
        }
    )


__all__ = [
    "SubscriptionResponse",
    "InvoiceResponse",
    "CheckoutSessionRequest",
    "CheckoutSessionResponse",
    "PortalSessionRequest",
    "PortalSessionResponse",
    "WebhookEventRequest",
    "SubscriptionCancelRequest",
    "SubscriptionCancelResponse",
    "InvoiceListResponse",
]
