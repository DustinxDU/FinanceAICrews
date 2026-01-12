"""
Singleton metaclass for ensuring single instance of classes.

Usage:
    class MyService(metaclass=SingletonMeta):
        pass
"""
from typing import Any, Dict
import threading

from AICrews.observability.logging import get_logger

logger = get_logger(__name__)


class SingletonMeta(type):
    """
    Thread-safe Singleton metaclass.

    Ensures only one instance of a class exists across the application.
    Supports reset for testing purposes.

    Example:
        class DatabaseConnection(metaclass=SingletonMeta):
            def __init__(self, url: str):
                self.url = url

        # First call creates instance
        db1 = DatabaseConnection("postgres://...")
        # Second call returns same instance (ignores new args)
        db2 = DatabaseConnection("mysql://...")
        assert db1 is db2
    """

    _instances: Dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs) -> Any:
        """Create or return existing instance."""
        if cls not in cls._instances:
            with cls._lock:
                # Double-check locking pattern
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
                    logger.debug(f"Created singleton instance of {cls.__name__}")
        return cls._instances[cls]

    @classmethod
    def reset(mcs, cls: type = None) -> None:
        """
        Reset singleton instance(s) for testing.

        Args:
            cls: Specific class to reset, or None to reset all.
        """
        with mcs._lock:
            if cls is not None:
                if cls in mcs._instances:
                    del mcs._instances[cls]
                    logger.debug(f"Reset singleton instance of {cls.__name__}")
            else:
                mcs._instances.clear()
                logger.debug("Reset all singleton instances")


__all__ = ["SingletonMeta"]
