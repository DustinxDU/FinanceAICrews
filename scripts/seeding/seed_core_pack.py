"""
Seed Core Pack - Initialize Core Pack from YAML configuration.

This script reads from config/agents/core-pack.yaml and seeds:
1. Core capabilities (10 capabilities)
2. Preset skills (22 skills)
3. Built-in providers (3 providers)

Usage:
    python -m scripts.seed_core_pack
"""
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from sqlalchemy import select
from AICrews.database.db_manager import DBManager
from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
from AICrews.database.models.skill import SkillCatalog, SkillKind


def load_core_pack_config() -> Dict[str, Any]:
    """Load Core Pack configuration from YAML file."""
    config_path = Path(__file__).parent.parent / "config" / "agents" / "core-pack.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Core Pack config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def seed_core_capabilities(db, capabilities: List[Dict]) -> int:
    """Seed core capability skills from config."""
    print("\n=== Seeding Core Capabilities ===")
    count = 0

    for cap_config in capabilities:
        cap_id = cap_config["id"]
        skill_key = f"cap:{cap_id}"

        # Check if exists
        existing = db.execute(
            select(SkillCatalog).where(SkillCatalog.skill_key == skill_key)
        ).scalar_one_or_none()

        if existing:
            print(f"  ✓ Capability '{skill_key}' already exists")
            continue

        # Create skill entry
        skill = SkillCatalog(
            skill_key=skill_key,
            kind=SkillKind.capability,
            capability_id=cap_id,
            group_name=cap_config.get("group", "market_data"),
            title=cap_config["display_name"],
            description=cap_config["description"],
            icon=cap_config.get("icon"),
            tags=[cap_config.get("group", "market_data")],
            invocation={"capability_id": cap_id},
            args_schema=None,
            examples=[],
            failure_modes=[],
            is_system=True,
            is_active=True,
            sort_order=1 if cap_config.get("is_core", False) else 10,
        )

        db.add(skill)
        count += 1
        print(f"  + Created capability '{skill_key}' ({cap_config['display_name']})")

    db.commit()
    return count


def seed_preset_skills(db, skills: List[Dict]) -> int:
    """Seed preset skills from config."""
    print("\n=== Seeding Preset Skills ===")
    count = 0

    for skill_config in skills:
        skill_key = skill_config["key"]

        # Check if exists
        existing = db.execute(
            select(SkillCatalog).where(SkillCatalog.skill_key == skill_key)
        ).scalar_one_or_none()

        if existing:
            print(f"  ✓ Skill '{skill_key}' already exists")
            continue

        # Determine kind from key prefix
        if skill_key.startswith(("skillset:", "workflow:")):
            kind = SkillKind.skillset
            group = "skillset"
        elif skill_key.startswith("preset:quant:"):
            kind = SkillKind.preset
            group = "quant"
        elif skill_key.startswith("preset:strategy:"):
            kind = SkillKind.strategy
            group = "strategy"
        elif skill_key.startswith("preset:"):
            kind = SkillKind.preset
            group = "preset"
        else:
            kind = SkillKind.preset
            group = "general"

        # Extract dependencies from capabilities and store in invocation
        capabilities = skill_config.get("capabilities", [])
        invocation_data = skill_config.get("invocation", {})
        invocation_data["required_capabilities"] = capabilities  # Store dependencies here

        # Create skill entry
        skill = SkillCatalog(
            skill_key=skill_key,
            kind=kind,
            capability_id=None,  # Presets don't map to single capability
            group_name=group,
            title=skill_config["display_name"],
            description=skill_config["description"],
            icon=None,  # Presets use default icons based on kind
            tags=skill_config.get("tags", []),
            invocation=invocation_data,  # Store invocation + dependencies
            args_schema=None,
            examples=[],
            failure_modes=[],
            is_system=True,
            is_active=skill_config.get("is_enabled", True),
            sort_order=skill_config.get("sort_order", 50),
        )

        db.add(skill)
        count += 1
        print(f"  + Created skill '{skill_key}' ({skill_config['display_name']})")

    db.commit()
    return count


