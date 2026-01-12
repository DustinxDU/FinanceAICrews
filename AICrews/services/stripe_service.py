"""
Stripe Service - Stripe integration for subscription management

Provides production-ready Stripe integration with:
- Idempotent customer creation
- Checkout session management
- Billing portal access
- Webhook event processing with idempotency guarantees

SECURITY NOTE: Webhook Signature Verification
==============================================
All webhook events MUST be verified using Stripe signature verification
in the API endpoint layer BEFORE calling handle_webhook_event().

Without signature verification, attackers can forge webhook events to:
- Bypass payment verification
- Manipulate subscriptions
- Create fake invoices
- Grant unauthorized access

Example (to be implemented in API endpoint):
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        stripe_service.handle_webhook_event(
            event.id, event.type, event.data
        )
    except stripe.error.SignatureVerificationError:
        # Invalid signature - reject the request
        raise HTTPException(status_code=400, detail="Invalid signature")
"""

from __future__ import annotations

from AICrews.observability.logging import get_logger
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import stripe
from sqlalchemy.orm import Session
from sqlalchemy import select

from AICrews.database.models import User, Subscription, Invoice, StripeEvent
from AICrews.services.entitlements.stripe_price_mapping import map_price_to_tier
from AICrews.services.notification_service import NotificationService

logger = get_logger(__name__)

