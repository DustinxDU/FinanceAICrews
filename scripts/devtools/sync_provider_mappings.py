#!/usr/bin/env python3
"""
Sync MCP provider capability mappings with actual tools.

This script:
1. Reads actual tools from MCPTool table (cached from MCP servers)
2. Uses CapabilityMatcher to generate smart mapping suggestions
3. Updates ProviderCapabilityMapping table with new mappings
4. Preserves existing mappings that are still valid

Usage:
    python scripts/sync_provider_mappings.py [--dry-run] [--provider PROVIDER_KEY]

Options:
    --dry-run       Show what would be changed without making changes
    --provider      Only sync a specific provider (e.g., "mcp:yfinance")
"""
import argparse
import logging
from typing import Dict, List, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from AICrews.database.db_manager import DBManager
from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
from AICrews.database.models.mcp import MCPServer, MCPTool
from AICrews.services.capability_matcher import get_capability_matcher

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def get_mcp_tools(session, provider: CapabilityProvider) -> List[Dict]:
    """Get actual tools from MCPTool table for a provider."""
    server_key = provider.provider_key.replace("mcp:", "")

    mcp_server = session.execute(
        select(MCPServer).where(MCPServer.server_key == server_key)
    ).scalar_one_or_none()

    if not mcp_server:
        return []

    mcp_tools = session.execute(
        select(MCPTool).where(MCPTool.server_id == mcp_server.id)
    ).scalars().all()

    # Convert to dict format expected by matcher
    return [
        {
            "name": t.tool_name,
            "description": t.description or "",
            "inputSchema": t.input_schema or {},
        }
        for t in mcp_tools
    ]


def analyze_provider(session, provider: CapabilityProvider) -> Dict:
    """Analyze a provider's current state."""
    actual_tools = get_mcp_tools(session, provider)
    actual_tool_names = set(t["name"] for t in actual_tools)

    # Get current mappings
    current_mappings = {m.raw_tool_name: m.capability_id for m in provider.mappings if m.raw_tool_name}
    mapped_tools = set(current_mappings.keys())

    # Find discrepancies
    missing_tools = actual_tool_names - mapped_tools
    stale_tools = mapped_tools - actual_tool_names

    return {
        "actual_tools": actual_tools,
        "actual_tool_names": actual_tool_names,
        "current_mappings": current_mappings,
        "missing_tools": missing_tools,
        "stale_tools": stale_tools,
    }


def generate_new_mappings(
    provider_key: str,
    actual_tools: List[Dict],
    current_mappings: Dict[str, str],
    missing_tools: Set[str]
) -> Dict[str, str]:
    """Generate mappings for missing tools using CapabilityMatcher."""
    if not missing_tools:
        return {}

    # Filter to only missing tools
    tools_to_map = [t for t in actual_tools if t["name"] in missing_tools]

    if not tools_to_map:
        return {}

    # Use capability matcher
    matcher = get_capability_matcher()
    suggestions = matcher.suggest_mappings(
        discovered_tools=tools_to_map,
        provider_key=provider_key
    )

    # suggestions format: List[{tool_name, capability_id, confidence, action}]
    # We need: {tool_name: capability_id} for tools with confidence >= 0.5
    new_mappings = {}
    for suggestion in suggestions:
        tool_name = suggestion.get("tool_name")
        cap_id = suggestion.get("capability_id")
        confidence = suggestion.get("confidence", 0)

        # Only include mappings with reasonable confidence
        if tool_name and cap_id and confidence >= 0.5 and tool_name in missing_tools:
            new_mappings[tool_name] = cap_id

    return new_mappings


