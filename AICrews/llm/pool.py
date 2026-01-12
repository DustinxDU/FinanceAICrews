from __future__ import annotations

import json
import threading
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional


class LLMInstancePool:
    """
    Simple in-process pool for reusing LLM instances.

    Keyed by a stable hash of a config dict.
    """

    def __init__(
        self,
        *,
        create_fn: Callable[[Dict[str, Any]], Any],
        maxsize: int = 128,
    ) -> None:
        self._create_fn = create_fn
        self._maxsize = int(maxsize)
        self._lock = threading.Lock()
        self._cache: "OrderedDict[str, Any]" = OrderedDict()

    def _make_key(self, config: Dict[str, Any]) -> str:
        payload = json.dumps(config, sort_keys=True, default=str, ensure_ascii=True)
        return payload

    def acquire(self, config: Dict[str, Any]) -> Any:
        key = self._make_key(config)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                return cached

        instance = self._create_fn(config)

        with self._lock:
            self._cache[key] = instance
            self._cache.move_to_end(key)
            if self._maxsize > 0 and len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)
        return instance

    def acquire_with_key(self, key_config: Dict[str, Any], *, create: Callable[[], Any]) -> Any:
        key = self._make_key(key_config)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                return cached

        instance = create()

        with self._lock:
            self._cache[key] = instance
            self._cache.move_to_end(key)
            if self._maxsize > 0 and len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)
        return instance

    def release(self, config: Dict[str, Any], instance: Any) -> None:
        # Currently a no-op; present for future ref-counting/health checks.
        return None

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
