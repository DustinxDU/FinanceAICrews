"""
Seed Skills System - Initialize builtin providers and capabilities.

This script seeds the database with:
1. Builtin providers (indicator_calc, strategy_eval)
2. Core capability skills (cap:* entries)
3. Provider→capability mappings

Run with: python -m scripts.seed_skills_system
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from AICrews.database.db_manager import DBManager
from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
from AICrews.database.models.skill import SkillCatalog, SkillKind
from AICrews.capabilities.taxonomy import (
    CORE_CAPABILITIES,
    EXTENDED_CAPABILITIES,
    COMPUTE_CAPABILITIES,
    CAPABILITY_METADATA,
)


def seed_builtin_providers(db):
    """Create builtin providers for compute capabilities."""
    print("\n=== Seeding Builtin Providers ===")

    builtin_providers = [
        {
            "provider_key": "builtin_compute",
            "provider_type": "builtin",
            "url": None,
            "config": {"type": "compute"},
            "enabled": True,
            "healthy": True,
            "priority": 100,
            "capabilities": COMPUTE_CAPABILITIES,
        },
    ]

    for provider_data in builtin_providers:
        provider_key = provider_data["provider_key"]

        # Check if exists
        existing = db.execute(
            select(CapabilityProvider).where(
                CapabilityProvider.provider_key == provider_key
            )
        ).scalar_one_or_none()

        if existing:
            print(f"  ✓ Provider '{provider_key}' already exists")
            continue

        # Create provider
        provider = CapabilityProvider(
            provider_key=provider_key,
            provider_type=provider_data["provider_type"],
            url=provider_data["url"],
            config=provider_data["config"],
            enabled=provider_data["enabled"],
            healthy=provider_data["healthy"],
            priority=provider_data["priority"],
        )

        db.add(provider)
        db.flush()

        # Create capability mappings
        for cap_id in provider_data["capabilities"]:
            mapping = ProviderCapabilityMapping(
                provider_id=provider.id,
                capability_id=cap_id,
                raw_tool_name=cap_id,  # For builtin, same as capability_id
                config=None,
            )
            db.add(mapping)

        print(f"  + Created provider '{provider_key}' with {len(provider_data['capabilities'])} capabilities")

    db.commit()


def seed_capability_skills(db):
    """Create skill catalog entries for all capabilities."""
    print("\n=== Seeding Capability Skills ===")

    # Combine all capabilities to seed
    all_caps_to_seed = CORE_CAPABILITIES + EXTENDED_CAPABILITIES + COMPUTE_CAPABILITIES

    for cap_id in all_caps_to_seed:
        skill_key = f"cap:{cap_id}"

        # Check if exists
        existing = db.execute(
            select(SkillCatalog).where(SkillCatalog.skill_key == skill_key)
        ).scalar_one_or_none()

        if existing:
            print(f"  ✓ Skill '{skill_key}' already exists")
            continue

        # Get metadata
        meta = CAPABILITY_METADATA.get(cap_id, {})
        display_name = meta.get("display_name", cap_id.replace("_", " ").title())
        description = meta.get("description", f"Access {display_name} capability")
        group = meta.get("group", "market_data")
        icon = meta.get("icon")

        # Determine if it's a core capability (should be enabled by default)
        is_core = cap_id in CORE_CAPABILITIES

        # Create skill
        skill = SkillCatalog(
            skill_key=skill_key,
            kind=SkillKind.capability,
            capability_id=cap_id,
            group_name=group,
            title=display_name,
            description=description,
            icon=icon,
            tags=[group],
            invocation={"capability_id": cap_id},
            args_schema=None,  # TODO: Could add generic ticker/date schema
            examples=[],
            failure_modes=[],
            is_system=True,
            is_active=True,
            sort_order=10 if is_core else 20,  # Core capabilities first
        )

        db.add(skill)
        print(f"  + Created skill '{skill_key}' ({display_name})")

    db.commit()


def main():
    """Run all seeding steps."""
    print("🌱 Seeding Skills System Database...")

    db_manager = DBManager()

    with db_manager.get_session() as db:
        seed_builtin_providers(db)
        seed_capability_skills(db)

    print("\n✅ Seeding complete!")
    print("\nNext steps:")
    print("1. Visit /tools page → Providers tab to see builtin providers")
    print("2. Visit /tools page → Skills tab to see capability skills")
    print("3. Add MCP providers via the 'Create Provider' button")


if __name__ == "__main__":
    main()
