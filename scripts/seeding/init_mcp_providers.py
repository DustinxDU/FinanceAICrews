#!/usr/bin/env python3
"""
Initialize MCP providers and sync tools from actual MCP server definitions.

This is the CANONICAL script for MCP initialization. It:
1. Creates/updates CapabilityProvider entries for MCP servers
2. Syncs MCPTool entries from actual server.py definitions (not hardcoded)
3. Generates capability mappings using CapabilityMatcher

Usage:
    python scripts/init_mcp_providers.py [--dry-run] [--skip-mappings]

Options:
    --dry-run         Show what would be done without making changes
    --skip-mappings   Skip capability mapping generation

IMPORTANT: This script reads tool definitions from docker/mcp/*/server.py files.
"""
import argparse
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from sqlalchemy import select, delete

from AICrews.database.db_manager import DBManager
from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
from AICrews.database.models.mcp import MCPServer, MCPTool
from AICrews.services.capability_matcher import get_capability_matcher

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# MCP server configurations
MCP_SERVERS = {
    "yfinance": {
        "display_name": "YFinance Global Markets",
        "description": "Global market data via Yahoo Finance. Supports US, international stocks, ETFs, forex, crypto, and more.",
        "url_env": "FAIC_MCP_YFINANCE_URL",
        "url_default": "http://localhost:8010/sse",
        "server_file": PROJECT_ROOT / "docker" / "mcp" / "yfinance" / "server.py",
        "requires_auth": False,
        "icon": "🌍",
        "mapping_priority": 80,  # Highest priority - primary data source
    },
    "akshare": {
        "display_name": "Akshare China Markets",
        "description": "China market data via Akshare. A-shares, Hong Kong stocks, financial statements, macro data.",
        "url_env": "FAIC_MCP_AKSHARE_URL",
        "url_default": "http://localhost:8009/sse",
        "server_file": PROJECT_ROOT / "docker" / "mcp" / "akshare" / "server.py",
        "requires_auth": False,
        "icon": "🇨🇳",
        "mapping_priority": 60,  # Secondary - A-share specialist
    },
    "openbb": {
        "display_name": "OpenBB Platform",
        "description": "Professional financial data via OpenBB. Equities, options, forex, crypto, fixed income, macro.",
        "url_env": "FAIC_MCP_OPENBB_URL",
        "url_default": "http://localhost:8008/mcp",
        "server_file": None,  # OpenBB uses external package, tools discovered dynamically
        "requires_auth": True,
        "icon": "📈",
        "mapping_priority": 40,  # Lowest priority - fallback option
    },
}


def extract_tools_from_server_file(server_file: Path) -> List[Dict[str, Any]]:
    """Extract tool definitions from MCP server source file."""
    if not server_file or not server_file.exists():
        return []

    content = server_file.read_text()

    # Match Tool(name="...", description="...", inputSchema={...})
    # This regex captures the full Tool() definition
    tool_pattern = r'Tool\(\s*name="([^"]+)",\s*description="([^"]+)"'

    tools = []
    for match in re.finditer(tool_pattern, content):
        tool_name = match.group(1)
        description = match.group(2)
        tools.append({
            "name": tool_name,
            "description": description,
            "inputSchema": {},  # Could be extracted but not needed for mapping
        })

    return tools



