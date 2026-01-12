#!/usr/bin/env python3
"""
Cleanup stale MCP tools and mappings.

This script:
1. Compares MCPTool table with actual tools defined in MCP server files
2. Removes tools that no longer exist in server definitions
3. Removes corresponding ProviderCapabilityMapping entries

Usage:
    python scripts/cleanup_mcp_tools.py [--dry-run]

Options:
    --dry-run       Show what would be deleted without making changes
"""
import argparse
import logging
import re
from pathlib import Path
from typing import Set

from sqlalchemy import select, delete

from AICrews.database.db_manager import DBManager
from AICrews.database.models.mcp import MCPServer, MCPTool
from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# MCP server source files
MCP_SERVER_FILES = {
    'yfinance': Path('/home/dustin/stock/FinanceAICrews/docker/mcp/yfinance/server.py'),
    'akshare': Path('/home/dustin/stock/FinanceAICrews/docker/mcp/akshare/server.py'),
    # openbb uses external package, tools are discovered dynamically
}


def extract_tools_from_server_file(server_file: Path) -> Set[str]:
    """Extract tool names from MCP server source file."""
    if not server_file.exists():
        logger.warning(f"Server file not found: {server_file}")
        return set()

    content = server_file.read_text()
    # Match Tool(name="tool_name", ...)
    tool_pattern = r'Tool\(\s*name="([^"]+)"'
    tools = set(re.findall(tool_pattern, content))
    return tools


def cleanup_server(session, server_key: str, dry_run: bool = False) -> dict:
    """Cleanup stale tools for a single MCP server."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {server_key}")
    logger.info(f"{'='*60}")

    stats = {"tools_removed": 0, "mappings_removed": 0}

    # Get MCP server
    mcp_server = session.execute(
        select(MCPServer).where(MCPServer.server_key == server_key)
    ).scalar_one_or_none()

    if not mcp_server:
        logger.warning(f"  MCP server not found in database: {server_key}")
        return stats

    # Get tools from DB
    db_tools = session.execute(
        select(MCPTool).where(MCPTool.server_id == mcp_server.id)
    ).scalars().all()
    db_tool_names = {t.tool_name for t in db_tools}

    # Get tools from server file
    server_file = MCP_SERVER_FILES.get(server_key)
    if server_file:
        server_tools = extract_tools_from_server_file(server_file)
        logger.info(f"  Tools in server.py: {len(server_tools)}")
    else:
        # For servers without local source (like openbb), skip cleanup
        logger.info(f"  No local server file for {server_key}, skipping tool cleanup")
        return stats

    logger.info(f"  Tools in database: {len(db_tool_names)}")

    # Find stale tools
    stale_tools = db_tool_names - server_tools

    if not stale_tools:
        logger.info(f"  No stale tools found")
        return stats

    logger.info(f"  Stale tools to remove: {len(stale_tools)}")
    for tool_name in sorted(stale_tools):
        logger.info(f"    - {tool_name}")

    # Get provider for this MCP server
    provider = session.execute(
        select(CapabilityProvider).where(CapabilityProvider.provider_key == f"mcp:{server_key}")
    ).scalar_one_or_none()

    if not dry_run:
        # Remove stale mappings first (foreign key constraint)
        if provider:
            for tool_name in stale_tools:
                result = session.execute(
                    delete(ProviderCapabilityMapping).where(
                        ProviderCapabilityMapping.provider_id == provider.id,
                        ProviderCapabilityMapping.raw_tool_name == tool_name
                    )
                )
                if result.rowcount > 0:
                    stats["mappings_removed"] += result.rowcount
                    logger.info(f"    Removed mapping for: {tool_name}")

        # Remove stale tools
        for tool_name in stale_tools:
            session.execute(
                delete(MCPTool).where(
                    MCPTool.server_id == mcp_server.id,
                    MCPTool.tool_name == tool_name
                )
            )
            stats["tools_removed"] += 1

        session.commit()
    else:
        stats["tools_removed"] = len(stale_tools)
        # Count mappings that would be removed
        if provider:
            for tool_name in stale_tools:
                mapping = session.execute(
                    select(ProviderCapabilityMapping).where(
                        ProviderCapabilityMapping.provider_id == provider.id,
                        ProviderCapabilityMapping.raw_tool_name == tool_name
                    )
                ).scalar_one_or_none()
                if mapping:
                    stats["mappings_removed"] += 1

    logger.info(f"  Removed: {stats['tools_removed']} tools, {stats['mappings_removed']} mappings")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Cleanup stale MCP tools and mappings")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made\n")

    db = DBManager()
    with db.get_session() as session:
        total_stats = {"tools_removed": 0, "mappings_removed": 0}

        # Process each MCP server with local source file
        for server_key in MCP_SERVER_FILES.keys():
            stats = cleanup_server(session, server_key, dry_run=args.dry_run)
            total_stats["tools_removed"] += stats["tools_removed"]
            total_stats["mappings_removed"] += stats["mappings_removed"]

        logger.info(f"\n{'='*60}")
        logger.info("TOTAL SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"  Tools removed: {total_stats['tools_removed']}")
        logger.info(f"  Mappings removed: {total_stats['mappings_removed']}")

        if args.dry_run:
            logger.info("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
