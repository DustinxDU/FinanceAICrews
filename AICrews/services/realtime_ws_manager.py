"""
实时 WebSocket 管理器

提供 WebSocket 连接管理，支持：
- 价格实时推送
- 用户订阅管理
- Redis Pub/Sub 集成
"""

import json
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
import asyncio

from AICrews.observability.logging import get_logger

logger = get_logger(__name__)


class RealtimeWebSocketManager:
    """实时 WebSocket 管理器"""
    
    _instance: Optional['RealtimeWebSocketManager'] = None
    
    def __new__(cls) -> 'RealtimeWebSocketManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 价格连接：ticker -> connections
        self._price_connections: Dict[str, Set[WebSocket]] = {}
        
        # 用户连接：user_id -> connections
        self._user_connections: Dict[int, Set[WebSocket]] = {}
        
        # 连接信息
        self._connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Redis Pub/Sub 任务
        self._pubsub_task: Optional[asyncio.Task] = None
        self._running = False
        
        self._initialized = True
    
    # ==================== 连接管理 ====================
    
    async def connect_price(self, websocket: WebSocket, tickers: list = None) -> None:
        """连接价格 WebSocket"""
        await websocket.accept()
        
        # 初始化连接信息
        self._connection_info[websocket] = {
            "tickers": set(tickers or []),
            "user_id": None,
            "connected_at": None
        }
        
        # 如果没有指定 ticker，加入通用频道
        if not tickers:
            tickers = ["_all"]
        
        for ticker in tickers:
            if ticker not in self._price_connections:
                self._price_connections[ticker] = set()
            self._price_connections[ticker].add(websocket)
        
        logger.info(f"Price WebSocket connected: {len(tickers)} tickers")
    
    def disconnect_price(self, websocket: WebSocket) -> None:
        """断开价格 WebSocket 连接"""
        if websocket not in self._connection_info:
            return
        
        info = self._connection_info[websocket]
        tickers = info.get("tickers", set())
        
        # 从所有 ticker 频道移除
        for ticker in tickers:
            if ticker in self._price_connections:
                self._price_connections[ticker].discard(websocket)
                if not self._price_connections[ticker]:
                    del self._price_connections[ticker]
        
        # 清理用户连接
        user_id = info.get("user_id")
        if user_id and user_id in self._user_connections:
            self._user_connections[user_id].discard(websocket)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
        
        # 清理连接信息
        del self._connection_info[websocket]
        
        logger.info("Price WebSocket disconnected")
    
    def subscribe_tickers(self, websocket: WebSocket, tickers: list) -> None:
        """订阅额外的 ticker"""
        if websocket not in self._connection_info:
            return
        
        info = self._connection_info[websocket]
        current_tickers = info.get("tickers", set())
        
        for ticker in tickers:
            if ticker not in current_tickers:
                current_tickers.add(ticker)
                
                if ticker not in self._price_connections:
                    self._price_connections[ticker] = set()
                self._price_connections[ticker].add(websocket)
        
        info["tickers"] = current_tickers
    
    def unsubscribe_tickers(self, websocket: WebSocket, tickers: list) -> None:
        """取消订阅 ticker"""
        if websocket not in self._connection_info:
            return
        
        info = self._connection_info[websocket]
        current_tickers = info.get("tickers", set())
        
        for ticker in tickers:
            current_tickers.discard(ticker)
            if ticker in self._price_connections:
                self._price_connections[ticker].discard(websocket)
                if not self._price_connections[ticker]:
                    del self._price_connections[ticker]
        
        info["tickers"] = current_tickers
    
    # ==================== 消息广播 ====================
    
    async def broadcast_price_update(self, ticker: str, data: Dict[str, Any]) -> int:
        """广播价格更新到所有订阅者"""
        message = json.dumps({
            "type": "price_update",
            "ticker": ticker,
            "data": data
        })
        
        # 发送到具体 ticker 频道
        connections = self._price_connections.get(ticker, set()).copy()
        
        # 发送到 _all 频道（广播给所有连接）
        all_connections = self._price_connections.get("_all", set()).copy()
        connections.update(all_connections)
        
        sent_count = 0
        for connection in connections:
            try:
                await connection.send_text(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send price update: {e}")
                self.disconnect_price(connection)
        
        return sent_count
    
    async def send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """发送消息到单个连接"""
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.disconnect_price(websocket)
            return False
    
    # ==================== Redis Pub/Sub 集成 ====================
    
    async def start_redis_subscriber(self, redis_manager) -> None:
        """启动 Redis Pub/Sub 监听"""
        if self._running:
            return
        
        self._running = True
        
        # 订阅所有价格频道
        channels = [f"price:*"]
        
        self._pubsub_task = asyncio.create_task(
            self._redis_subscriber_loop(redis_manager, channels)
        )
        
        logger.info("Redis subscriber started")
    
    async def stop_redis_subscriber(self) -> None:
        """停止 Redis Pub/Sub 监听"""
        self._running = False
        
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Redis subscriber stopped")
    
    async def _redis_subscriber_loop(self, redis_manager, channels: list) -> None:
        """Redis Pub/Sub 循环"""
        try:
            async with redis_manager.subscribe(channels) as pubsub:
                async for message in pubsub.listen():
                    if not self._running:
                        break
                    
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            ticker = data.get("ticker")
                            if ticker:
                                await self.broadcast_price_update(ticker, data.get("data", {}))
                        except Exception as e:
                            logger.error(f"Error processing Redis message: {e}")
        except asyncio.CancelledError:
            logger.info("Redis subscriber loop cancelled")
        except Exception as e:
            logger.error(f"Redis subscriber error: {e}")
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        total_connections = sum(len(conns) for conns in self._price_connections.values())
        unique_tickers = len([k for k in self._price_connections.keys() if k != "_all"])
        
        return {
            "total_connections": total_connections,
            "unique_tickers": unique_tickers,
            "channels": list(self._price_connections.keys()),
            "running": self._running
        }


# 全局单例
_realtime_ws_manager: Optional[RealtimeWebSocketManager] = None


def get_realtime_ws_manager() -> RealtimeWebSocketManager:
    """获取实时 WebSocket 管理器单例"""
    global _realtime_ws_manager
    if _realtime_ws_manager is None:
        _realtime_ws_manager = RealtimeWebSocketManager()
    return _realtime_ws_manager
