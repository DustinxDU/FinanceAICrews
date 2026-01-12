"""
配置模块

集中管理全局配置（Settings/Constants/MCP 配置）。
"""

from .settings import Settings, get_settings, set_settings
from .constants import (
    MARKETS,
    DEBATE_ROUNDS,
    DEFAULT_ANALYSTS,
    REPORT_TYPES,
)
from .mcp import (
    MCPConfigLoader,
    MCPConfigConverter,
    MCPServerDefinition,
    AgentToolFilter,
    ToolPolicyLoader,
    get_mcp_config_loader,
    get_mcp_config_converter,
    get_mcps_for_agent,
    get_tool_allowlist_for_agent,
    get_tool_policy_loader,
)

__all__ = [
    "Settings",
    "get_settings",
    "set_settings",
    "MARKETS",
    "DEBATE_ROUNDS",
    "DEFAULT_ANALYSTS",
    "REPORT_TYPES",
    "MCPConfigLoader",
    "MCPConfigConverter",
    "MCPServerDefinition",
    "AgentToolFilter",
    "ToolPolicyLoader",
    "get_mcp_config_loader",
    "get_mcp_config_converter",
    "get_mcps_for_agent",
    "get_tool_allowlist_for_agent",
    "get_tool_policy_loader",
]