# Configure Stripe API key from environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class StripeService:
    """Service for Stripe subscription management with idempotent operations"""

    def __init__(self, db: Session):
        """Initialize Stripe service

        Args:
            db: Database session
        """
        self.db = db

    @staticmethod
    def _to_utc(ts: Optional[int]) -> Optional[datetime]:
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    def _set_user_tier(self, user_id: int, tier: str) -> None:
        tier_normalized = tier if tier in {"free", "starter", "pro"} else "free"
        user = self.db.get(User, user_id)
        if not user:
            return
        user.subscription_level = tier_normalized
        self.db.commit()

    def create_or_get_customer(self, user_id: int) -> str:
        """
        Create or get Stripe customer ID for user (idempotent)

        This method ensures only one Stripe customer is created per user,
        even if called multiple times.

        Args:
            user_id: User ID

        Returns:
            stripe_customer_id: Stripe customer ID

        Raises:
            ValueError: If user not found
        """
        # Check if subscription exists with customer_id
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        subscription = self.db.execute(stmt).scalar_one_or_none()

        if subscription and subscription.stripe_customer_id:
            logger.debug(f"Found existing Stripe customer {subscription.stripe_customer_id} for user {user_id}")
            return subscription.stripe_customer_id

        # Get user
        user_stmt = select(User).where(User.id == user_id)
        user = self.db.execute(user_stmt).scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Create Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name or user.username,
            metadata={"user_id": str(user_id)}
        )

        # Save to database
        if subscription:
            subscription.stripe_customer_id = customer.id
        else:
            subscription = Subscription(
                user_id=user_id,
                stripe_customer_id=customer.id,
                status="incomplete"
            )
            self.db.add(subscription)

        self.db.commit()
        logger.info(f"Created Stripe customer {customer.id} for user {user_id}")

        return customer.id

    def create_checkout_session(
        self,
        user_id: int,
        price_id: str,
        success_url: str,
        cancel_url: str
    ) -> str:
        """
        Create Stripe checkout session for subscription

        Args:
            user_id: User ID
            price_id: Stripe price ID (e.g., price_xxx)
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect after canceled payment

        Returns:
            checkout_session.url: URL to redirect user to checkout

        Raises:
            ValueError: If user not found
        """
        customer_id = self.create_or_get_customer(user_id)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user_id)}
        )

        logger.info(f"Created checkout session {session.id} for user {user_id}")
        return session.url

    def create_portal_session(self, user_id: int, return_url: str) -> str:
        """
        Create Stripe billing portal session

        Allows users to manage their subscription, payment methods, and invoices.

        Args:
            user_id: User ID
            return_url: URL to redirect after portal session

        Returns:
            portal_session.url: URL to redirect user to billing portal

        Raises:
            ValueError: If no Stripe customer found for user
        """
        # Get customer (must exist)
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        subscription = self.db.execute(stmt).scalar_one_or_none()

        if not subscription or not subscription.stripe_customer_id:
            raise ValueError(f"No Stripe customer found for user {user_id}")

        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=return_url
        )

        logger.info(f"Created portal session for user {user_id}")
        return session.url

    def handle_webhook_event(
        self,
        event_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Handle Stripe webhook event with idempotency

        This method ensures each webhook event is processed exactly once,
        even if Stripe sends duplicates.

        SECURITY: This method assumes the webhook event has already been
        verified using Stripe signature verification. The API endpoint layer
        MUST verify the webhook signature before calling this method:

            stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )

        Without signature verification, attackers can forge webhook events
        to bypass payment, manipulate subscriptions, or create fake invoices.

        Args:
            event_id: Stripe event ID (for idempotency)
            event_type: Event type (e.g., "customer.subscription.created")
            event_data: Event data dict from Stripe

        Raises:
            Exception: If event processing fails
        """
        # Check if already processed (idempotency)
        stmt = select(StripeEvent).where(StripeEvent.event_id == event_id)
        existing_event = self.db.execute(stmt).scalar_one_or_none()

        if existing_event:
            if existing_event.processing_status == "processed":
                logger.info(f"Event {event_id} already processed, skipping")
                return
            # If failed or pending, try again
            logger.info(f"Retrying event {event_id} with status {existing_event.processing_status}")

        # Create event record if not exists
        if not existing_event:
            stripe_event = StripeEvent(
                event_id=event_id,
                event_type=event_type,
                processing_status="pending"
            )
            self.db.add(stripe_event)
            self.db.commit()
            self.db.refresh(stripe_event)
        else:
            stripe_event = existing_event

        try:
            # Process event based on type
            if event_type == "customer.subscription.created":
                self._handle_subscription_created(event_data)
            elif event_type == "customer.subscription.updated":
                self._handle_subscription_updated(event_data)
            elif event_type == "customer.subscription.deleted":
                self._handle_subscription_deleted(event_data)
            elif event_type == "invoice.paid":
                self._handle_invoice_paid(event_data)
            elif event_type == "invoice.payment_failed":
                self._handle_invoice_failed(event_data)
            else:
                logger.info(f"Unhandled event type: {event_type}")

            # Mark as processed
            stripe_event.processing_status = "processed"
            stripe_event.processed_at = datetime.now()
            self.db.commit()
            logger.info(f"Successfully processed event {event_id} ({event_type})")

        except Exception as e:
            logger.error(f"Error processing webhook event {event_id}: {e}", exc_info=True)
            stripe_event.processing_status = "failed"
            stripe_event.error_message = str(e)[:1000]  # Truncate to fit column
            self.db.commit()
            raise

    def _handle_subscription_created(self, data: Dict[str, Any]) -> None:
        """Handle customer.subscription.created event"""
        subscription_obj = data["object"]
        customer_id = subscription_obj["customer"]

        # Find subscription by customer_id
        stmt = select(Subscription).where(
            Subscription.stripe_customer_id == customer_id
        )
        subscription = self.db.execute(stmt).scalar_one_or_none()

        if subscription:
            subscription.stripe_subscription_id = subscription_obj["id"]
            subscription.stripe_price_id = subscription_obj["items"]["data"][0]["price"]["id"]
            subscription.status = subscription_obj["status"]
            subscription.current_period_start = self._to_utc(subscription_obj["current_period_start"])
            subscription.current_period_end = self._to_utc(subscription_obj["current_period_end"])
            subscription.cancel_at_period_end = subscription_obj.get("cancel_at_period_end", False)
            self.db.commit()
            logger.info(f"Created subscription {subscription_obj['id']} for customer {customer_id}")

            self._set_user_tier(subscription.user_id, map_price_to_tier(subscription.stripe_price_id))

            # Emit webhook event (best-effort, after all DB operations)
            NotificationService(self.db).emit_event(
                subscription.user_id,
                "billing.subscription_created",
                {
                    "subscription_id": subscription_obj["id"],
                    "price_id": subscription.stripe_price_id,
                    "status": subscription_obj["status"],
                },
            )
        else:
            logger.warning(f"No subscription record found for customer {customer_id}")

    def _handle_subscription_updated(self, data: Dict[str, Any]) -> None:
        """Handle customer.subscription.updated event"""
        subscription_obj = data["object"]

        stmt = select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_obj["id"]
        )
        subscription = self.db.execute(stmt).scalar_one_or_none()

        if subscription:
            subscription.status = subscription_obj["status"]
            subscription.current_period_start = self._to_utc(subscription_obj["current_period_start"])
            subscription.current_period_end = self._to_utc(subscription_obj["current_period_end"])
            subscription.cancel_at_period_end = subscription_obj.get("cancel_at_period_end", False)
            subscription.stripe_price_id = subscription_obj["items"]["data"][0]["price"]["id"]

            if subscription_obj.get("canceled_at"):
                subscription.canceled_at = self._to_utc(subscription_obj["canceled_at"])

            self.db.commit()
            logger.info(f"Updated subscription {subscription_obj['id']}")

            self._set_user_tier(subscription.user_id, map_price_to_tier(subscription.stripe_price_id))

            # Emit webhook event (best-effort, after all DB operations)
            NotificationService(self.db).emit_event(
                subscription.user_id,
                "billing.subscription_updated",
                {
                    "subscription_id": subscription_obj["id"],
                    "price_id": subscription.stripe_price_id,
                    "status": subscription_obj["status"],
                    "cancel_at_period_end": subscription_obj.get("cancel_at_period_end", False),
                },
            )
        else:
            logger.warning(f"No subscription found for subscription_id {subscription_obj['id']}")

    def _handle_subscription_deleted(self, data: Dict[str, Any]) -> None:
        """Handle customer.subscription.deleted event"""
        subscription_obj = data["object"]

        stmt = select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_obj["id"]
        )
        subscription = self.db.execute(stmt).scalar_one_or_none()

        if subscription:
            subscription.status = "canceled"
            subscription.canceled_at = datetime.now()
            self.db.commit()
            logger.info(f"Deleted subscription {subscription_obj['id']}")
            self._set_user_tier(subscription.user_id, "free")

            # Emit webhook event (best-effort, after all DB operations)
            NotificationService(self.db).emit_event(
                subscription.user_id,
                "billing.subscription_deleted",
                {
                    "subscription_id": subscription_obj["id"],
                },
            )
        else:
            logger.warning(f"No subscription found for subscription_id {subscription_obj['id']}")

    def _handle_invoice_paid(self, data: Dict[str, Any]) -> None:
        """Handle invoice.paid event"""
        invoice_obj = data["object"]

        # Find user by customer_id
        customer_id = invoice_obj["customer"]
        stmt = select(Subscription).where(
            Subscription.stripe_customer_id == customer_id
        )
        subscription = self.db.execute(stmt).scalar_one_or_none()

        if not subscription:
            logger.warning(f"No subscription found for customer {customer_id}")
            return

        # Create or update invoice
        invoice_stmt = select(Invoice).where(
            Invoice.stripe_invoice_id == invoice_obj["id"]
        )
        invoice = self.db.execute(invoice_stmt).scalar_one_or_none()

        if not invoice:
            invoice = Invoice(
                user_id=subscription.user_id,
                stripe_invoice_id=invoice_obj["id"],
                stripe_subscription_id=invoice_obj.get("subscription"),
                amount=invoice_obj["amount_paid"],
                currency=invoice_obj["currency"],
                status="paid",
                invoice_pdf=invoice_obj.get("invoice_pdf"),
                hosted_invoice_url=invoice_obj.get("hosted_invoice_url"),
                period_start=datetime.fromtimestamp(invoice_obj["period_start"]),
                period_end=datetime.fromtimestamp(invoice_obj["period_end"])
            )
            self.db.add(invoice)
        else:
            invoice.status = "paid"
            invoice.amount = invoice_obj["amount_paid"]

        self.db.commit()
        logger.info(f"Processed paid invoice {invoice_obj['id']}")

        # Emit webhook event (best-effort, after all DB operations)
        NotificationService(self.db).emit_event(
            subscription.user_id,
            "billing.invoice_paid",
            {
                "invoice_id": invoice_obj["id"],
                "subscription_id": invoice_obj.get("subscription"),
                "amount": invoice_obj["amount_paid"],
                "currency": invoice_obj["currency"],
            },
        )

    def _handle_invoice_failed(self, data: Dict[str, Any]) -> None:
        """Handle invoice.payment_failed event"""
        invoice_obj = data["object"]

        stmt = select(Invoice).where(
            Invoice.stripe_invoice_id == invoice_obj["id"]
        )
        invoice = self.db.execute(stmt).scalar_one_or_none()

        if invoice:
            invoice.status = "uncollectible"
            self.db.commit()
            logger.warning(f"Invoice payment failed: {invoice_obj['id']}")

            # Emit webhook event (best-effort, after all DB operations)
            NotificationService(self.db).emit_event(
                invoice.user_id,
                "billing.invoice_failed",
                {
                    "invoice_id": invoice_obj["id"],
                    "subscription_id": invoice_obj.get("subscription"),
                },
            )
        else:
            logger.warning(f"No invoice found for invoice_id {invoice_obj['id']}")


__all__ = ["StripeService"]
