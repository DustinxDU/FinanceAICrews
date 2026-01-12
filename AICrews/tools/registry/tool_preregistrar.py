from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple
import threading


class ToolPreregistrar:
    """
    Pre-register tools by applying wrapping once and caching the wrapped result.

    This is an in-process optimization: for the same cache_key_prefix + tool name,
    the same wrapped tool instance is reused.
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str], Any] = {}
        self._lock = threading.Lock()

    def preregister(
        self,
        tools: List[Any],
        *,
        cache_key_prefix: str,
        wrap_tool: Callable[[Any], Any],
    ) -> List[Any]:
        wrapped_tools: List[Any] = []
        for tool in tools:
            tool_name = (
                getattr(tool, "name", None)
                or getattr(tool, "__name__", None)
                or str(tool)
            )
            key = (str(cache_key_prefix), str(tool_name))
            with self._lock:
                cached = self._cache.get(key)
                if cached is None:
                    cached = wrap_tool(tool)
                    self._cache[key] = cached
            wrapped_tools.append(cached)
        return wrapped_tools

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

