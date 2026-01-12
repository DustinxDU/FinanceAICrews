#!/bin/bash
# MCP Servers Startup Script
# Delegates to scripts/devtools/start_mcp_servers.py

cd "$(dirname "$0")/.."

echo "=== MCP Servers Startup ==="
echo ""
echo "Note: OpenBB MCP runs via Docker Compose (docker compose up -d openbb_mcp)"
echo ""

# Run the Python script
python3 scripts/devtools/start_mcp_servers.py
