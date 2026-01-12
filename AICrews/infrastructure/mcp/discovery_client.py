"""
MCP Discovery Client - 轻量级 MCP 工具发现客户端

用于发现 MCP 服务器上的工具列表和健康检查。
这是一个简化的客户端，仅用于管理界面的工具发现功能。

注意：Agent 运行时应使用 NativeMCPConfigLoader 和 CrewAI 原生 MCP 集成。
"""

import asyncio
import httpx
from typing import List, Dict, Any, Optional
from AICrews.observability.logging import get_logger

logger = get_logger(__name__)


class MCPDiscoveryClient:
    """MCP 工具发现客户端
    
    用于管理界面的工具发现和健康检查功能。
    支持 SSE 和 HTTP 传输协议的 MCP 服务器。
    """
    
    def __init__(self, server_url: str, timeout: int = 10):
        """初始化发现客户端
        
        Args:
            server_url: MCP 服务器 URL
            timeout: 请求超时时间（秒）
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取 MCP 服务器上的工具列表
        
        Returns:
            工具列表，每个工具包含 name, description 等字段
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 尝试标准 MCP 端点
                endpoints = [
                    f"{self.server_url}/tools",
                    f"{self.server_url}/mcp/tools",
                    f"{self.server_url}/api/tools",
                    f"{self.server_url}/list_tools",
                ]
                
                for endpoint in endpoints:
                    try:
                        response = await client.get(endpoint)
                        if response.status_code == 200:
                            data = response.json()
                            # 处理不同的响应格式
                            if isinstance(data, list):
                                return data
                            elif isinstance(data, dict):
                                return data.get("tools", data.get("result", []))
                    except Exception:
                        continue
                
                # 尝试 JSON-RPC 格式
                try:
                    response = await client.post(
                        self.server_url,
                        json={
                            "jsonrpc": "2.0",
                            "method": "tools/list",
                            "id": 1,
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if "result" in data:
                            result = data["result"]
                            if isinstance(result, dict) and "tools" in result:
                                return result["tools"]
                            elif isinstance(result, list):
                                return result
                except Exception:
                    pass
                
                logger.warning(f"Could not discover tools from {self.server_url}")
                return []
                
        except Exception as e:
            logger.error(f"Error discovering tools from {self.server_url}: {e}")
            return []
    
    async def health_check(self) -> bool:
        """检查 MCP 服务器健康状态
        
        Returns:
            True 如果服务器健康，否则 False
        """
        try:
            tools = await asyncio.wait_for(
                self.list_tools(),
                timeout=float(self.timeout)
            )
            return len(tools) > 0
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for {self.server_url}")
            return False
        except Exception as e:
            logger.warning(f"Health check failed for {self.server_url}: {e}")
            return False


# 便捷函数
def get_mcp_discovery_client(server_url: str, timeout: int = 10) -> MCPDiscoveryClient:
    """获取 MCP 发现客户端实例
    
    Args:
        server_url: MCP 服务器 URL
        timeout: 请求超时时间（秒）
        
    Returns:
        MCPDiscoveryClient 实例
    """
    return MCPDiscoveryClient(server_url=server_url, timeout=timeout)
