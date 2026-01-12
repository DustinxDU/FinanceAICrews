from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CacheItem:
    value: Any
    expires_at: Optional[float]


class LayeredCacheManager:
    """
    Layered cache manager (v2 plan).

    Task 1 implementation: memory layer only.
    Future tasks can extend this to Redis-backed layers.
    """

    def __init__(self, redis_manager: Any = None):
        self._redis = redis_manager
        self._memory: Dict[str, CacheItem] = {}

    def get(self, key: str, *, layer: str = "memory") -> Any:
        if layer != "memory":
            raise ValueError("Only memory layer is implemented")

        item = self._memory.get(key)
        if item is None:
            return None

        if item.expires_at is not None and time.time() > item.expires_at:
            self._memory.pop(key, None)
            return None

        return item.value

    def set(self, key: str, value: Any, *, ttl: int | float | None, layer: str = "memory") -> None:
        if layer != "memory":
            raise ValueError("Only memory layer is implemented")

        expires_at = None if ttl is None else (time.time() + float(ttl))
        self._memory[key] = CacheItem(value=value, expires_at=expires_at)

    def clear(self, *, layer: str = "memory") -> None:
        if layer != "memory":
            raise ValueError("Only memory layer is implemented for clear()")
        self._memory.clear()

    async def get_json(self, key: str, *, layer: str = "redis") -> Any:
        if layer == "memory":
            return self.get(key, layer="memory")
        if layer != "redis":
            raise ValueError(f"Unsupported cache layer: {layer}")
        if not self._redis:
            return None
        return await self._redis.get_json(key)

    async def set_json(
        self, key: str, value: Any, *, ttl: int, layer: str = "redis"
    ) -> bool:
        if layer == "memory":
            self.set(key, value, ttl=ttl, layer="memory")
            return True
        if layer != "redis":
            raise ValueError(f"Unsupported cache layer: {layer}")
        if not self._redis:
            return False
        return bool(await self._redis.set(key, value, ttl=ttl, json_encode=True))

    def get_json_sync(self, key: str, *, layer: str = "redis") -> Any:
        if layer == "memory":
            return self.get(key, layer="memory")
        if layer != "redis":
            raise ValueError(f"Unsupported cache layer: {layer}")
        if not self._redis:
            return None
        getter = getattr(self._redis, "get_json_sync", None)
        if callable(getter):
            return getter(key)
        return None

    def set_json_sync(
        self, key: str, value: Any, *, ttl: int, layer: str = "redis"
    ) -> bool:
        if layer == "memory":
            self.set(key, value, ttl=ttl, layer="memory")
            return True
        if layer != "redis":
            raise ValueError(f"Unsupported cache layer: {layer}")
        if not self._redis:
            return False
        setter = getattr(self._redis, "set_sync", None)
        if callable(setter):
            return bool(setter(key, value, ttl=ttl, json_encode=True))
        return False
