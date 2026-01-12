"""
Infrastructure Layer

封装外部 IO 与适配器（缓存、向量存储等）。
"""

from .cache.redis_manager import RedisManager
from .vectorstores.postgres import (
    PostgresVectorStore,
    LegacyLessonVectorStore,
    UnifiedVectorStore,
    SearchResult,
)

__all__ = [
    "RedisManager",
    "PostgresVectorStore",
    "LegacyLessonVectorStore",
    "UnifiedVectorStore",
    "SearchResult",
]
