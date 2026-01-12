"""
Cockpit Macro Indicator Sync Service

目标：将 Cockpit 宏观指标从外部数据源拉取后，写入 DB（macro_indicator_cache）并写入 Redis 热缓存。

约束：
- 读路径（API）不触发外部 I/O
- 常驻任务必须可 start/stop，并由 backend/app/core/lifespan.py 统一启停
"""

from __future__ import annotations

import asyncio
import math
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select

from AICrews.observability.logging import get_logger
from AICrews.database.db_manager import get_db_session
from AICrews.database.models.cockpit import MacroIndicatorCache
from AICrews.infrastructure.cache.redis_manager import get_redis_manager
from AICrews.infrastructure.data_fetcher import (
    get_yfinance_fetcher,
    is_yfinance_rate_limited,
    get_yfinance_cooldown_remaining,
)
from AICrews.services.market_service import COCKPIT_MACRO_CONFIG

logger = get_logger(__name__)


MACRO_REDIS_KEY = "cockpit:macro:all"


def _sanitize_for_json(data: Any) -> Any:
    """清理数据中的 NaN/Inf 值，使其可以安全存储到 PostgreSQL JSON 字段。
    
    PostgreSQL JSON 类型不支持 NaN 和 Infinity，需要转换为 None。
    """
    if data is None:
        return None
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    if isinstance(data, dict):
        return {k: _sanitize_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_for_json(item) for item in data]
    return data


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全地将值转换为 float，处理 NaN 和无效值。"""
    if value is None:
        return default
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


class CockpitMacroSyncService:
    def __init__(self):
        self.redis = get_redis_manager()
        self.yfinance_fetcher = get_yfinance_fetcher()
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self.is_running:
            return

        self.is_running = True
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("CockpitMacroSyncService started")

    async def stop(self) -> None:
        if not self.is_running:
            return

        self.is_running = False
        self._shutdown_event.set()

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("CockpitMacroSyncService stopped")

    def _interval_seconds(self) -> int:
        return int(
            os.getenv("FAIC_COCKPIT_MACRO_SYNC_INTERVAL_SECONDS", "600")
        )  # default 10min

    async def _run_loop(self) -> None:
        interval = self._interval_seconds()

        # Startup: run once quickly
        try:
            await self.sync_once()
        except Exception as exc:
            logger.error("Initial macro sync failed: %s", exc, exc_info=True)

        while self.is_running:
            try:
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), timeout=interval
                    )
                    break
                except asyncio.TimeoutError:
                    pass

                await self.sync_once()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Macro sync loop error: %s", exc, exc_info=True)
                await asyncio.sleep(5)

    async def sync_once(self) -> None:
        """同步宏观指标数据
        
        v2.0 优化：使用批量请求减少 API 调用次数。
        将 9 次独立请求合并为 1 次批量请求。
        
        v2.1 降级策略：当外部 API 完全失败时，使用 DB 缓存刷新 Redis，
        确保 API 读取路径始终有数据可用。
        
        v2.2 优化：在 YFinance 限流时直接跳过请求，使用 DB 缓存。
        """
        now = datetime.now()
        updated: List[Dict[str, Any]] = []

        # 检查 YFinance 是否处于限流状态
        if is_yfinance_rate_limited():
            cooldown_remaining = get_yfinance_cooldown_remaining()
            logger.warning(
                f"YFinance rate limited, skipping sync and using DB cache "
                f"(cooldown remaining: {cooldown_remaining:.1f}s)"
            )
            # 直接从 DB 读取旧数据刷新 Redis
            await self._refresh_redis_from_db()
            return

        # 收集所有需要获取的 yf_symbol
        symbols_map: Dict[str, str] = {}  # yf_symbol -> indicator_id
        for code, config in COCKPIT_MACRO_CONFIG.items():
            indicator_id = config.get("id", code)
            yf_symbol = config.get("yf_symbol", config.get("symbol", indicator_id))
            symbols_map[yf_symbol] = indicator_id

        # 批量获取所有价格数据（1 次 API 调用代替 9 次）
        batch_results: Dict[str, Optional[Dict[str, Any]]] = {}
        fetch_failed_completely = False
        
        try:
            batch_results = await self.yfinance_fetcher.fetch_prices_batch(
                list(symbols_map.keys())
            )
        except Exception as exc:
            logger.warning("Batch fetch failed: %s, trying individual fetches", exc)
            # 回退到单个获取
            for yf_symbol in symbols_map.keys():
                try:
                    batch_results[yf_symbol] = await self.yfinance_fetcher.fetch_price(yf_symbol)
                except Exception as e:
                    logger.debug(f"Individual fetch failed for {yf_symbol}: {e}")
                    batch_results[yf_symbol] = None

        # 检查是否所有请求都失败了
        successful_fetches = sum(1 for v in batch_results.values() if v is not None)
        if successful_fetches == 0:
            fetch_failed_completely = True
            logger.warning(
                "All external fetches failed, will use DB cache as fallback for Redis"
            )

        async with get_db_session() as session:
            for code, config in COCKPIT_MACRO_CONFIG.items():
                indicator_id = config.get("id", code)
                yf_symbol = config.get("yf_symbol", config.get("symbol", indicator_id))

                result = batch_results.get(yf_symbol)
                error: Optional[str] = None if result else "No data from batch fetch"

                row = (
                    await session.execute(
                        select(MacroIndicatorCache).where(
                            MacroIndicatorCache.indicator_id == indicator_id
                        )
                    )
                ).scalar_one_or_none()

                if not row:
                    row = MacroIndicatorCache(
                        indicator_id=indicator_id,
                        indicator_name=config.get("name", indicator_id),
                        symbol=config.get("symbol", indicator_id),
                        indicator_type=config.get("type", "macro"),
                        is_critical=bool(config.get("critical", False)),
                        data_source="sdk:yfinance:batch",
                        last_updated=now,
                        is_active=True,
                    )
                    session.add(row)

                if not result:
                    row.fetch_error = error or "No data returned"
                    # 即使获取失败，如果 DB 中有旧数据，也加入 updated 列表用于 Redis 缓存
                    if row.current_value:
                        updated.append(
                            {
                                "id": indicator_id,
                                "name": row.indicator_name or config.get("name", indicator_id),
                                "value": row.current_value,
                                "change": row.change_value or "+0.00%",
                                "change_percent": float(row.change_percent or 0.0),
                                "trend": row.trend or ("up" if (row.change_percent or 0.0) >= 0 else "down"),
                                "critical": bool(config.get("critical", row.is_critical)),
                                "symbol": row.symbol or config.get("symbol", indicator_id),
                                "type": row.indicator_type or config.get("type", "macro"),
                                "_stale": True,  # 标记为过期数据
                            }
                        )
                    continue

                # 使用 _safe_float 处理 NaN/Inf 值
                price = _safe_float(
                    result.get("price", result.get("regularMarketPrice", 0)),
                    default=0.0
                )

                change_percent = _safe_float(
                    result.get(
                        "change_percent",
                        result.get("regularMarketChangePercent", 0),
                    ),
                    default=0.0
                )

                change_sign = "+" if change_percent >= 0 else ""
                change_str = f"{change_sign}{change_percent:.2f}%"

                value_format = config.get("value_format")
                try:
                    current_value = (
                        value_format(price) if callable(value_format) else str(price)
                    )
                except Exception as e:
                    logger.debug(f"Failed to format value for {yf_symbol}: {e}")
                    current_value = str(price)

                row.indicator_name = config.get("name", row.indicator_name)
                row.symbol = config.get("symbol", row.symbol)
                row.indicator_type = config.get("type", row.indicator_type)
                row.is_critical = bool(config.get("critical", row.is_critical))
                row.current_value = current_value
                row.change_value = change_str
                row.change_percent = change_percent
                row.trend = "up" if change_percent >= 0 else "down"
                row.raw_data = _sanitize_for_json(result)
                row.fetch_error = None
                row.last_updated = now

                updated.append(
                    {
                        "id": indicator_id,
                        "name": config.get("name", indicator_id),
                        "value": current_value,
                        "change": change_str,
                        "change_percent": change_percent,
                        "trend": "up" if change_percent >= 0 else "down",
                        "critical": bool(config.get("critical", False)),
                        "symbol": config.get("symbol", indicator_id),
                        "type": config.get("type", "macro"),
                    }
                )

            await session.commit()

        # 写入 Redis（热缓存）
        # 即使部分/全部失败，也缓存成功的指标集合 + DB 中的旧数据
        if updated:
            # 使用较短的 TTL 如果是降级数据
            ttl = self._interval_seconds() if not fetch_failed_completely else min(self._interval_seconds(), 300)
            await self.redis.set(
                MACRO_REDIS_KEY,
                {
                    "indicators": updated, 
                    "last_updated": now.isoformat(),
                    "is_stale": fetch_failed_completely,
                },
                ttl=ttl,
            )

        if fetch_failed_completely:
            logger.warning(
                "Cockpit macro sync completed with DB fallback: cached=%s/%s (stale data)",
                len(updated), len(COCKPIT_MACRO_CONFIG)
            )
        else:
            logger.info(
                "Cockpit macro sync completed (batch): updated=%s/%s", 
                len(updated), len(COCKPIT_MACRO_CONFIG)
            )


    async def _refresh_redis_from_db(self) -> None:
        """从 DB 读取旧数据刷新 Redis 缓存
        
        当 YFinance 限流时调用，确保 Redis 缓存不会过期。
        """
        now = datetime.now()
        updated: List[Dict[str, Any]] = []

        async with get_db_session() as session:
            for code, config in COCKPIT_MACRO_CONFIG.items():
                indicator_id = config.get("id", code)

                row = (
                    await session.execute(
                        select(MacroIndicatorCache).where(
                            MacroIndicatorCache.indicator_id == indicator_id
                        )
                    )
                ).scalar_one_or_none()

                if row and row.current_value:
                    updated.append(
                        {
                            "id": indicator_id,
                            "name": row.indicator_name or config.get("name", indicator_id),
                            "value": row.current_value,
                            "change": row.change_value or "+0.00%",
                            "change_percent": float(row.change_percent or 0.0),
                            "trend": row.trend or ("up" if (row.change_percent or 0.0) >= 0 else "down"),
                            "critical": bool(config.get("critical", row.is_critical)),
                            "symbol": row.symbol or config.get("symbol", indicator_id),
                            "type": row.indicator_type or config.get("type", "macro"),
                            "_stale": True,
                        }
                    )

        if updated:
            # 使用较短的 TTL（最多 5 分钟），促使更快重试
            ttl = min(self._interval_seconds(), 300)
            await self.redis.set(
                MACRO_REDIS_KEY,
                {
                    "indicators": updated,
                    "last_updated": now.isoformat(),
                    "is_stale": True,
                },
                ttl=ttl,
            )
            logger.info(
                f"Refreshed Redis from DB cache: {len(updated)}/{len(COCKPIT_MACRO_CONFIG)} indicators (stale)"
            )
        else:
            logger.warning("No cached data in DB to refresh Redis")


_macro_sync_service: Optional[CockpitMacroSyncService] = None


def get_cockpit_macro_sync_service() -> CockpitMacroSyncService:
    global _macro_sync_service
    if _macro_sync_service is None:
        _macro_sync_service = CockpitMacroSyncService()
    return _macro_sync_service


async def start_cockpit_macro_sync_service() -> None:
    await get_cockpit_macro_sync_service().start()


async def stop_cockpit_macro_sync_service() -> None:
    await get_cockpit_macro_sync_service().stop()