def seed_builtin_providers(db, providers: List[Dict]) -> int:
    """Seed built-in providers from config."""
    print("\n=== Seeding Built-in Providers ===")
    count = 0

    for provider_config in providers:
        provider_key = provider_config["key"]

        # Check if exists
        existing = db.execute(
            select(CapabilityProvider).where(
                CapabilityProvider.provider_key == provider_key
            )
        ).scalar_one_or_none()

        if existing:
            print(f"  ✓ Provider '{provider_key}' already exists")
            continue

        provider_type = provider_config.get("provider_type") or provider_config.get("type", "builtin")
        connection_schema = provider_config.get("connection_schema", {})

        # Create provider
        provider = CapabilityProvider(
            provider_key=provider_key,
            provider_type=provider_type,
            url=None,
            config=provider_config.get("config", {}),
            connection_schema=connection_schema,
            enabled=provider_config.get("enabled", True),
            healthy=provider_config.get("healthy", True),
            priority=provider_config.get("priority", 100),
        )

        db.add(provider)
        db.flush()

        # Create capability mappings
        mappings = provider_config.get("mappings")
        if mappings is None:
            capability_ids = provider_config.get("capabilities", [])
            mappings = [
                {"capability_id": cap_id, "raw_tool_name": cap_id}
                for cap_id in capability_ids
            ]

        for mapping_def in mappings:
            cap_id = mapping_def.get("capability_id")
            if not cap_id:
                continue

            mapping = ProviderCapabilityMapping(
                provider_id=provider.id,
                capability_id=cap_id,
                raw_tool_name=mapping_def.get("raw_tool_name", cap_id),
                config=mapping_def.get("config"),
            )
            db.add(mapping)

        count += 1
        print(f"  + Created provider '{provider_key}' with {len(mappings)} capabilities")

    db.commit()
    return count


def verify_seeding(db) -> Dict[str, int]:
    """Verify seeding results."""
    print("\n=== Verifying Seeding ===")

    stats = {
        "capabilities": db.execute(
            select(SkillCatalog).where(SkillCatalog.kind == SkillKind.capability)
        ).scalars().all(),
        "presets": db.execute(
            select(SkillCatalog).where(SkillCatalog.kind.in_([SkillKind.preset, SkillKind.strategy]))
        ).scalars().all(),
        "providers": db.execute(
            select(CapabilityProvider).where(CapabilityProvider.provider_type == "builtin")
        ).scalars().all(),
    }

    print(f"  ✓ Capabilities: {len(stats['capabilities'])}")
    print(f"  ✓ Preset Skills: {len(stats['presets'])}")
    print(f"  ✓ Built-in Providers: {len(stats['providers'])}")

    return {
        "capabilities": len(stats["capabilities"]),
        "presets": len(stats["presets"]),
        "providers": len(stats["providers"]),
    }


def main():
    """Run Core Pack seeding."""
    print("🌱 Seeding FinanceAI Core Pack v1.0.0...")

    # Load configuration
    try:
        config = load_core_pack_config()
        print(f"\n✓ Loaded Core Pack config: {config['metadata']['name']}")
        print(f"  Version: {config['metadata']['version']}")
        print(f"  Author: {config['metadata']['author']}")
    except Exception as e:
        print(f"❌ Failed to load Core Pack config: {e}")
        sys.exit(1)

    # Seed database
    db_manager = DBManager()

    with db_manager.get_session() as db:
        # Seed in order: providers -> capabilities -> skills
        provider_count = seed_builtin_providers(db, config.get("providers", []))
        cap_count = seed_core_capabilities(db, config.get("capabilities", []))
        skill_count = seed_preset_skills(db, config.get("skills", []))

        # Verify
        stats = verify_seeding(db)

    print("\n✅ Core Pack seeding complete!")
    print("\nSummary:")
    print(f"  - Capabilities: {cap_count} new, {stats['capabilities']} total")
    print(f"  - Preset Skills: {skill_count} new, {stats['presets']} total")
    print(f"  - Built-in Providers: {provider_count} new, {stats['providers']} total")

    print("\nNext steps:")
    print("1. Visit /tools?category=skills to see Core Pack skills")
    print("2. Use preset skills in Crew Builder → Agent Skills")
    print("3. Add MCP providers to enable market data capabilities")


if __name__ == "__main__":
    main()
