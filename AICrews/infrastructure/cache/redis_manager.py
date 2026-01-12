"""
Redis 缓存管理器

提供统一的 Redis 连接和缓存操作接口，支持：
- 键值存储（带 TTL）
- 发布/订阅（用于实时推送）
- 连接池管理
"""

import json
from AICrews.observability.logging import get_logger
from typing import Optional, Any, Dict, List
from datetime import datetime
import redis.asyncio as redis
import redis as sync_redis
from contextlib import asynccontextmanager

logger = get_logger(__name__)


class RedisManager:
    """Redis 连接和缓存管理器"""
    
    _instance: Optional['RedisManager'] = None
    _pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    _sync_client: Optional[sync_redis.Redis] = None
    
    # Key 前缀设计
    PRICE_PREFIX = "price:"           # 单个资产价格
    PORTFOLIO_PREFIX = "portfolio:"   # 用户组合
    COCKPIT_PREFIX = "cockpit:"       # Cockpit 数据
    SUBSCRIPTION_PREFIX = "sub:"      # 订阅状态
    
    # TTL 配置（秒）
    PRICE_TTL = 400                   # 价格数据 400秒（需 >= 同步间隔 300s + 缓冲）
    PORTFOLIO_TTL = 60                # 组合数据 60秒
    COCKPIT_TTL = 60                  # Cockpit 数据 60秒
    
    def __new__(cls) -> 'RedisManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def init(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        max_connections: int = 50
    ) -> None:
        """初始化 Redis 连接池"""
        if self._pool is not None:
            logger.warning("Redis pool already initialized")
            return
            
        # 使用环境变量，优先支持 FAIC_ 前缀
        import os
        host = host or os.getenv("FAIC_INFRA_REDIS_HOST", os.getenv("REDIS_HOST", "localhost"))
        port = port or int(os.getenv("FAIC_INFRA_REDIS_PORT", os.getenv("REDIS_PORT", "6379")))
        db = db or int(os.getenv("FAIC_INFRA_REDIS_DB", os.getenv("REDIS_DB", "0")))
        password = password or os.getenv("FAIC_INFRA_REDIS_PASSWORD", os.getenv("REDIS_PASSWORD"))
            
        try:
            # 初始化异步连接池
            self._pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                decode_responses=True
            )
            self._client = redis.Redis(connection_pool=self._pool)
            
            # 初始化同步客户端 (用于线程池背景任务)
            self._sync_client = sync_redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )
            
            # 测试连接
            await self._client.ping()
            logger.info(f"Redis connected successfully: {host}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self) -> None:
        """关闭 Redis 连接

        Handles the case where the event loop might be closing/closed.
        """
        # Close async client first
        if self._client:
            try:
                await self._client.close()
            except RuntimeError as e:
                # Handle "Event loop is closed" error during shutdown
                if "Event loop is closed" in str(e) or "closed" in str(e).lower():
                    logger.debug("Redis async client close skipped (event loop closed)")
                else:
                    raise

        # Disconnect connection pool
        if self._pool:
            try:
                await self._pool.disconnect()
            except RuntimeError as e:
                # Handle "Event loop is closed" error during shutdown
                if "Event loop is closed" in str(e) or "closed" in str(e).lower():
                    logger.debug("Redis pool disconnect skipped (event loop closed)")
                else:
                    raise

        # Close sync client (no async issues)
        if self._sync_client:
            try:
                self._sync_client.close()
            except Exception as e:
                logger.debug(f"Redis sync client close error (ignored): {e}")

        self._client = None
        self._sync_client = None
        self._pool = None
        logger.info("Redis connection closed")
    
    # ==================== 基础操作 ====================
    
    def set_sync(self, key: str, value: Any, ttl: int = 60, json_encode: bool = True) -> bool:
        """同步版本的 set，用于非 asyncio 线程"""
        if not self._sync_client:
            return False
        try:
            if json_encode:
                value = json.dumps(value, default=str)
            self._sync_client.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis set_sync error: {e}")
            return False

    def incr_sync(self, key: str, amount: int = 1, ttl: int = 60) -> int:
        """同步版本的 incr，用于 rate limiting / 线程环境。

        - 返回当前计数；失败时返回 0
        - 仅在第一次递增时设置 TTL（避免每次续期）
        """
        if not self._sync_client:
            return 0
        try:
            value = int(self._sync_client.incr(key, int(amount)))
            if ttl and value == int(amount):
                try:
                    self._sync_client.expire(key, int(ttl))
                except Exception:
                    logger.debug("Redis expire failed for key=%s", key, exc_info=True)
            return value
        except Exception as e:
            logger.error(f"Redis incr_sync error: {e}")
            return 0

    def get_json_sync(self, key: str) -> Optional[Dict[str, Any]]:
        """同步版本的 get_json"""
        if not self._sync_client:
            return None
        try:
            value = self._sync_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Redis get_json_sync error: {e}")
        return None

    def keys_sync(self, pattern: str) -> List[str]:
        """同步版本的 keys，用于非 asyncio 线程"""
        if not self._sync_client:
            return []
        try:
            return self._sync_client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys_sync error: {e}")
            return []

    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not self._client:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """获取 JSON 格式的值"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for key {key}: {e}")
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 60,
        json_encode: bool = True
    ) -> bool:
        """设置值

        Handles event loop closed errors gracefully during shutdown.
        """
        if not self._client:
            return False
        try:
            if json_encode:
                value = json.dumps(value, default=str)
            await self._client.set(key, value, ex=ttl)
            return True
        except RuntimeError as e:
            # Handle "Event loop is closed" error during shutdown
            if "Event loop is closed" in str(e) or "closed" in str(e).lower():
                logger.debug(f"Redis set skipped (event loop closed): {key}")
                return False
            logger.error(f"Redis set error: {e}")
            return False
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def incr(self, key: str, amount: int = 1, ttl: int = 60) -> int:
        """INCR key with TTL (best-effort), returns new value; returns 0 if Redis unavailable.

        Handles event loop closed errors gracefully during shutdown.
        """
        if not self._client:
            return 0
        try:
            val = await self._client.incr(key, amount)
            if val == amount:
                await self._client.expire(key, ttl)
            return int(val)
        except RuntimeError as e:
            # Handle "Event loop is closed" error during shutdown
            if "Event loop is closed" in str(e) or "closed" in str(e).lower():
                logger.debug(f"Redis incr skipped (event loop closed): {key}")
                return 0
            logger.error(f"Redis incr error: {e}")
            return 0
        except Exception as e:
            logger.error(f"Redis incr error: {e}")
            return 0
    
    async def delete(self, key: str) -> bool:
        """删除键"""
        if not self._client:
            return False
        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """批量删除匹配模式的键"""
        if not self._client:
            return 0
        try:
            keys = await self._client.keys(pattern)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete_pattern error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self._client:
            return False
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    # ==================== 价格缓存操作 ====================
    
    def _price_key(self, ticker: str) -> str:
        """生成价格缓存键"""
        return f"{self.PRICE_PREFIX}{ticker}"
    
    async def get_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取单个资产价格"""
        return await self.get_json(self._price_key(ticker))
    
    async def set_price(self, ticker: str, data: Dict[str, Any], ttl: int = None) -> bool:
        """设置单个资产价格"""
        if ttl is None:
            ttl = self.PRICE_TTL
        
        # 添加时间戳
        data["cached_at"] = datetime.now().isoformat()
        
        return await self.set(
            self._price_key(ticker),
            data,
            ttl=ttl
        )
    
    async def delete_price(self, ticker: str) -> bool:
        """删除价格缓存"""
        return await self.delete(self._price_key(ticker))
    
    async def get_multiple_prices(self, tickers: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """批量获取多个资产价格"""
        if not self._client:
            return {t: None for t in tickers}
        
        try:
            keys = [self._price_key(t) for t in tickers]
            values = await self._client.mget(keys)
            
            result = {}
            for ticker, value in zip(tickers, values):
                if value:
                    try:
                        result[ticker] = json.loads(value)
                    except json.JSONDecodeError:
                        result[ticker] = None
                else:
                    result[ticker] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Redis mget error: {e}")
            return {t: None for t in tickers}
    
    # ==================== 组合缓存操作 ====================
    
    def _portfolio_key(self, user_id: int) -> str:
        """生成用户组合缓存键"""
        return f"{self.PORTFOLIO_PREFIX}{user_id}"
    
    async def get_user_portfolio(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """获取用户关注的资产列表"""
        return await self.get_json(self._portfolio_key(user_id))
    
    async def set_user_portfolio(
        self,
        user_id: int,
        assets: List[Dict[str, Any]],
        ttl: int = None
    ) -> bool:
        """设置用户关注的资产列表"""
        if ttl is None:
            ttl = self.PORTFOLIO_TTL
        return await self.set(
            self._portfolio_key(user_id),
            assets,
            ttl=ttl
        )
    
    async def invalidate_user_portfolio(self, user_id: int) -> bool:
        """使用户组合缓存失效"""
        return await self.delete(self._portfolio_key(user_id))
    
    # ==================== Cockpit 缓存操作 ====================
    
    def _cockpit_key(self, user_id: int) -> str:
        """生成 Cockpit 数据缓存键"""
        return f"{self.COCKPIT_PREFIX}{user_id}"
    
    async def get_cockpit_dashboard(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取 Cockpit 仪表盘数据"""
        return await self.get_json(self._cockpit_key(user_id))
    
    async def set_cockpit_dashboard(
        self,
        user_id: int,
        data: Dict[str, Any],
        ttl: int = None
    ) -> bool:
        """设置 Cockpit 仪表盘数据"""
        if ttl is None:
            ttl = self.COCKPIT_TTL
        return await self.set(
            self._cockpit_key(user_id),
            data,
            ttl=ttl
        )
    
    async def invalidate_cockpit(self, user_id: int) -> bool:
        """使 Cockpit 缓存失效"""
        return await self.delete(self._cockpit_key(user_id))
    
    # ==================== 发布/订阅（实时推送） ====================
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """发布消息到频道"""
        if not self._client:
            return 0
        try:
            return await self._client.publish(
                channel,
                json.dumps(message, default=str)
            )
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            return 0
    
    def publish_channel(self, ticker: str) -> str:
        """生成价格更新频道名"""
        return f"{self.PRICE_PREFIX}{ticker}"
    
    async def publish_price_update(self, ticker: str, data: Dict[str, Any]) -> int:
        """发布价格更新"""
        message = {
            "type": "price_update",
            "ticker": ticker,
            "data": {
                **data,
                "timestamp": datetime.now().isoformat()
            }
        }
        return await self.publish(self.publish_channel(ticker), message)
    
    @asynccontextmanager
    async def subscribe(self, channels: List[str]):
        """订阅频道（上下文管理器）"""
        if not self._client:
            raise RuntimeError("Redis not initialized")
        
        pubsub = self._client.pubsub()
        await pubsub.subscribe(*channels)
        
        try:
            yield pubsub
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
    
    # ==================== 订阅者计数操作 ====================
    
    def _subscriber_key(self, ticker: str) -> str:
        """生成订阅者计数键"""
        return f"{self.SUBSCRIPTION_PREFIX}count:{ticker}"
    
    async def increment_subscriber(self, ticker: str) -> int:
        """增加订阅者计数"""
        if not self._client:
            return 0
        try:
            return await self._client.incr(self._subscriber_key(ticker))
        except Exception as e:
            logger.error(f"Redis incr error: {e}")
            return 0
    
    async def decrement_subscriber(self, ticker: str) -> int:
        """减少订阅者计数"""
        if not self._client:
            return 0
        try:
            result = await self._client.decr(self._subscriber_key(ticker))
            # 确保不返回负数
            if result < 0:
                await self._client.set(self._subscriber_key(ticker), 0)
                return 0
            return result
        except Exception as e:
            logger.error(f"Redis decr error: {e}")
            return 0
    
    async def get_subscriber_count(self, ticker: str) -> int:
        """获取订阅者计数"""
        if not self._client:
            return 0
        try:
            value = await self._client.get(self._subscriber_key(ticker))
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return 0
    
    # ==================== 统计信息 ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取 Redis 统计信息"""
        if not self._client:
            return {"status": "disconnected"}
        
        try:
            info = await self._client.info("memory")
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": await self._client.info("clients"),
                "uptime_seconds": await self._client.info("uptime_in_seconds"),
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"status": "error", "error": str(e)}


# 全局单例
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """获取 Redis 管理器单例"""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


async def init_redis(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None
) -> RedisManager:
    """初始化 Redis 连接"""
    manager = get_redis_manager()
    await manager.init(host=host, port=port, db=db, password=password)
    return manager


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global _redis_manager
    if _redis_manager:
        await _redis_manager.close()
        _redis_manager = None
