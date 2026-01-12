"""Billing API Endpoints - Stripe subscription management

SECURITY: This module implements Stripe webhook signature verification
to prevent unauthorized access and payment bypass attacks.

API Layer - Thin orchestration, business logic in StripeService
"""

import logging
import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.security import get_current_user, get_db
from AICrews.database.models import User, Subscription, Invoice
from AICrews.services.stripe_service import StripeService
from AICrews.schemas.billing import (
    SubscriptionResponse,
    InvoiceResponse,
    InvoiceListResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PortalSessionRequest,
    PortalSessionResponse,
)
from AICrews.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])

# Stripe webhook secret from environment
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


def get_stripe_service(db: Session = Depends(get_db)) -> StripeService:
    """Dependency injection for StripeService"""
    return StripeService(db)


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get current subscription",
    description="Returns the current user's subscription details including status and billing period"
)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's subscription details

    Returns:
        SubscriptionResponse: Current subscription with Stripe IDs, status, and period info

    Raises:
        404: No subscription found for user
    """
    stmt = select(Subscription).where(Subscription.user_id == current_user.id)
    subscription = db.execute(stmt).scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )

    return SubscriptionResponse.model_validate(subscription)


@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    summary="Get invoice history",
    description="Returns paginated list of invoices for the current user"
)
async def get_invoices(
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get paginated invoice history for current user

    Args:
        page: Page number (starts at 1)
        limit: Items per page (max 100)

    Returns:
        InvoiceListResponse: List of invoices with pagination metadata
    """
    from sqlalchemy import func

    # Validate pagination parameters
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1"
        )
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100"
        )

    # Get total count
    count_stmt = select(func.count()).select_from(Invoice).where(
        Invoice.user_id == current_user.id
    )
    total = db.execute(count_stmt).scalar()

    # Get invoices
    offset = (page - 1) * limit
    stmt = (
        select(Invoice)
        .where(Invoice.user_id == current_user.id)
        .order_by(Invoice.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    invoices = db.execute(stmt).scalars().all()

    return InvoiceListResponse(
        invoices=[InvoiceResponse.model_validate(inv) for inv in invoices],
        total=total,
        has_more=(offset + limit) < total
    )


@router.post(
    "/checkout",
    response_model=CheckoutSessionResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Create checkout session",
    description="Creates a Stripe checkout session for subscription purchase"
)
async def create_checkout(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    service: StripeService = Depends(get_stripe_service),
):
    """Create Stripe checkout session for subscription purchase

    Args:
        request: Checkout session parameters (price_id, success_url, cancel_url)

    Returns:
        CheckoutSessionResponse: Checkout URL and session ID for redirect

    Raises:
        400: Invalid price_id or user already has active subscription
        500: Stripe API error
    """
    try:
        # Get user_id before service call to avoid session detachment issues
        user_id = current_user.id

        checkout_url = service.create_checkout_session(
            user_id=user_id,
            price_id=request.price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        # Extract session ID from URL
        # Format: https://checkout.stripe.com/c/pay/cs_test_abc123...
        session_id = checkout_url.split("/")[-1] if "/" in checkout_url else "unknown"

        logger.info(f"Created checkout session for user {user_id}")
        return CheckoutSessionResponse(url=checkout_url, session_id=session_id)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )
    except Exception as e:
        logger.error(f"Checkout creation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


@router.post(
    "/portal",
    response_model=PortalSessionResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Create billing portal session",
    description="Creates a Stripe billing portal session for subscription management"
)
async def create_portal(
    request: PortalSessionRequest,
    current_user: User = Depends(get_current_user),
    service: StripeService = Depends(get_stripe_service),
):
    """Create Stripe billing portal session

    The billing portal allows users to:
    - Update payment methods
    - View invoice history
    - Cancel subscriptions
    - Update billing information

    Args:
        request: Portal session parameters (return_url)

    Returns:
        PortalSessionResponse: Portal URL for redirect

    Raises:
        400: No Stripe customer found for user
        500: Stripe API error
    """
    try:
        # Get user_id before service call to avoid session detachment issues
        user_id = current_user.id

        portal_url = service.create_portal_session(
            user_id=user_id,
            return_url=request.return_url,
        )

        logger.info(f"Created portal session for user {user_id}")
        return PortalSessionResponse(url=portal_url)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe portal error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session"
        )
    except Exception as e:
        logger.error(f"Portal creation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session"
        )


@router.post(
    "/webhook",
    status_code=200,
    summary="Stripe webhook handler",
    description=(
        "SECURITY: Handles Stripe webhook events with signature verification.\n\n"
        "This endpoint verifies the webhook signature using Stripe's SDK before "
        "processing events to prevent unauthorized access and payment bypass attacks.\n\n"
        "Supported events:\n"
        "- customer.subscription.created\n"
        "- customer.subscription.updated\n"
        "- customer.subscription.deleted\n"
        "- invoice.paid\n"
        "- invoice.payment_failed"
    )
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    service: StripeService = Depends(get_stripe_service),
):
    """
    Handle Stripe webhook events with signature verification

    SECURITY IMPLEMENTATION:
    ======================
    This endpoint implements webhook signature verification using
    stripe.Webhook.construct_event() to prevent the following attacks:

    1. Payment Bypass: Attackers cannot forge subscription.created events
    2. Subscription Manipulation: Cannot fake status updates
    3. Invoice Fraud: Cannot create fake paid invoices
    4. Replay Attacks: Stripe's timestamp validation prevents replay

    The verification process:
    1. Extract raw request body (not parsed JSON)
    2. Extract Stripe-Signature header
    3. Verify signature using Stripe SDK + webhook secret
    4. Only process events that pass verification

    Args:
        request: Raw FastAPI request (for body access)
        stripe_signature: Stripe-Signature header value

    Returns:
        200: Event processed successfully or already processed (idempotent)
        400: Invalid signature or missing header
        500: Webhook secret not configured

    Note:
        - Returns 200 even on processing errors to prevent Stripe retries
        - Processing errors are logged for manual review
        - Idempotent: duplicate events are safely ignored
    """
    # Validate webhook secret is configured
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )

    # Validate signature header is present
    if not stripe_signature:
        logger.warning("Webhook request missing stripe-signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header"
        )

    # Get raw body (required for signature verification)
    payload = await request.body()

    try:
        # CRITICAL SECURITY: Verify webhook signature
        # This prevents unauthorized webhook events from being processed
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )

        logger.info(
            f"Received verified webhook: {event['type']} "
            f"(ID: {event['id']}, Livemode: {event.get('livemode', False)})"
        )

        # Process event (idempotent - safe to call multiple times)
        service.handle_webhook_event(
            event_id=event['id'],
            event_type=event['type'],
            event_data=event['data']
        )

        return {"status": "success", "event_id": event['id']}

    except stripe.error.SignatureVerificationError as e:
        # SECURITY: Invalid signature - reject the request
        logger.warning(f"Invalid webhook signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    except ValueError as e:
        # Invalid payload format
        logger.warning(f"Invalid webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except Exception as e:
        # Processing error - return 200 to prevent Stripe retries
        # (Idempotency ensures we can manually retry later)
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Event received but processing failed",
            "detail": str(e)
        }
