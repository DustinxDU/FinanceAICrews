"""
MCP Infrastructure - Agent 工具系统支持

保留 CrewAI MCP 集成，用于 Agent 动态工具发现和调用。
"""

from AICrews.infrastructure.mcp.async_mcp import AsyncMCPServer
from AICrews.infrastructure.mcp.dynamic_filter import create_context_aware_filter
from AICrews.infrastructure.mcp.discovery_client import (
    MCPDiscoveryClient,
    get_mcp_discovery_client,
)

__all__ = [
    "AsyncMCPServer",
    "create_context_aware_filter",
    "MCPDiscoveryClient",
    "get_mcp_discovery_client",
]
