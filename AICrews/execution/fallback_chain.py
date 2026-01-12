from __future__ import annotations

import asyncio
import inspect
from AICrews.observability.logging import get_logger
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, List, Optional

logger = get_logger(__name__)


@dataclass
class FallbackStats:
    total: int = 0
    success: int = 0
    fail: int = 0
    fallback_used: int = 0


class FallbackChain:
    def __init__(self, steps: List[Callable[[], Any]]):
        self._steps = list(steps)
        self._stats = FallbackStats()

    @property
    def stats(self) -> FallbackStats:
        return self._stats

    def run(self) -> Any:
        self._stats.total += 1
        last_err: Optional[BaseException] = None

        for idx, step in enumerate(self._steps):
            try:
                result = step()
                if result is not None:
                    self._stats.success += 1
                    if idx > 0:
                        self._stats.fallback_used += 1
                    return result
            except Exception as e:
                last_err = e
                self._stats.fail += 1
                logger.warning("Fallback step failed: idx=%s err=%s", idx, e, exc_info=True)
                continue

        if last_err:
            logger.error("All fallback steps failed: err=%s", last_err, exc_info=True)
        return None

    async def arun(self) -> Any:
        self._stats.total += 1
        last_err: Optional[BaseException] = None

        for idx, step in enumerate(self._steps):
            try:
                result = step()
                if inspect.isawaitable(result):
                    result = await result
                if result is not None:
                    self._stats.success += 1
                    if idx > 0:
                        self._stats.fallback_used += 1
                    return result
            except Exception as e:
                last_err = e
                self._stats.fail += 1
                logger.warning(
                    "Async fallback step failed: idx=%s err=%s", idx, e, exc_info=True
                )
                continue

        if last_err:
            logger.error("All async fallback steps failed: err=%s", last_err, exc_info=True)
        return None


__all__ = ["FallbackChain", "FallbackStats"]

