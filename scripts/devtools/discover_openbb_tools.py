#!/usr/bin/env python3
"""
Discover OpenBB MCP Tools

This script connects to the OpenBB MCP server and lists all available tools.
Useful for debugging tool name mismatches and understanding what's available.

Usage:
    source venv/bin/activate && python scripts/discover_openbb_tools.py

Environment:
    Set OPENBB_MCP_SERVER_URL in .env or environment (default: http://localhost:8008/mcp/)
"""

import asyncio
import json
import os
import sys

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from AICrews.tools.mcp._infra.mcp_client import OpenBBMCPClient
from AICrews.tools.mcp._infra.openbb_config import get_openbb_config


def categorize_tools(tools: list) -> dict:
    """Group tools by their prefix/category."""
    categories = {}
    for tool in tools:
        name = tool["name"]
        # Extract category from tool name (e.g., "equity_price_quote" -> "equity")
        parts = name.split("_")
        category = parts[0] if parts else "other"
        
        if category not in categories:
            categories[category] = []
        categories[category].append(tool)
    
    return categories


async def main() -> int:
    cfg = get_openbb_config()
    print(f"OpenBB MCP Server URL: {cfg.mcp_server_url}")
    print("=" * 60)
    
    client = OpenBBMCPClient()
    if not await client.connect():
        print("ERROR: Failed to connect to OpenBB MCP server")
        print("Make sure the server is running: docker compose up -d openbb_mcp")
        return 1
    
    try:
        tools = await client.list_tools()
        print(f"\nTotal tools available: {len(tools)}\n")
        
        # Categorize tools
        categories = categorize_tools(tools)
        
        for category, cat_tools in sorted(categories.items()):
            print(f"\n{'=' * 60}")
            print(f"Category: {category.upper()} ({len(cat_tools)} tools)")
            print("=" * 60)
            
            for tool in sorted(cat_tools, key=lambda x: x["name"]):
                print(f"\n  Tool: {tool['name']}")
                if tool.get("description"):
                    # Truncate long descriptions
                    desc = tool["description"]
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    print(f"    Description: {desc}")
                
                # Show input schema if available
                schema = tool.get("inputSchema", {})
                if schema.get("properties"):
                    props = list(schema["properties"].keys())
                    required = schema.get("required", [])
                    print(f"    Parameters: {', '.join(props)}")
                    if required:
                        print(f"    Required: {', '.join(required)}")
        
        # Print summary of tool names for easy reference
        print("\n" + "=" * 60)
        print("TOOL NAMES SUMMARY (for code reference)")
        print("=" * 60)
        all_names = sorted([t["name"] for t in tools])
        for name in all_names:
            print(f"  - {name}")
        
        # Check for expected tools
        print("\n" + "=" * 60)
        print("EXPECTED TOOL AVAILABILITY CHECK")
        print("=" * 60)
        expected_tools = {
            "equity_price_quote": "Stock price quote",
            "equity_price_historical": "Historical stock prices",
            "equity_fundamental_metrics": "Fundamental metrics",
            "equity_fundamental_balance": "Balance sheet",
            "equity_fundamental_cash": "Cash flow statement",
            "equity_fundamental_income": "Income statement",
            "equity_search": "Symbol search",
            "news_company": "Company news",
            "news_world": "World news",
            "economy_fred_search": "FRED economic data",
            "technical_analysis": "Technical analysis (likely NOT available)",
        }
        
        for tool_name, description in expected_tools.items():
            status = "✓ Available" if tool_name in all_names else "✗ NOT FOUND"
            print(f"  {status}: {tool_name} ({description})")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await client.disconnect()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
