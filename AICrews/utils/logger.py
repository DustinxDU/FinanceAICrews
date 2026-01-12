"""
兼容层 - 重新导出 AICrews.observability.logging 的内容

⚠️ 此模块已弃用，请直接使用 AICrews.observability.logging
"""

import warnings

warnings.warn(
    "AICrews.utils.logger is deprecated. Use AICrews.observability.logging instead.",
    DeprecationWarning,
    stacklevel=2
)

from AICrews.observability.logging import (
    LogModule,
    LogContext,
    ContextFilter,
    set_context,
    clear_context,
    get_context,
    configure_logging,
    get_logger,
    get_module_logger,
    reset_logging,
)

# 为了向后兼容，创建一个默认 logger
logger = get_logger(__name__)

__all__ = [
    "LogModule",
    "LogContext",
    "ContextFilter",
    "set_context",
    "clear_context",
    "get_context",
    "configure_logging",
    "get_logger",
    "get_module_logger",
    "reset_logging",
    "logger",
]
