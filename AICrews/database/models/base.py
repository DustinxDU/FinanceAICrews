"""
Base Database Models - 基础数据库模型

包含 Base 类和枚举定义。
"""

from __future__ import annotations

from enum import Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


class SourceScope(str, Enum):
    """知识源作用域"""
    SYSTEM = "system"
    USER = "user"


class SourceTier(str, Enum):
    """知识源层级"""
    FREE = "free"
    PREMIUM = "premium"
    PRIVATE = "private"


__all__ = ["Base", "SourceScope", "SourceTier"]
