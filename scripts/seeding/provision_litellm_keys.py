#!/usr/bin/env python
"""
LiteLLM Virtual Key Provisioner CLI

This CLI provides administrative commands for managing LiteLLM virtual keys:
- reconcile: Batch process pending provisioning keys
- provision-user: Provision keys for a specific user
- revoke: Revoke/delete a virtual key
- rotate: Rotate a user's virtual key (future implementation)

Security Note:
- This script requires LITELLM_PROXY_MASTER_KEY environment variable
- Should ONLY be run by administrators/ops team
- Never run in app containers (master key isolation)

Usage:
    # Batch reconcile (process up to 50 keys)
    python scripts/provision_litellm_keys.py reconcile --limit 50

    # Dry run
    python scripts/provision_litellm_keys.py reconcile --limit 10 --dry-run

    # Provision specific user
    python scripts/provision_litellm_keys.py provision-user --user-id 123

    # Revoke key
    python scripts/provision_litellm_keys.py revoke --id 456
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import click

from AICrews.database.db_manager import DBManager
from AICrews.database.models.llm_policy import LLMVirtualKey, VirtualKeyStatusEnum
from AICrews.services.provisioner_service import ProvisionerService
from AICrews.services.litellm_admin_client import LiteLLMAdminClient
from AICrews.utils.encryption import decrypt_api_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """
    LiteLLM Virtual Key Provisioner CLI.

    Administrative tool for managing virtual key lifecycle.
    Requires LITELLM_PROXY_MASTER_KEY environment variable.
    """
    pass


@cli.command()
@click.option("--limit", default=50, help="Maximum number of keys to process")
@click.option("--dry-run", is_flag=True, help="Dry run mode (no actual provisioning)")
def reconcile(limit: int, dry_run: bool):
    """
    Batch process pending provisioning keys.

    Queries for keys in PROVISIONING or FAILED (past retry time) status
    and processes them in batches.

    Uses SELECT FOR UPDATE SKIP LOCKED for concurrent safety.
    """
    logger.info(
        f"Starting reconcile: limit={limit}, dry_run={dry_run}"
    )

    async def run():
        db_manager = DBManager()

        try:
            admin_client = LiteLLMAdminClient()
            service = ProvisionerService(admin_client=admin_client)

            with db_manager.get_session() as db:
                stats = await service.reconcile(
                    db=db, limit=limit, dry_run=dry_run
                )

                logger.info(f"Reconcile complete: {stats}")

                # Print summary
                click.echo("\n" + "=" * 60)
                click.echo("Reconcile Summary")
                click.echo("=" * 60)
                click.echo(f"Processed: {stats['processed']}")
                click.echo(f"Success:   {stats['success']}")
                click.echo(f"Failed:    {stats['failed']}")
                click.echo(f"Skipped:   {stats['skipped']}")
                click.echo("=" * 60 + "\n")

            await admin_client.close()

        except Exception as e:
            logger.error(f"Reconcile failed: {e}", exc_info=True)
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)

    asyncio.run(run())


@cli.command()
@click.option("--user-id", required=True, type=int, help="User ID to provision keys for")
@click.option("--dry-run", is_flag=True, help="Dry run mode")
def provision_user(user_id: int, dry_run: bool):
    """
    Provision virtual keys for a specific user.

    Creates or resets both:
    - vk_user (for BYOK agent tiers)
    - vk_system_on_behalf (for system scopes)
    """
    logger.info(
        f"Provisioning user: user_id={user_id}, dry_run={dry_run}"
    )

    async def run():
        db_manager = DBManager()

        try:
            admin_client = LiteLLMAdminClient()
            service = ProvisionerService(admin_client=admin_client)

            with db_manager.get_session() as db:
                result = await service.provision_user(
                    user_id=user_id, db=db, dry_run=dry_run
                )

                logger.info(f"Provision result: {result}")

                # Print summary
                click.echo("\n" + "=" * 60)
                click.echo(f"Provision User {user_id}")
                click.echo("=" * 60)
                click.echo(f"Created:        {', '.join(result['created']) if result['created'] else 'None'}")
                click.echo(f"Already Active: {', '.join(result['already_active']) if result['already_active'] else 'None'}")
                click.echo("=" * 60 + "\n")

                if not dry_run:
                    click.echo("Keys created in PROVISIONING state.")
                    click.echo("Run 'reconcile' command to complete provisioning.\n")

            await admin_client.close()

        except Exception as e:
            logger.error(f"Provision user failed: {e}", exc_info=True)
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)

    asyncio.run(run())


@cli.command()
@click.option("--id", "key_id", required=True, type=int, help="Virtual key row ID to revoke")
@click.option("--dry-run", is_flag=True, help="Dry run mode")
def revoke(key_id: int, dry_run: bool):
    """
    Revoke a virtual key.

    Marks key as REVOKED in DB and deletes it from LiteLLM Proxy.
    """
    logger.info(f"Revoking key: id={key_id}, dry_run={dry_run}")

    async def run():
        db_manager = DBManager()

        try:
            admin_client = LiteLLMAdminClient()

            with db_manager.get_session() as db:
                # Get key
                vk = db.query(LLMVirtualKey).filter_by(id=key_id).first()

                if not vk:
                    click.echo(f"ERROR: Key {key_id} not found", err=True)
                    sys.exit(1)

                if vk.status == VirtualKeyStatusEnum.REVOKED:
                    click.echo(f"Key {key_id} is already REVOKED")
                    return

                # Decrypt key
                if vk.litellm_key_encrypted:
                    import os
                    encryption_key = os.getenv("ENCRYPTION_KEY")
                    virtual_key = decrypt_api_key(vk.litellm_key_encrypted, encryption_key)
                else:
                    click.echo(f"WARNING: Key {key_id} has no encrypted key stored", err=True)
                    virtual_key = None

                # Print key info
                click.echo("\n" + "=" * 60)
                click.echo(f"Key Details (ID: {key_id})")
                click.echo("=" * 60)
                click.echo(f"User ID:    {vk.user_id}")
                click.echo(f"Key Type:   {vk.key_type}")
                click.echo(f"Key Alias:  {vk.key_alias}")
                click.echo(f"Status:     {vk.status.value}")
                click.echo("=" * 60 + "\n")

                if dry_run:
                    click.echo("[DRY RUN] Would revoke this key")
                    return

                # Delete from LiteLLM Proxy
                if virtual_key:
                    deleted = await admin_client.delete_key(virtual_key)
                    if deleted:
                        click.echo(f"Deleted key from LiteLLM Proxy")
                    else:
                        click.echo(f"Key not found in LiteLLM Proxy (may already be deleted)")

                # Mark as revoked in DB
                from datetime import datetime
                vk.status = VirtualKeyStatusEnum.REVOKED
                vk.revoked_at = datetime.now()
                db.commit()

                click.echo(f"Key {key_id} marked as REVOKED in database\n")

            await admin_client.close()

        except Exception as e:
            logger.error(f"Revoke failed: {e}", exc_info=True)
            click.echo(f"ERROR: {e}", err=True)
            sys.exit(1)

    asyncio.run(run())


@cli.command()
@click.option("--user-id", required=True, type=int, help="User ID to rotate keys for")
@click.option("--key-type", required=True, type=click.Choice(["user", "system_on_behalf"]), help="Key type to rotate")
@click.option("--dry-run", is_flag=True, help="Dry run mode")
def rotate(user_id: int, key_type: str, dry_run: bool):
    """
    Rotate a user's virtual key (creates new key, marks old as rotated).

    NOT IMPLEMENTED YET - placeholder for future feature.
    """
    click.echo("ERROR: rotate command not yet implemented", err=True)
    click.echo("Use provision-user + manual revoke for now", err=True)
    sys.exit(1)


if __name__ == "__main__":
    cli()
