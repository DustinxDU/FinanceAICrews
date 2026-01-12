#!/usr/bin/env python3
"""
MCP Servers Startup Script

启动 OpenBB MCP 和 Akshare MCP 服务器
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.devtools.akshare_server import start_akshare_server
from AICrews.config.settings import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | [%(levelname)s] | %(message)s'
)
logger = logging.getLogger(__name__)


class MCPServerManager:
    """MCP 服务器管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.servers = []
        self.running = False
    
    async def start_openbb_server(self):
        """启动 OpenBB MCP 服务器"""
        # OpenBB MCP 已容器化，建议用 docker-compose 管理：
        #   docker-compose up -d openbb_mcp
        # 主机端点示例 http://localhost:8008/mcp/ （streamable-http，取决于端口映射）
        logger.info("OpenBB MCP server is expected to run via docker compose service: openbb_mcp")
        logger.info("If not running, start with: docker compose up -d openbb_mcp")
        return None
    
    async def start_akshare_server(self):
        """启动 Akshare MCP 服务器"""
        logger.info(f"Starting Akshare MCP server on {self.settings.mcp.akshare['mcp_server_url']}")
        
        # 解析 URL 获取 host 和 port
        url = self.settings.mcp.akshare['mcp_server_url']
        if url.startswith('ws://'):
            url = url[5:]
        host, port = url.split(':')
        port = int(port)
        
        # 启动服务器
        server_task = asyncio.create_task(start_akshare_server(host, port))
        self.servers.append(('akshare', server_task))
        
        return server_task
    
    async def start_all_servers(self):
        """启动所有 MCP 服务器"""
        logger.info("Starting MCP servers...")
        
        # 启动 Akshare 服务器
        await self.start_akshare_server()
        
        # 提示启动 OpenBB 服务器
        await self.start_openbb_server()
        
        self.running = True
        logger.info("All MCP servers started successfully")
        
        # 等待中断信号
        await self._wait_for_shutdown()
    
    async def _wait_for_shutdown(self):
        """等待关闭信号"""
        shutdown_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            shutdown_event.set()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 等待关闭事件
        await shutdown_event.wait()
        
        # 关闭所有服务器
        await self.shutdown_all_servers()
    
    async def shutdown_all_servers(self):
        """关闭所有服务器"""
        logger.info("Shutting down MCP servers...")
        
        for name, task in self.servers:
            logger.info(f"Shutting down {name} server...")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.servers.clear()
        self.running = False
        logger.info("All MCP servers shutdown complete")


async def main():
    """主函数"""
    # 检查 MCP 是否启用
    settings = get_settings()
    if not settings.mcp.enabled:
        logger.warning("MCP is disabled in settings. Set MCP_ENABLED=true to enable.")
        return
    
    # 创建服务器管理器
    manager = MCPServerManager()
    
    # 启动服务器
    await manager.start_all_servers()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, exiting...")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
