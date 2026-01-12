"""
Provisioner Service - Virtual Key Lifecycle Management

This module implements the core state machine for managing LiteLLM virtual keys:
- PROVISIONING → ACTIVE (successful provisioning)
- PROVISIONING → FAILED (error with retry)
- Batch reconciliation with SELECT FOR UPDATE SKIP LOCKED
- Exponential backoff with cap (max 300s)
- Max retries enforcement

Key Design Principles:
- State machine driven: Pure logic, no HTTP in core methods
- Idempotent: Safe to retry (key_alias based)
- Concurrent-safe: SELECT FOR UPDATE SKIP LOCKED
- Observable: Returns detailed statistics
"""

from AICrews.observability.logging import get_logger
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from AICrews.database.models.llm_policy import LLMVirtualKey, VirtualKeyStatusEnum
from AICrews.services.litellm_admin_client import (
    LiteLLMAdminClient,
    LiteLLMAdminError,
)
from AICrews.utils.encryption import encrypt_api_key

logger = get_logger(__name__)


class ProvisioningResult(str, Enum):
    """Result of processing a single provisioning key."""

    SUCCESS = "success"
    FAILED_RETRY = "failed_retry"
    SKIPPED_MAX_RETRIES = "skipped_max_retries"


class ProvisionerService:
    """
    Service for provisioning and managing LiteLLM virtual keys.

    This service handles the complete lifecycle of virtual keys:
    - Creating PROVISIONING records
    - Calling LiteLLM Admin API to generate keys
    - Encrypting and storing keys in DB
    - Managing retry logic with exponential backoff
    - Batch reconciliation with concurrency safety

    Example:
        ```python
        admin_client = LiteLLMAdminClient(...)
        service = ProvisionerService(admin_client=admin_client)

        # Process all pending provisioning
        stats = await service.reconcile(db=db, limit=50)

        # Provision specific user
        await service.provision_user(user_id=123, db=db)
        ```
    """

    def __init__(
        self,
        admin_client: Optional[LiteLLMAdminClient] = None,
        max_retries: int = 10,
        max_backoff_seconds: int = 300,
    ):
        """
        Initialize Provisioner Service.

        Args:
            admin_client: LiteLLM Admin Client (if None, creates from env)
            max_retries: Maximum retry attempts before giving up (default 10)
            max_backoff_seconds: Maximum backoff delay in seconds (default 300)
        """
        self.admin_client = admin_client or LiteLLMAdminClient()
        self.max_retries = max_retries
        self.max_backoff_seconds = max_backoff_seconds

        # Get encryption key from env
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        if not self.encryption_key:
            logger.warning(
                "ENCRYPTION_KEY not set, using default (NOT for production)"
            )
            self.encryption_key = None  # Will use default in encryption.py

    async def reconcile(
        self, db: AsyncSession, limit: int = 50, dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Batch process pending provisioning keys.

        Uses SELECT FOR UPDATE SKIP LOCKED for concurrent-safe processing.

        Args:
            db: Database session
            limit: Maximum number of keys to process
            dry_run: If True, don't actually provision (for testing)

        Returns:
            Dict with statistics:
            {
                "processed": 10,
                "success": 8,
                "failed": 2,
                "skipped": 0,
            }
        """
        stats = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

        # Query for keys needing provisioning
        # - status = PROVISIONING or FAILED (with next_retry_at in past)
        # - Use FOR UPDATE SKIP LOCKED for concurrent safety
        now = datetime.now()

        stmt = (
            select(LLMVirtualKey)
            .where(
                (LLMVirtualKey.status == VirtualKeyStatusEnum.PROVISIONING)
                | (
                    (LLMVirtualKey.status == VirtualKeyStatusEnum.FAILED)
                    & (
                        (LLMVirtualKey.next_retry_at.is_(None))
                        | (LLMVirtualKey.next_retry_at <= now)
                    )
                )
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        result = await db.execute(stmt)
        keys = result.scalars().all()

        logger.info(f"Reconcile: found {len(keys)} keys to process (limit={limit})")

        for vk in keys:
            if dry_run:
                logger.info(f"[DRY RUN] Would process key: {vk.key_alias}")
                stats["processed"] += 1
                continue

            try:
                result = await self._process_provisioning_key(vk, db)

                stats["processed"] += 1

                if result == ProvisioningResult.SUCCESS:
                    stats["success"] += 1
                elif result == ProvisioningResult.FAILED_RETRY:
                    stats["failed"] += 1
                elif result == ProvisioningResult.SKIPPED_MAX_RETRIES:
                    stats["skipped"] += 1

            except Exception as e:
                logger.error(
                    f"Unexpected error processing key {vk.id}: {e}", exc_info=True
                )
                stats["processed"] += 1
                stats["failed"] += 1

        logger.info(f"Reconcile complete: {stats}")

        return stats

    async def provision_user(
        self, user_id: int, db: AsyncSession, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Provision virtual keys for a specific user.

        Creates or updates keys for:
        - vk_user (for BYOK agent tiers)
        - vk_system_on_behalf (for system scopes)

        Args:
            user_id: User ID to provision keys for
            db: Database session
            dry_run: If True, don't actually create keys

        Returns:
            Dict with created/updated key info
        """
        results = {"user_id": user_id, "created": [], "already_active": []}

        # Define the two key types to provision
        key_configs = [
            {
                "key_type": "user",
                "key_alias": f"vk:user:{user_id}",
                "allowed_models": ["agents_fast", "agents_balanced", "agents_best"],
            },
            {
                "key_type": "system_on_behalf",
                "key_alias": f"vk:obo:{user_id}",
                "allowed_models": [
                    "sys_copilot_v1",
                    "sys_cockpit_scan_v1",
                    "sys_agents_fast_v1",
                    "sys_agents_balanced_v1",
                    "sys_agents_best_v1",
                    "sys_crew_router_v1",
                    "sys_crew_summary_v1",
                ],
            },
        ]

        for config in key_configs:
            # Check if key already exists
            stmt = select(LLMVirtualKey).filter_by(
                user_id=user_id, key_type=config["key_type"]
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing and existing.status == VirtualKeyStatusEnum.ACTIVE:
                # Already active - skip
                logger.info(
                    f"Key already active: user_id={user_id}, "
                    f"key_type={config['key_type']}"
                )
                results["already_active"].append(config["key_type"])
                continue

            if existing:
                # Exists but not active - reset to PROVISIONING
                existing.status = VirtualKeyStatusEnum.PROVISIONING
                existing.retry_count = 0
                existing.next_retry_at = None
                existing.last_error = None
                await db.commit()

                logger.info(
                    f"Reset existing key to PROVISIONING: user_id={user_id}, "
                    f"key_type={config['key_type']}"
                )
                results["created"].append(config["key_type"])
            else:
                # Create new PROVISIONING record
                if dry_run:
                    logger.info(
                        f"[DRY RUN] Would create key: user_id={user_id}, "
                        f"key_type={config['key_type']}"
                    )
                    results["created"].append(config["key_type"])
                    continue

                vk = LLMVirtualKey(
                    user_id=user_id,
                    key_type=config["key_type"],
                    key_alias=config["key_alias"],
                    status=VirtualKeyStatusEnum.PROVISIONING,
                    allowed_models=config["allowed_models"],
                    retry_count=0,
                )
                db.add(vk)
                await db.commit()

                logger.info(
                    f"Created PROVISIONING key: user_id={user_id}, "
                    f"key_type={config['key_type']}"
                )
                results["created"].append(config["key_type"])

        return results

    async def _process_provisioning_key(
        self, vk: LLMVirtualKey, db: AsyncSession
    ) -> ProvisioningResult:
        """
        Process a single key in PROVISIONING/FAILED state.

        State transitions:
        - SUCCESS: PROVISIONING → ACTIVE (key encrypted + stored)
        - FAILED_RETRY: PROVISIONING → FAILED (retry_count++, backoff)
        - SKIPPED: retry_count > max_retries (no change)

        Args:
            vk: Virtual key record to process
            db: Database session

        Returns:
            ProvisioningResult indicating outcome
        """
        # Check max retries
        if vk.retry_count >= self.max_retries:
            logger.warning(
                f"Key {vk.id} exceeded max_retries ({self.max_retries}), skipping"
            )
            return ProvisioningResult.SKIPPED_MAX_RETRIES

        try:
            # Call LiteLLM Admin API to generate key
            result = await self.admin_client.generate_key(
                key_alias=vk.key_alias,
                models=vk.allowed_models or [],
                metadata={
                    "user_id": str(vk.user_id),
                    "key_type": vk.key_type,
                    "env": os.getenv("ENVIRONMENT", "development"),
                },
                user_id=str(vk.user_id),
            )

            virtual_key = result["key"]

            # Encrypt and store
            vk.litellm_key_encrypted = encrypt_api_key(
                virtual_key, self.encryption_key
            )
            vk.status = VirtualKeyStatusEnum.ACTIVE
            vk.provisioned_at = datetime.now()
            vk.last_error = None
            vk.next_retry_at = None

            await db.commit()

            logger.info(
                f"Successfully provisioned key: id={vk.id}, "
                f"alias={vk.key_alias}, user_id={vk.user_id}"
            )

            return ProvisioningResult.SUCCESS

        except LiteLLMAdminError as e:
            # Provisioning failed - increment retry and schedule backoff
            vk.retry_count += 1
            vk.status = VirtualKeyStatusEnum.FAILED
            vk.last_error = str(e)

            # Calculate backoff delay: min(2^retry_count, max_backoff_seconds)
            delay_seconds = min(2**vk.retry_count, self.max_backoff_seconds)
            vk.next_retry_at = datetime.now() + timedelta(seconds=delay_seconds)

            await db.commit()

            logger.error(
                f"Failed to provision key: id={vk.id}, alias={vk.key_alias}, "
                f"retry_count={vk.retry_count}, next_retry_at={vk.next_retry_at}, "
                f"error={e}"
            )

            return ProvisioningResult.FAILED_RETRY

        except Exception as e:
            # Unexpected error
            vk.retry_count += 1
            vk.status = VirtualKeyStatusEnum.FAILED
            vk.last_error = f"Unexpected error: {e}"

            delay_seconds = min(2**vk.retry_count, self.max_backoff_seconds)
            vk.next_retry_at = datetime.now() + timedelta(seconds=delay_seconds)

            await db.commit()

            logger.error(
                f"Unexpected error provisioning key: id={vk.id}, error={e}",
                exc_info=True,
            )

            return ProvisioningResult.FAILED_RETRY