def normalize_tool_schema(input_schema: Dict) -> Dict:
    """Normalize MCP tool schema to be more LLM-friendly.
    
    - Simplifies anyOf enum structures by merging all possible values
    - Preserves default values
    - Maintains other schema properties
    
    This helps LLMs better understand parameter constraints.
    """
    if not input_schema or not isinstance(input_schema, dict):
        return input_schema
    
    # Deep copy to avoid modifying original
    import copy
    schema = copy.deepcopy(input_schema)
    
    # Process properties
    properties = schema.get("properties", {})
    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            continue
        
        # Handle anyOf with enum values
        if "anyOf" in prop_schema:
            any_of = prop_schema["anyOf"]
            if isinstance(any_of, list):
                # Collect all enum values from anyOf branches
                all_enums = set()
                for branch in any_of:
                    if isinstance(branch, dict) and "enum" in branch:
                        if isinstance(branch["enum"], list):
                            all_enums.update(branch["enum"])
                
                # If we found enum values, replace anyOf with single enum
                if all_enums:
                    # Sort for consistency (splits_only first if present)
                    sorted_enums = sorted(all_enums, key=lambda x: (
                        0 if x == "splits_only" else
                        1 if "split" in x.lower() else
                        2
                    ))
                    
                    # Preserve default value if it exists
                    default = prop_schema.get("default")
                    
                    # Replace anyOf with single enum
                    prop_schema.pop("anyOf")
                    prop_schema["enum"] = sorted_enums
                    if default:
                        prop_schema["default"] = default
                    else:
                        # If no default, use first enum value
                        prop_schema["default"] = sorted_enums[0]
                    
                    # Preserve or update description
                    if "description" not in prop_schema:
                        prop_schema["description"] = f"Valid values: {', '.join(sorted_enums)}"
    
    return schema


