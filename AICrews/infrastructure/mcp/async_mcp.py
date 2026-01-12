from crewai.mcp import MCPServerSSE
from crewai.mcp.filters import create_static_tool_filter
from typing import List, Optional, Dict, Any


class AsyncMCPServer:
    """CrewAI 异步 MCP 服务器封装 (v1.7.0+)"""

    def __init__(
        self,
        url: str,
        tool_filter: Optional[List[str]] = None,
        cache_tools_list: bool = True,
    ):
        self.url = url
        self.tool_filter = tool_filter

        filter_obj = None
        if tool_filter:
            filter_obj = create_static_tool_filter(tool_filter)

        self._mcp_config = MCPServerSSE(
            url=url,
            tool_filter=filter_obj,
            cache_tools_list=cache_tools_list,
        )

    @property
    def config(self):
        return self._mcp_config

    def get_tool_filter(self) -> Optional[List[str]]:
        return self.tool_filter
