"""
统一数据同步服务 (Unified Sync Service)

合并了 subscription_sync_service 和 data_sync_service 的功能，提供：
- 基于 Redis 的高速缓存
- WebSocket 实时推送
- 统一的订阅管理

核心逻辑：
1. 触发 (Trigger)：用户关注资产
2. 任务注册 (Registration)：检查是否已在活跃监控，启动同步
3. 数据拉取 (Fetch & Cache)：调用 MCP API，更新 Redis + DB
4. 共享 (Sharing)：多用户共享同一份 Redis 缓存
5. 推送 (Push)：WebSocket 实时推送更新
6. 注销 (Deregistration)：无用户关注时停止同步
"""

import asyncio
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

from AICrews.database.models import (
    Asset,
    UserPortfolio,
    RealtimeQuote,
    ActiveMonitoring,
)
from AICrews.database.db_manager import get_db_session
from AICrews.infrastructure.cache.redis_manager import get_redis_manager
from AICrews.services.realtime_ws_manager import get_realtime_ws_manager
from AICrews.infrastructure.data_fetcher import (
    get_yfinance_fetcher,
    get_akshare_fetcher,
    detect_market,
    MarketType,
    is_yfinance_rate_limited,
    get_yfinance_cooldown_remaining,
)
from AICrews.observability.logging import get_logger
from AICrews.config.settings import get_settings

logger = get_logger(__name__)


@dataclass
class SyncTask:
    """同步任务信息

    默认值从 SyncConfig 配置获取，支持通过环境变量覆盖。
    """

    ticker: str
    asset_type: str
    subscriber_count: int = 0
    last_sync_at: Optional[datetime] = None
    task_handle: Optional[asyncio.Task] = None
    error_count: int = 0
    is_running: bool = False

    # 从配置获取默认值
    sync_interval_seconds: int = field(default_factory=lambda: get_settings().sync.default_interval)
    base_interval_seconds: int = field(default_factory=lambda: get_settings().sync.base_interval)
    max_interval_seconds: int = field(default_factory=lambda: get_settings().sync.max_interval)
    max_errors: int = field(default_factory=lambda: get_settings().sync.max_errors)