def sync_mcp_server(session, server_key: str, config: Dict, dry_run: bool = False) -> Dict:
    """Sync a single MCP server and its tools."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {server_key}")
    logger.info(f"{'='*60}")

    stats = {"tools_synced": 0, "provider_created": False, "mappings_generated": 0}

    # Get or create MCPServer
    mcp_server = session.execute(
        select(MCPServer).where(MCPServer.server_key == server_key)
    ).scalar_one_or_none()

    url = os.getenv(config["url_env"], config["url_default"])

    if not mcp_server:
        if not dry_run:
            mcp_server = MCPServer(
                server_key=server_key,
                display_name=config["display_name"],
                description=config["description"],
                transport_type="sse" if "sse" in url.lower() else "http",
                url=url,
                requires_auth=config["requires_auth"],
                is_system=True,
                is_active=True,
            )
            session.add(mcp_server)
            session.flush()
        logger.info(f"  Created MCPServer: {server_key}")
    else:
        logger.info(f"  MCPServer exists: {server_key}")

    # Get or create CapabilityProvider
    provider_key = f"mcp:{server_key}"
    provider = session.execute(
        select(CapabilityProvider).where(CapabilityProvider.provider_key == provider_key)
    ).scalar_one_or_none()

    if not provider:
        if not dry_run:
            provider = CapabilityProvider(
                provider_key=provider_key,
                provider_type="mcp",
                url=url,
                enabled=True,
                healthy=False,  # Will be updated by health check
                priority=10,
            )
            session.add(provider)
            session.flush()
        stats["provider_created"] = True
        logger.info(f"  Created CapabilityProvider: {provider_key}")
    else:
        logger.info(f"  CapabilityProvider exists: {provider_key}")

    # Extract tools from server file
    server_file = config.get("server_file")
    if server_file:
        tools = extract_tools_from_server_file(server_file)
        logger.info(f"  Extracted {len(tools)} tools from {server_file.name}")

        if tools and not dry_run and mcp_server:
            # Clear existing tools
            session.execute(
                delete(MCPTool).where(MCPTool.server_id == mcp_server.id)
            )

            # Add new tools with normalized schema
            for tool_data in tools:
                # Normalize schema to simplify anyOf structures
                original_schema = tool_data.get("inputSchema", {})
                normalized_schema = normalize_tool_schema(original_schema)
                
                tool = MCPTool(
                    server_id=mcp_server.id,
                    tool_name=tool_data["name"],
                    display_name=tool_data["name"],
                    description=tool_data["description"],
                    input_schema=normalized_schema,
                    is_active=True,
                )
                session.add(tool)
                stats["tools_synced"] += 1

            session.flush()
            logger.info(f"  Synced {stats['tools_synced']} tools to MCPTool table")
    else:
        logger.info(f"  No local server file (tools discovered dynamically)")

    return stats


def generate_mappings(session, provider_key: str, dry_run: bool = False) -> int:
    """Generate capability mappings for a provider using CapabilityMatcher.

    Args:
        session: Database session
        provider_key: Provider key (e.g., "mcp:akshare")
        dry_run: If True, don't make changes

    Returns:
        Number of mappings created
    """
    provider = session.execute(
        select(CapabilityProvider).where(CapabilityProvider.provider_key == provider_key)
    ).scalar_one_or_none()

    if not provider:
        return 0

    server_key = provider_key.replace("mcp:", "")
    mcp_server = session.execute(
        select(MCPServer).where(MCPServer.server_key == server_key)
    ).scalar_one_or_none()

    if not mcp_server:
        return 0

    # Get tools
    tools = session.execute(
        select(MCPTool).where(MCPTool.server_id == mcp_server.id)
    ).scalars().all()

    if not tools:
        return 0

    # Convert to format expected by matcher
    tool_dicts = [
        {"name": t.tool_name, "description": t.description or "", "inputSchema": t.input_schema or {}}
        for t in tools
    ]

    # Get suggestions from matcher
    matcher = get_capability_matcher()
    suggestions = matcher.suggest_mappings(
        discovered_tools=tool_dicts,
        provider_key=provider_key
    )

    if not suggestions:
        return 0

    # Get mapping priority from config (default 50)
    mapping_priority = MCP_SERVERS.get(server_key, {}).get("mapping_priority", 50)

    if not dry_run:
        # Clear existing mappings
        session.execute(
            delete(ProviderCapabilityMapping).where(
                ProviderCapabilityMapping.provider_id == provider.id
            )
        )

        # Add new mappings with priority
        for suggestion in suggestions:
            tool_name = suggestion.get("tool_name")
            cap_id = suggestion.get("capability_id")
            confidence = suggestion.get("confidence", 0)

            if tool_name and cap_id and confidence >= 0.5:
                mapping = ProviderCapabilityMapping(
                    provider_id=provider.id,
                    capability_id=cap_id,
                    raw_tool_name=tool_name,
                    priority=mapping_priority,  # Use configured priority
                )
                session.add(mapping)

        session.flush()
        logger.info(f"  Created mappings with priority={mapping_priority}")

    return len([s for s in suggestions if s.get("confidence", 0) >= 0.5])


def main():
    parser = argparse.ArgumentParser(description="Initialize MCP providers and sync tools")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--skip-mappings", action="store_true", help="Skip capability mapping generation")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made\n")

    db = DBManager()
    with db.get_session() as session:
        total_stats = {"tools_synced": 0, "providers_created": 0, "mappings_generated": 0}

        # Sync each MCP server
        for server_key, config in MCP_SERVERS.items():
            stats = sync_mcp_server(session, server_key, config, dry_run=args.dry_run)
            total_stats["tools_synced"] += stats["tools_synced"]
            if stats["provider_created"]:
                total_stats["providers_created"] += 1

        # Generate mappings
        if not args.skip_mappings:
            logger.info(f"\n{'='*60}")
            logger.info("Generating capability mappings...")
            logger.info(f"{'='*60}")

            for server_key in MCP_SERVERS.keys():
                provider_key = f"mcp:{server_key}"
                count = generate_mappings(session, provider_key, dry_run=args.dry_run)
                total_stats["mappings_generated"] += count
                logger.info(f"  {provider_key}: {count} mappings")

        if not args.dry_run:
            session.commit()

        logger.info(f"\n{'='*60}")
        logger.info("SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"  Providers created: {total_stats['providers_created']}")
        logger.info(f"  Tools synced: {total_stats['tools_synced']}")
        logger.info(f"  Mappings generated: {total_stats['mappings_generated']}")

        if args.dry_run:
            logger.info("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
