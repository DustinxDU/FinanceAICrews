from __future__ import annotations

import asyncio
from AICrews.observability.logging import get_logger
import time
from typing import Any, Awaitable, Callable, Optional, TypeVar

from AICrews.schemas.error_handling import ErrorConfig, ErrorStrategy

logger = get_logger(__name__)

T = TypeVar("T")


class ErrorHandler:
    def run_with_policy(self, fn: Callable[[], T], config: ErrorConfig) -> Optional[T]:
        strategy = config.strategy

        if strategy == ErrorStrategy.RETRY:
            last_err: Optional[BaseException] = None
            for attempt in range(config.max_retries + 1):
                try:
                    return fn()
                except Exception as e:
                    last_err = e
                    logger.warning(
                        "Execution failed (retry): attempt=%s/%s err=%s",
                        attempt + 1,
                        config.max_retries + 1,
                        e,
                        exc_info=True,
                    )
                    if attempt >= config.max_retries:
                        break
                    if config.retry_delay:
                        time.sleep(config.retry_delay)
            raise last_err  # type: ignore[misc]

        if strategy == ErrorStrategy.ERROR_OUTPUT:
            try:
                return fn()
            except Exception as e:
                logger.warning("Execution failed (error_output): err=%s", e, exc_info=True)
                return config.error_output  # type: ignore[return-value]

        if strategy == ErrorStrategy.CONTINUE:
            try:
                return fn()
            except Exception as e:
                logger.warning("Execution failed (continue): err=%s", e, exc_info=True)
                return None

        # STOP/FALLBACK default: raise on error (fallback chain handled elsewhere)
        return fn()

    async def arun_with_policy(
        self, fn: Callable[[], Awaitable[T]], config: ErrorConfig
    ) -> Optional[T]:
        strategy = config.strategy

        if strategy == ErrorStrategy.RETRY:
            last_err: Optional[BaseException] = None
            for attempt in range(config.max_retries + 1):
                try:
                    return await fn()
                except Exception as e:
                    last_err = e
                    logger.warning(
                        "Async execution failed (retry): attempt=%s/%s err=%s",
                        attempt + 1,
                        config.max_retries + 1,
                        e,
                        exc_info=True,
                    )
                    if attempt >= config.max_retries:
                        break
                    if config.retry_delay:
                        await asyncio.sleep(config.retry_delay)
            raise last_err  # type: ignore[misc]

        if strategy == ErrorStrategy.ERROR_OUTPUT:
            try:
                return await fn()
            except Exception as e:
                logger.warning("Async execution failed (error_output): err=%s", e, exc_info=True)
                return config.error_output  # type: ignore[return-value]

        if strategy == ErrorStrategy.CONTINUE:
            try:
                return await fn()
            except Exception as e:
                logger.warning("Async execution failed (continue): err=%s", e, exc_info=True)
                return None

        return await fn()


__all__ = ["ErrorHandler", "ErrorConfig", "ErrorStrategy"]