class UnifiedSyncService:
    """统一数据同步服务 - 使用 SDK Fetcher 获取数据"""

    def __init__(self):
        self.sync_tasks: Dict[str, SyncTask] = {}
        self.yfinance_fetcher = get_yfinance_fetcher()
        self.akshare_fetcher = get_akshare_fetcher()
        self.redis = get_redis_manager()
        self.ws_manager = get_realtime_ws_manager()
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.is_running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """启动同步服务"""
        if self.is_running:
            logger.warning("Unified sync service is already running")
            return

        self.is_running = True
        self._shutdown_event.clear()

        logger.info("Starting unified sync service...")

        # 恢复活跃监控任务
        await self._restore_active_monitoring()

        # 启动 Redis Pub/Sub 监听
        await self.ws_manager.start_redis_subscriber(self.redis)

        # 启动主循环
        asyncio.create_task(self._main_loop())

        logger.info("Unified sync service started successfully")

    async def stop(self) -> None:
        """停止同步服务"""
        if not self.is_running:
            return

        logger.info("Stopping unified sync service...")

        self.is_running = False
        self._shutdown_event.set()

        # 停止 Redis Pub/Sub
        await self.ws_manager.stop_redis_subscriber()

        # 停止所有同步任务
        for task_info in self.sync_tasks.values():
            if task_info.task_handle and not task_info.task_handle.done():
                task_info.task_handle.cancel()
                try:
                    await task_info.task_handle
                except asyncio.CancelledError:
                    pass

        self.executor.shutdown(wait=True)
        logger.info("Unified sync service stopped")

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "is_running": self.is_running,
            "tasks_count": len(self.sync_tasks),
            "active_tasks": sum(
                1 for t in self.sync_tasks.values() if getattr(t, "is_running", False)
            ),
            "total_errors": sum(t.error_count for t in self.sync_tasks.values()),
        }

    async def register_subscription(
        self, user_id: int, ticker: str, asset_type: str = None
    ) -> bool:
        """用户订阅资产时调用

        Args:
            user_id: 用户ID
            ticker: 资产代码
            asset_type: 资产类型（可选，从数据库获取）

        Returns:
            是否成功
        """
        try:
            async with get_db_session() as session:
                # 检查/创建 Asset
                asset = await session.get(Asset, ticker)
                if not asset:
                    if not asset_type:
                        asset_type = self._guess_asset_type(ticker)
                    asset_info = await self._fetch_asset_info(ticker, asset_type)
                    if not asset_info:
                        logger.error(f"Failed to fetch asset info for {ticker}")
                        return False
                    asset = Asset(**asset_info)
                    session.add(asset)
                elif not asset_type:
                    asset_type = asset.asset_type

                # 检查活跃监控状态
                monitoring = await session.get(ActiveMonitoring, ticker)
                if monitoring:
                    # 已存在，增加订阅者数量
                    monitoring.subscriber_count += 1
                    logger.info(
                        f"Increased subscriber count for {ticker} to {monitoring.subscriber_count}"
                    )
                else:
                    # 不存在，创建新的监控记录并启动任务
                    monitoring = ActiveMonitoring(
                        ticker=ticker,
                        subscriber_count=1,
                        sync_interval_minutes=1,
                        is_active=True,
                    )
                    session.add(monitoring)

                    # 启动同步任务（立即执行一次）
                    await self._start_sync_task(ticker, asset.asset_type)
                    logger.info(f"Started new sync task for {ticker}")

                await session.commit()

                # 同步更新 Redis 订阅计数
                await self.redis.set(
                    f"sub:count:{ticker}", monitoring.subscriber_count, ttl=3600
                )

                return True

        except Exception as e:
            logger.error(f"Error registering subscription for {ticker}: {e}")
            return False

    async def unregister_subscription(self, user_id: int, ticker: str) -> bool:
        """用户取消订阅资产时调用"""
        try:
            async with get_db_session() as session:
                monitoring = await session.get(ActiveMonitoring, ticker)
                if not monitoring:
                    logger.warning(f"No active monitoring found for {ticker}")
                    return True

                monitoring.subscriber_count -= 1

                if monitoring.subscriber_count <= 0:
                    # 没有订阅者了，停止任务并删除监控记录
                    await self._stop_sync_task(ticker)
                    await session.delete(monitoring)
                    logger.info(f"Stopped sync task for {ticker} - no subscribers")
                else:
                    logger.info(
                        f"Decreased subscriber count for {ticker} to {monitoring.subscriber_count}"
                    )

                await session.commit()

                # 同步更新 Redis
                await self.redis.set(
                    f"sub:count:{ticker}", monitoring.subscriber_count, ttl=3600
                )

                return True

        except Exception as e:
            logger.error(f"Error unregistering subscription for {ticker}: {e}")
            return False

    async def get_price(
        self, ticker: str, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """获取资产价格（优先从 Redis）"""
        # 尝试从 Redis 获取
        if not force_refresh:
            cached = await self.redis.get_price(ticker)
            if cached:
                cached["source"] = "cache"
                return cached

        # 从数据库获取
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(RealtimeQuote).where(RealtimeQuote.ticker == ticker)
                )
                quote = result.scalar_one_or_none()
                if quote:
                    data = {
                        "price": quote.price,
                        "price_local": quote.price_local,
                        "change_percent": quote.change_percent,
                        "change_value": quote.change_value,
                        "volume": quote.volume,
                        "last_updated": quote.last_updated.isoformat()
                        if quote.last_updated
                        else None,
                        "source": "database",
                    }
                    return data
        except Exception as e:
            logger.error(f"Error fetching price from database: {e}")

        return None

    async def get_user_prices(self, user_id: int, tickers: list) -> Dict[str, Any]:
        """获取用户关注的多个资产价格"""
        result = {}

        # 并行从 Redis 获取
        prices = await self.redis.get_multiple_prices(tickers)

        for ticker, price_data in prices.items():
            if price_data:
                result[ticker] = price_data
            else:
                # 尝试从数据库获取
                db_price = await self.get_price(ticker)
                if db_price:
                    result[ticker] = db_price
                else:
                    # 返回占位数据
                    result[ticker] = {
                        "ticker": ticker,
                        "price": None,
                        "change_percent": None,
                        "source": "pending",
                        "error": "Data not available",
                    }

        return result

    async def _main_loop(self) -> None:
        """主循环：定期检查和清理任务"""
        while self.is_running:
            try:
                # 检查订阅者变化并同步活跃监控列表
                await self._sync_active_monitoring()

                # 清理错误过多的任务
                await self._cleanup_failed_tasks()

                # 等待30秒或收到停止信号
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=30.0)
                    break  # 收到停止信号
                except asyncio.TimeoutError:
                    continue  # 继续循环

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)

    async def _restore_active_monitoring(self) -> None:
        """恢复已有的活跃监控任务"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(ActiveMonitoring)
                    .where(ActiveMonitoring.is_active == True)
                    .where(ActiveMonitoring.subscriber_count > 0)
                )

                # 获取所有监控记录并启动任务
                monitorings = result.scalars().all()
                for monitoring in monitorings:
                    await self._start_sync_task(monitoring.ticker, None)
                    logger.info(f"Restored sync task for {monitoring.ticker}")

        except Exception as e:
            logger.error(f"Error restoring active monitoring: {e}")

    async def _start_sync_task(self, ticker: str, asset_type: str = None) -> None:
        """启动特定资产的同步任务"""
        if ticker in self.sync_tasks:
            logger.warning(f"Sync task for {ticker} already exists")
            return

        # 如果没有指定 asset_type，从数据库获取
        if not asset_type:
            try:
                async with get_db_session() as session:
                    asset = await session.get(Asset, ticker)
                    if asset:
                        asset_type = asset.asset_type
            except Exception as e:
                logger.debug(f"Failed to fetch asset type for {ticker} from DB: {e}")

        if not asset_type:
            asset_type = self._guess_asset_type(ticker)

        # SyncTask 会从 SyncConfig 获取默认值
        task_info = SyncTask(
            ticker=ticker,
            asset_type=asset_type,
            subscriber_count=0,  # 从数据库同步
        )

        # 创建异步任务
        task_handle = asyncio.create_task(self._sync_asset_loop(task_info))
        task_info.task_handle = task_handle

        self.sync_tasks[ticker] = task_info
        logger.info(f"Started sync task for {ticker} ({asset_type})")

    async def _stop_sync_task(self, ticker: str) -> None:
        """停止特定资产的同步任务"""
        if ticker not in self.sync_tasks:
            logger.warning(f"No sync task found for {ticker}")
            return

        task_info = self.sync_tasks[ticker]
        if task_info.task_handle and not task_info.task_handle.done():
            task_info.task_handle.cancel()
            try:
                await task_info.task_handle
            except asyncio.CancelledError:
                pass

        del self.sync_tasks[ticker]

        # 清理 Redis 缓存
        await self.redis.delete_price(ticker)

        logger.info(f"Stopped sync task for {ticker}")

    async def _sync_asset_loop(self, task_info: SyncTask) -> None:
        """单个资产的同步循环"""
        ticker = task_info.ticker

        # 立即执行一次同步
        await self._sync_single_asset(ticker, task_info.asset_type)

        while self.is_running:
            try:
                task_info.is_running = True

                # 获取最新数据
                success = await self._sync_single_asset(ticker, task_info.asset_type)

                if success:
                    task_info.error_count = 0
                    # Gradually recover interval back to base (fast recovery without oscillation)
                    if (
                        task_info.sync_interval_seconds
                        > task_info.base_interval_seconds
                    ):
                        task_info.sync_interval_seconds = max(
                            task_info.base_interval_seconds,
                            int(task_info.sync_interval_seconds * 0.75),
                        )
                else:
                    task_info.error_count += 1
                    # Exponential backoff under persistent failures (e.g., provider limits/timeouts)
                    task_info.sync_interval_seconds = min(
                        task_info.max_interval_seconds,
                        max(
                            task_info.base_interval_seconds,
                            task_info.sync_interval_seconds * 2,
                        ),
                    )
                    logger.warning(
                        f"Failed to sync {ticker} (error count: {task_info.error_count})"
                    )

                task_info.is_running = False

                # 等待下次同步
                await asyncio.sleep(task_info.sync_interval_seconds)

            except asyncio.CancelledError:
                logger.info(f"Sync task for {ticker} was cancelled")
                break
            except Exception as e:
                task_info.error_count += 1
                logger.error(f"Error in sync loop for {ticker}: {e}")
                await asyncio.sleep(30)  # 出错时等待30秒再重试

        task_info.is_running = False

    async def _sync_single_asset(self, ticker: str, asset_type: str) -> bool:
        """同步单个资产数据"""
        try:
            # 调用 MCP 获取数据
            if asset_type in ["US", "CRYPTO"]:
                data = await self._fetch_quote(ticker, asset_type)
            else:
                data = await self._fetch_quote(ticker, asset_type)

            if not data:
                return False

            # 更新 Redis 缓存
            await self.redis.set_price(ticker, data)

            # 异步更新数据库
            asyncio.create_task(self._update_db(ticker, data))

            # WebSocket 推送
            await self.ws_manager.broadcast_price_update(ticker, data)

            logger.debug(f"Synced {ticker}: price={data.get('price')}")
            return True

        except Exception as e:
            logger.error(f"Error syncing {ticker}: {e}")
            return False

    async def _fetch_price_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """使用 SDK Fetcher 获取价格数据

        v2.0 优化：添加备用数据源机制。
        当主数据源失败时，自动尝试备用数据源。

        v2.1 修复：当主数据源返回 None 时也尝试备用数据源。

        v2.2 增强：当所有数据源都失败时，使用 Redis 缓存的旧数据作为降级方案。

        v2.3 优化：在 YFinance 限流时直接跳过请求，使用缓存数据。

        路由逻辑：
        - US/CRYPTO/其他: 主 YFinance → 备用 AkShare → Redis 缓存
        - CN/HK: 主 AkShare → 备用 YFinance → Redis 缓存
        """
        market = detect_market(ticker)

        # 定义主/备数据源
        if market in [MarketType.CN, MarketType.HK]:
            primary_fetcher = self.akshare_fetcher
            backup_fetcher = self.yfinance_fetcher
            primary_name = "akshare"
            backup_name = "yfinance"
            primary_is_yfinance = False
        else:
            primary_fetcher = self.yfinance_fetcher
            backup_fetcher = self.akshare_fetcher
            primary_name = "yfinance"
            backup_name = "akshare"
            primary_is_yfinance = True

        price = None

        # 检查 YFinance 是否处于限流状态
        yf_rate_limited = is_yfinance_rate_limited()
        if yf_rate_limited:
            cooldown_remaining = get_yfinance_cooldown_remaining()
            logger.debug(
                f"YFinance rate limited for {ticker}, cooldown remaining: {cooldown_remaining:.1f}s"
            )

        # 尝试主数据源（如果是 YFinance 且被限流，则跳过）
        if not (primary_is_yfinance and yf_rate_limited):
            try:
                if market == MarketType.CRYPTO:
                    price = await self.yfinance_fetcher.fetch_crypto_price(ticker)
                else:
                    price = await primary_fetcher.fetch_price(ticker)

                if price:
                    price["_source"] = primary_name
                    return price
                else:
                    logger.debug(f"Primary source ({primary_name}) returned no data for {ticker}")
            except Exception as e:
                logger.warning(f"Primary source ({primary_name}) failed for {ticker}: {e}")

        # 主数据源失败或被跳过，尝试备用数据源（如果是 YFinance 且被限流，则跳过）
        backup_is_yfinance = not primary_is_yfinance
        if not (backup_is_yfinance and yf_rate_limited):
            try:
                logger.info(f"Trying backup source ({backup_name}) for {ticker}")
                price = await backup_fetcher.fetch_price(ticker)
                if price:
                    price["_source"] = backup_name
                    return price
            except Exception as e:
                logger.debug(f"Backup source ({backup_name}) also failed for {ticker}: {e}")

        # 所有数据源都失败或被跳过，尝试使用 Redis 缓存的旧数据
        try:
            cached = await self.redis.get_price(ticker)
            if cached:
                logger.warning(
                    f"All data sources unavailable for {ticker}, using cached data "
                    f"(last_updated: {cached.get('last_updated', 'unknown')})"
                )
                cached["_source"] = "cache_fallback"
                cached["_stale"] = True
                return cached
        except Exception as e:
            logger.debug(f"Redis cache fallback also failed for {ticker}: {e}")

        return None

    async def _fetch_quote(
        self, ticker: str, asset_type: str
    ) -> Optional[Dict[str, Any]]:
        """获取报价数据 - 使用 SDK Fetcher"""
        price_data = await self._fetch_price_data(ticker)

        if price_data:
            return self._normalize_quote_data(price_data, ticker)

        return None
    def _normalize_quote_data(
        self, data: Dict[str, Any], ticker: str
    ) -> Dict[str, Any]:
        """标准化报价数据"""
        return {
            "ticker": ticker,
            "price": data.get("price") or data.get("regularMarketPrice"),
            "change_percent": data.get("change_percent")
            or data.get("regularMarketChangePercent"),
            "change_value": data.get("change") or data.get("regularMarketChange"),
            "volume": data.get("volume") or data.get("regularMarketVolume"),
            "open": data.get("open") or data.get("regularMarketOpen"),
            "high": data.get("high") or data.get("regularMarketDayHigh"),
            "low": data.get("low") or data.get("regularMarketDayLow"),
            "previous_close": data.get("previousClose")
            or data.get("regularMarketPreviousClose"),
            "market_cap": data.get("marketCap"),
            "timestamp": datetime.now().isoformat(),
        }

    async def _update_db(self, ticker: str, data: Dict[str, Any]) -> None:
        """异步更新数据库"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(RealtimeQuote).where(RealtimeQuote.ticker == ticker)
                )
                existing = result.scalar_one_or_none()

                current_time = datetime.now()

                if existing:
                    # 更新
                    existing.price = data.get("price")
                    existing.change_percent = data.get("change_percent")
                    existing.change_value = data.get("change_value")
                    existing.volume = data.get("volume")
                    existing.last_updated = current_time
                    existing.fetch_error = None
                else:
                    # 创建
                    new_quote = RealtimeQuote(
                        ticker=ticker,
                        price=data.get("price"),
                        change_percent=data.get("change_percent"),
                        change_value=data.get("change_value"),
                        volume=data.get("volume"),
                        last_updated=current_time,
                        data_source="mcp",
                    )
                    session.add(new_quote)

                await session.commit()

        except Exception as e:
            logger.error(f"Error updating database for {ticker}: {e}")

    async def _fetch_asset_info(
        self, ticker: str, asset_type: str
    ) -> Optional[Dict[str, Any]]:
        """获取资产基础信息"""
        try:
            info = {"name": ticker, "asset_type": asset_type}

            if asset_type == "US":
                result = await self.yfinance_fetcher.fetch_quote(ticker)
                if result and isinstance(result, dict):
                    info["name"] = result.get("name", ticker)
                    info["exchange"] = result.get("exchange")
                    info["sector"] = result.get("sector")
                    info["industry"] = result.get("industry")

            return {
                "ticker": ticker,
                "name": info.get("name", ticker),
                "asset_type": asset_type,
                "exchange": info.get("exchange"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "currency": "USD",
                "is_active": True,
            }
        except Exception as e:
            logger.warning(f"Failed to fetch asset info for {ticker} ({asset_type}): {e}")
            return None

    def _guess_asset_type(self, ticker: str) -> str:
        """猜测资产类型"""
        if ticker.endswith(".SS") or ticker.endswith(".SZ"):
            return "CN"
        if ticker.endswith(".HK"):
            return "HK"
        if "-" in ticker:  # e.g. BTC-USD
            return "CRYPTO"
        return "US"

    async def _sync_active_monitoring(self) -> None:
        """同步活跃监控任务"""
        # 简单实现：这里可以添加逻辑来检查数据库中状态变化
        # 当前实现主要依赖 register_subscription 和 unregister_subscription 来维护
        pass

    async def _cleanup_failed_tasks(self) -> None:
        """清理失败过多的任务"""
        failed_tickers = []
        for ticker, task in self.sync_tasks.items():
            if task.error_count > task.max_errors:
                failed_tickers.append(ticker)

        for ticker in failed_tickers:
            logger.warning(f"Stopping sync task for {ticker} due to excessive errors")
            await self._stop_sync_task(ticker)


# 全局单例
_unified_sync_service: Optional[UnifiedSyncService] = None


def get_unified_sync_service() -> UnifiedSyncService:
    """获取统一同步服务单例"""
    global _unified_sync_service
    if _unified_sync_service is None:
        _unified_sync_service = UnifiedSyncService()
    return _unified_sync_service


async def start_unified_sync_service():
    """启动统一同步服务"""
    service = get_unified_sync_service()
    await service.start()


async def stop_unified_sync_service():
    """停止统一同步服务"""
    service = get_unified_sync_service()
    await service.stop()