def sync_provider(session, provider: CapabilityProvider, dry_run: bool = False) -> Dict:
    """Sync a single provider's mappings."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {provider.provider_key}")
    logger.info(f"{'='*60}")

    analysis = analyze_provider(session, provider)

    if not analysis["actual_tools"]:
        logger.warning(f"  No tools found in MCPTool table for {provider.provider_key}")
        return {"status": "skipped", "reason": "no_tools"}

    logger.info(f"  Actual tools: {len(analysis['actual_tool_names'])}")
    logger.info(f"  Current mappings: {len(analysis['current_mappings'])}")
    logger.info(f"  Missing mappings: {len(analysis['missing_tools'])}")
    logger.info(f"  Stale mappings: {len(analysis['stale_tools'])}")

    stats = {
        "added": 0,
        "removed": 0,
        "preserved": 0,
    }

    # Remove stale mappings
    if analysis["stale_tools"]:
        logger.info(f"\n  Removing stale mappings:")
        for tool_name in analysis["stale_tools"]:
            cap_id = analysis["current_mappings"][tool_name]
            logger.info(f"    - {tool_name} -> {cap_id}")

            if not dry_run:
                session.execute(
                    select(ProviderCapabilityMapping)
                    .where(
                        ProviderCapabilityMapping.provider_id == provider.id,
                        ProviderCapabilityMapping.raw_tool_name == tool_name
                    )
                ).scalar_one_or_none()
                # Delete via query
                from sqlalchemy import delete
                session.execute(
                    delete(ProviderCapabilityMapping).where(
                        ProviderCapabilityMapping.provider_id == provider.id,
                        ProviderCapabilityMapping.raw_tool_name == tool_name
                    )
                )
            stats["removed"] += 1

    # Generate new mappings for missing tools
    if analysis["missing_tools"]:
        new_mappings = generate_new_mappings(
            provider.provider_key,
            analysis["actual_tools"],
            analysis["current_mappings"],
            analysis["missing_tools"]
        )

        if new_mappings:
            logger.info(f"\n  Adding new mappings ({len(new_mappings)}):")
            for tool_name, cap_id in sorted(new_mappings.items()):
                logger.info(f"    + {tool_name} -> {cap_id}")

                if not dry_run:
                    mapping = ProviderCapabilityMapping(
                        provider_id=provider.id,
                        capability_id=cap_id,
                        raw_tool_name=tool_name,
                    )
                    session.add(mapping)
                stats["added"] += 1

        # Report unmapped tools
        unmapped = analysis["missing_tools"] - set(new_mappings.keys())
        if unmapped:
            logger.info(f"\n  Could not auto-map ({len(unmapped)} tools):")
            for tool_name in sorted(unmapped)[:10]:  # Show first 10
                logger.info(f"    ? {tool_name}")
            if len(unmapped) > 10:
                logger.info(f"    ... and {len(unmapped) - 10} more")

    # Count preserved
    preserved_tools = analysis["actual_tool_names"] & set(analysis["current_mappings"].keys())
    stats["preserved"] = len(preserved_tools)

    if not dry_run:
        session.commit()

    logger.info(f"\n  Summary: +{stats['added']} added, -{stats['removed']} removed, {stats['preserved']} preserved")

    return {"status": "success", "stats": stats}


def main():
    parser = argparse.ArgumentParser(description="Sync MCP provider capability mappings")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--provider", type=str, help="Only sync specific provider (e.g., mcp:yfinance)")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made\n")

    db = DBManager()
    with db.get_session() as session:
        # Get MCP providers
        query = select(CapabilityProvider).options(
            joinedload(CapabilityProvider.mappings)
        ).where(CapabilityProvider.provider_type == "mcp")

        if args.provider:
            query = query.where(CapabilityProvider.provider_key == args.provider)

        providers = session.execute(query).unique().scalars().all()

        if not providers:
            logger.error("No MCP providers found")
            return

        total_stats = {"added": 0, "removed": 0, "preserved": 0}

        for provider in providers:
            result = sync_provider(session, provider, dry_run=args.dry_run)
            if result["status"] == "success":
                for key in total_stats:
                    total_stats[key] += result["stats"][key]

        logger.info(f"\n{'='*60}")
        logger.info("TOTAL SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"  Added: {total_stats['added']}")
        logger.info(f"  Removed: {total_stats['removed']}")
        logger.info(f"  Preserved: {total_stats['preserved']}")

        if args.dry_run:
            logger.info("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
