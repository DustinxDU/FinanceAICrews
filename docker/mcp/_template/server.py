"""
MCP Server Template - Standard MCP Server with SSE Transport

Replace <SERVER_NAME> and customize tools for your SDK.

Usage:
    1. Copy this directory to docker/mcp/<your_server_name>/
    2. Rename and customize this file
    3. Add your SDK to requirements.txt
    4. Define your tools in TOOL_DEFINITIONS
    5. Implement tool execution in _execute_tool()
    6. Add entry to config/mcp_servers.yaml
    7. Add service to docker-compose.yml
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.responses import Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ServerConfig:
    """Server configuration."""
    enable_caching: bool = True
    cache_ttl_default: int = 300  # 5 minutes
    rate_limit_per_minute: int = 60


def get_config() -> ServerConfig:
    """Load configuration from environment variables."""
    config = ServerConfig()
    config.enable_caching = os.environ.get("MCP_CACHE", "true").lower() == "true"
    config.rate_limit_per_minute = int(os.environ.get("MCP_RATE_LIMIT", "60"))
    return config


# =============================================================================
# Utilities
# =============================================================================

def df_to_dict(df: pd.DataFrame, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convert DataFrame to dictionary payload."""
    result = {
        "data": df.to_dict("records") if not df.empty else [],
        "columns": df.columns.tolist() if hasattr(df, "columns") else [],
        "count": len(df),
    }
    if extra:
        result.update(extra)
    if df.empty:
        result.setdefault("message", "No data found")
    return result


# =============================================================================
# Cache & Rate Limiter
# =============================================================================

class DataCache:
    """Simple in-memory TTL cache."""

    def __init__(self):
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        value = self._store.get(key)
        if not value:
            return None
        expire, data = value
        if expire and expire < time.time():
            self._store.pop(key, None)
            return None
        return data

    def set(self, key: str, value: Any, ttl: int):
        expire = time.time() + ttl if ttl else None
        self._store[key] = (expire, value)


class RateLimiter:
    """Basic sliding window rate limiter."""

    def __init__(self, limit_per_minute: int):
        self.limit = limit_per_minute
        self._timestamps: List[float] = []

    async def acquire(self):
        now = time.time()
        window_start = now - 60
        self._timestamps = [t for t in self._timestamps if t >= window_start]
        if self.limit and len(self._timestamps) >= self.limit:
            oldest = self._timestamps[0]
            sleep_for = max(0.0, (oldest + 60) - now)
            await asyncio.sleep(sleep_for)
        self._timestamps.append(time.time())


# =============================================================================
# Your SDK Client - Customize This
# =============================================================================

class SDKClient:
    """Your SDK client - replace with actual implementation."""

    async def example_tool(self, param1: str, param2: Optional[str] = None) -> Dict[str, Any]:
        """Example tool implementation."""
        def _fetch():
            # Replace with actual SDK call
            return {"result": f"Called with {param1}, {param2}"}
        return await asyncio.to_thread(_fetch)


# =============================================================================
# Tool Definitions - Customize This
# =============================================================================

TOOL_DEFINITIONS: List[Tool] = [
    Tool(
        name="example_tool",
        description="Example tool - replace with your actual tool",
        inputSchema={
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "First parameter",
                },
                "param2": {
                    "type": "string",
                    "description": "Optional second parameter",
                },
            },
            "required": ["param1"],
        },
    ),
]


# =============================================================================
# MCP Server
# =============================================================================

def create_mcp_server() -> Server:
    """Create and configure the MCP server instance."""
    server = Server("template-mcp")  # Replace with your server name
    config = get_config()
    client = SDKClient()
    cache = DataCache() if config.enable_caching else None
    rate_limiter = RateLimiter(config.rate_limit_per_minute)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOL_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        await rate_limiter.acquire()

        if cache:
            cache_key = f"{name}:{json.dumps(arguments, sort_keys=True)}"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit for {name}")
                return [TextContent(type="text", text=json.dumps(cached_result, ensure_ascii=False, default=str))]

        try:
            result = await _execute_tool(client, name, arguments)
            if cache:
                cache.set(cache_key, result, config.cache_ttl_default)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            error_result = {"error": str(e), "tool": name, "arguments": arguments}
            return [TextContent(type="text", text=json.dumps(error_result, ensure_ascii=False))]

    return server


async def _execute_tool(client: SDKClient, name: str, arguments: dict) -> Dict[str, Any]:
    """Execute the specified tool - customize this for your tools."""
    if name == "example_tool":
        return await client.example_tool(
            param1=arguments["param1"],
            param2=arguments.get("param2"),
        )
    else:
        raise ValueError(f"Unknown tool: {name}")


# =============================================================================
# Starlette Application
# =============================================================================

def create_starlette_app() -> Starlette:
    """Create Starlette application with SSE endpoint."""
    mcp_server = create_mcp_server()
    sse_transport = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as streams:
            await mcp_server.run(
                streams[0],
                streams[1],
                mcp_server.create_initialization_options(),
            )
        return Response()

    async def handle_health(request: Request):
        return JSONResponse({
            "status": "ok",
            "server": "template-mcp",  # Replace with your server name
            "version": "1.0.0",
            "transport": "sse",
            "tools_count": len(TOOL_DEFINITIONS),
        })

    async def handle_tools_list(request: Request):
        tools = [
            {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
            for t in TOOL_DEFINITIONS
        ]
        return JSONResponse({"tools": tools, "count": len(tools)})

    routes = [
        Route("/health", handle_health, methods=["GET"]),
        Route("/tools", handle_tools_list, methods=["GET"]),
        Route("/sse", handle_sse, methods=["GET"]),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ]

    return Starlette(routes=routes)


# =============================================================================
# Entry Point
# =============================================================================

app = create_starlette_app()

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_SERVER_PORT", "8010"))

    logger.info(f"Starting MCP Server on {host}:{port}")
    logger.info(f"SSE endpoint: http://{host}:{port}/sse")
    logger.info(f"Health check: http://{host}:{port}/health")

    uvicorn.run(app, host=host, port=port)
