"""
Provider rate limiting / backoff helpers.

Phase 4 goal:
- 统一限制外部 provider（yfinance/akshare/openbb/MCP）的请求速率与并发
- 降低触发 429/封禁的概率，并在压力下优雅退避

Design:
- 并发：进程内 asyncio.Semaphore
  - 优点：简单，保护本进程不把 provider 打爆
- 速率：优先使用 Redis 计数（跨进程/多实例共享），无 Redis 时回退到进程内计数
  - 计数窗口：固定窗口（default 60s），通过 env 可配置

Note:
- 这是“守门员”，不是重试器：网络/服务端错误由调用方按业务处理。
"""

from __future__ import annotations

import asyncio
from AICrews.observability.logging import get_logger
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

from AICrews.infrastructure.cache.redis_manager import get_redis_manager

logger = get_logger(__name__)


@dataclass
class ProviderLimitConfig:
    provider: str
    max_concurrency: int
    max_requests_per_window: int
    window_seconds: int


class ProviderRateLimiter:
    def __init__(self):
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._local_windows: Dict[str, Dict[int, int]] = {}

    def _cfg(self, provider: str) -> ProviderLimitConfig:
        p = provider.upper()
        max_concurrency = int(os.getenv(f"FAIC_PROVIDER_{p}_MAX_CONCURRENCY", "5"))
        window_seconds = int(os.getenv(f"FAIC_PROVIDER_{p}_WINDOW_SECONDS", "60"))
        max_requests_per_window = int(os.getenv(f"FAIC_PROVIDER_{p}_MAX_REQUESTS_PER_WINDOW", "120"))
        return ProviderLimitConfig(
            provider=provider,
            max_concurrency=max_concurrency,
            max_requests_per_window=max_requests_per_window,
            window_seconds=window_seconds,
        )

    def _sem(self, provider: str) -> asyncio.Semaphore:
        if provider not in self._semaphores:
            self._semaphores[provider] = asyncio.Semaphore(self._cfg(provider).max_concurrency)
        return self._semaphores[provider]

    async def acquire(self, provider: str, cost: int = 1) -> None:
        cfg = self._cfg(provider)
        sem = self._sem(provider)
        await sem.acquire()

        try:
            await self._acquire_rate(cfg, cost=cost)
        except Exception:
            sem.release()
            raise

    def release(self, provider: str) -> None:
        sem = self._sem(provider)
        sem.release()

    async def _acquire_rate(self, cfg: ProviderLimitConfig, cost: int) -> None:
        window = int(time.time() // cfg.window_seconds)
        redis = get_redis_manager()

        # Prefer Redis-based counter (cross-process). If Redis not ready, fallback to local.
        key = f"rl:{cfg.provider}:{window}"

        if getattr(redis, "_client", None) is not None:
            while True:
                current = await redis.incr(key, amount=cost, ttl=cfg.window_seconds + 1)
                if current <= cfg.max_requests_per_window:
                    return

                # exceeded: sleep until next window
                now = time.time()
                next_window_at = (window + 1) * cfg.window_seconds
                sleep_s = max(0.05, next_window_at - now)
                logger.warning(
                    "Provider rate limited (redis): provider=%s limit=%s/%ss current=%s sleep=%.2fs",
                    cfg.provider,
                    cfg.max_requests_per_window,
                    cfg.window_seconds,
                    current,
                    sleep_s,
                )
                await asyncio.sleep(sleep_s)
                window = int(time.time() // cfg.window_seconds)
                key = f"rl:{cfg.provider}:{window}"

        # Local fallback (single-process only)
        win_counts = self._local_windows.setdefault(cfg.provider, {})
        while True:
            count = win_counts.get(window, 0) + cost
            if count <= cfg.max_requests_per_window:
                win_counts[window] = count
                # best-effort cleanup older windows
                for old in list(win_counts.keys()):
                    if old < window - 3:
                        win_counts.pop(old, None)
                return

            now = time.time()
            next_window_at = (window + 1) * cfg.window_seconds
            sleep_s = max(0.05, next_window_at - now)
            logger.warning(
                "Provider rate limited (local): provider=%s limit=%s/%ss current=%s sleep=%.2fs",
                cfg.provider,
                cfg.max_requests_per_window,
                cfg.window_seconds,
                count,
                sleep_s,
            )
            await asyncio.sleep(sleep_s)
            window = int(time.time() // cfg.window_seconds)

    def get_stats(self) -> Dict[str, object]:
        out: Dict[str, object] = {}
        for provider, sem in self._semaphores.items():
            # Semaphore doesn't expose current count directly; we expose configured + best-effort available.
            cfg = self._cfg(provider)
            out[provider] = {
                "max_concurrency": cfg.max_concurrency,
                "window_seconds": cfg.window_seconds,
                "max_requests_per_window": cfg.max_requests_per_window,
            }
        return out


_provider_limiter: Optional[ProviderRateLimiter] = None


def get_provider_limiter() -> ProviderRateLimiter:
    global _provider_limiter
    if _provider_limiter is None:
        _provider_limiter = ProviderRateLimiter()
    return _provider_limiter

