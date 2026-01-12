#!/usr/bin/env python3
"""
Seed script for builtin tool mappings.

Populates default capability mappings for builtin providers that have no mappings.
Run this script to ensure all builtin providers have their default tool mappings.

Usage:
    python -m scripts.seed_builtin_tool_mappings

Or:
    python scripts/seed_builtin_tool_mappings.py
"""

import logging
import sys
from typing import Dict, List, Optional, Tuple

# Add project root to path for imports
sys.path.insert(0, '/home/dustin/stock/FinanceAICrews')

from AICrews.database.db_manager import DBManager
from AICrews.database.models import CapabilityProvider, ProviderCapabilityMapping

logger = logging.getLogger(__name__)


# Default mappings for builtin providers
# Format: {provider_key: [{"capability_id": str, "raw_tool_name": str, "priority": int}]}
DEFAULT_BUILTIN_MAPPINGS = {
    "builtin:file_read_tool": [
        {"capability_id": "file_read", "raw_tool_name": "FileReadTool", "priority": 50}
    ],
    "builtin:directory_read_tool": [
        {"capability_id": "directory_read", "raw_tool_name": "DirectoryReadTool", "priority": 50}
    ],
}


def get_providers_needing_mappings(db) -> List[Tuple[CapabilityProvider, List[dict]]]:
    """
    Find builtin providers that need default mappings.

    Args:
        db: Database session

    Returns:
        List of (provider, mappings_needed) tuples
    """
    from sqlalchemy import select

    providers_needing_mappings = []

    for provider_key, mappings_needed in DEFAULT_BUILTIN_MAPPINGS.items():
        # Find provider by key
        result = db.execute(
            select(CapabilityProvider).where(
                CapabilityProvider.provider_key == provider_key
            )
        ).scalar_one_or_none()

        if result is None:
            logger.warning(f"Provider '{provider_key}' not found in database")
            continue

        provider = result

        # Check if provider already has any of the default mappings
        existing_capability_ids = {
            m.capability_id for m in provider.mappings if m.capability_id
        }

        # Filter to only mappings that don't exist yet
        missing_mappings = [
            m for m in mappings_needed
            if m["capability_id"] not in existing_capability_ids
        ]

        if missing_mappings:
            providers_needing_mappings.append((provider, missing_mappings))
            logger.info(
                f"Provider '{provider_key}' needs {len(missing_mappings)} "
                f"of {len(mappings_needed)} default mappings"
            )
        else:
            logger.debug(f"Provider '{provider_key}' already has all default mappings")

    return providers_needing_mappings


def seed_mappings(db: Optional[DBManager] = None) -> Dict[str, int]:
    """
    Seed default builtin tool mappings to the database.

    Args:
        db: Optional DBManager instance. If not provided, creates one.

    Returns:
        Dictionary with counts:
        - total_providers: Number of providers processed
        - total_mappings: Total new mappings created
        - skipped_mappings: Number of mappings already existed
    """
    from sqlalchemy import select

    # Use provided DBManager or create new one
    if db is None:
        db = DBManager()

    counts = {
        "total_providers": 0,
        "total_mappings": 0,
        "skipped_mappings": 0,
    }

    try:
        with db.get_session() as session:
            # Get providers that need mappings
            providers_info = get_providers_needing_mappings(session)

            for provider, mappings_needed in providers_info:
                counts["total_providers"] += 1

                for mapping_def in mappings_needed:
                    # Create new mapping with priority
                    new_mapping = ProviderCapabilityMapping(
                        provider_id=provider.id,
                        capability_id=mapping_def["capability_id"],
                        raw_tool_name=mapping_def["raw_tool_name"],
                        priority=mapping_def.get("priority", 50),  # Use configured priority
                        config={},
                    )
                    session.add(new_mapping)
                    counts["total_mappings"] += 1
                    logger.info(
                        f"Created mapping: {provider.provider_key} -> "
                        f"{mapping_def['capability_id']} ({mapping_def['raw_tool_name']}) "
                        f"priority={mapping_def.get('priority', 50)}"
                    )

            session.commit()

            logger.info(
                f"Seeding complete: {counts['total_providers']} providers, "
                f"{counts['total_mappings']} new mappings created, "
                f"{counts['skipped_mappings']} skipped"
            )

    except Exception as e:
        logger.error(f"Error seeding builtin mappings: {e}")
        session.rollback()
        raise

    return counts


def main():
    """Main entry point for the seed script."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(
        description="Seed builtin tool mappings to database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    logger.info("Starting builtin tool mappings seed...")

    if args.dry_run:
        # Just show what would be done
        db = DBManager()
        with db.get_session() as session:
            providers_info = get_providers_needing_mappings(session)
            print("\n=== Dry Run Results ===")
            print(f"Providers needing mappings: {len(providers_info)}")
            for provider, mappings in providers_info:
                print(f"  {provider.provider_key}:")
                for m in mappings:
                    print(f"    - {m['capability_id']} -> {m['raw_tool_name']}")
        return

    # Actually seed
    counts = seed_mappings()
    print(f"\nSeeding complete: {counts}")


if __name__ == "__main__":
    main()
