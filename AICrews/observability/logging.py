"""
统一日志配置模块

提供全仓库唯一的日志初始化入口 `configure_logging(settings)`。
基于标准 Python logging，使用 dictConfig 配置，支持：
- stdout + file 双通道
- 按级别和模块分文件
- 轮转策略
- 环境变量驱动配置
- 上下文字段注入（job_id/run_id/user_id/ticker）
- 业务模块分类（LogModule）
"""

import logging
import logging.config
import os
import sys
import contextvars
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from AICrews.config.settings import get_settings, LoggingConfig


LOG_DIR_ENV = "FAIC_PATH_LOGS"
CONSOLE_LEVEL_ENV = "CONSOLE_LOG_LEVEL"
FILE_LEVEL_ENV = "FILE_LOG_LEVEL"
GLOBAL_LEVEL_ENV = "FAIC_INFRA_LOG_LEVEL"
LOGGING_ENABLED_ENV = "FAIC_LOGGING_ENABLED"
LOGGING_FORCE_ENV = "FAIC_LOGGING_FORCE_CONFIG"


# ==================== 业务模块常量 ====================

class LogModule:
    """日志模块分类常量

    用于标识不同业务模块的日志，便于过滤和分析。

    Usage:
        from AICrews.observability.logging import LogModule, get_module_logger

        logger = get_module_logger(LogModule.CREW)
        logger.info("Crew execution started")
    """
    TRADING = "trading"          # 交易执行模块
    RISK = "risk"                # 风控模块
    DATA = "data"                # 数据处理模块
    CREW = "crew"                # CrewAI多智能体模块
    DATABASE = "database"        # 数据库操作模块
    LLM = "llm"                  # LLM调用模块
    ANALYSIS = "analysis"        # 分析模块
    SYSTEM = "system"            # 系统级别
    PERFORMANCE = "performance"  # 性能监控
    MCP = "mcp"                  # MCP 服务模块
    SYNC = "sync"                # 数据同步模块
    OBSERVABILITY = "observability"  # 可观测性模块
    DEFAULT = "app"              # 默认模块


# 日志级别映射（用于配置）
LOG_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}


_context_vars = {
    "job_id": contextvars.ContextVar("job_id", default=None),
    "run_id": contextvars.ContextVar("run_id", default=None),
    "user_id": contextvars.ContextVar("user_id", default=None),
    "ticker": contextvars.ContextVar("ticker", default=None),
    "endpoint": contextvars.ContextVar("endpoint", default=None),
}


class ContextFilter(logging.Filter):
    """日志上下文过滤器，注入 job_id/run_id/user_id/ticker 等字段"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.job_id = _context_vars["job_id"].get() or "-"
        record.run_id = _context_vars["run_id"].get() or "-"
        record.user_id = _context_vars["user_id"].get() or "-"
        record.ticker = _context_vars["ticker"].get() or "-"
        record.endpoint = _context_vars["endpoint"].get() or "-"
        return True


def set_context(**kwargs) -> None:
    """设置日志上下文

    Args:
        job_id: 任务 ID
        run_id: 运行 ID
        user_id: 用户 ID
        ticker: 股票代码
        endpoint: API 端点
    """
    for key, value in kwargs.items():
        if key in _context_vars:
            _context_vars[key].set(value)


def clear_context() -> None:
    """清除日志上下文"""
    for var in _context_vars.values():
        var.set(None)


def get_context(key: str) -> Optional[Any]:
    """获取日志上下文值"""
    if key in _context_vars:
        return _context_vars[key].get()
    return None


class LogContext:
    """上下文管理器，用于临时设置日志上下文"""

    def __init__(self, **kwargs):
        self._tokens = {}
        self._kwargs = kwargs

    def __enter__(self):
        for key, value in self._kwargs.items():
            if key in _context_vars:
                self._tokens[key] = _context_vars[key].set(value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for key, token in self._tokens.items():
            _context_vars[key].reset(token)
        return False


def _get_log_dir() -> Path:
    """获取日志目录路径"""
    log_dir = os.getenv(LOG_DIR_ENV, "logs")
    return Path(log_dir).resolve()


def _ensure_log_dir(log_dir: Path) -> None:
    """确保日志目录存在"""
    log_dir.mkdir(parents=True, exist_ok=True)
    app_log_dir = log_dir / "app"
    app_log_dir.mkdir(parents=True, exist_ok=True)


def _get_level_from_env(env_name: str, default: str) -> str:
    """从环境变量获取日志级别"""
    return os.getenv(env_name, default).upper()


def _build_dict_config(config: LoggingConfig) -> Dict[str, Any]:
    """构建 logging.config.dictConfig 所需的配置字典"""
    log_dir = _get_log_dir()
    _ensure_log_dir(log_dir)

    console_level = _get_level_from_env(CONSOLE_LEVEL_ENV, config.console_level)
    file_level = _get_level_from_env(FILE_LEVEL_ENV, config.file_level)
    global_level = _get_level_from_env(GLOBAL_LEVEL_ENV, config.global_level)

    log_format = "%(asctime)s | %(name)s | [%(levelname)s] | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    dict_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context_filter": {
                "()": ContextFilter,
            },
        },
        "formatters": {
            "standard": {
                "format": log_format,
                "datefmt": date_format,
            },
            "console": {
                "format": "%(name)s - %(message)s",
                "datefmt": date_format,
            },
            "context_standard": {
                "format": "%(asctime)s | %(name)s | [%(levelname)s] | job_id=%(job_id)s | run_id=%(run_id)s | user_id=%(user_id)s | ticker=%(ticker)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s",
                "datefmt": date_format,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": console_level,
                "formatter": "console",
                "stream": "ext://sys.stdout",
                "filters": ["context_filter"],
            },
            "file_app": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": file_level,
                "formatter": "context_standard",
                "filename": str(log_dir / "app" / "app.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
                "filters": ["context_filter"],
            },
            "file_error": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": logging.ERROR,
                "formatter": "context_standard",
                "filename": str(log_dir / "app" / "error.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
                "filters": ["context_filter"],
            },
            "file_debug": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": logging.DEBUG,
                "formatter": "context_standard",
                "filename": str(log_dir / "app" / "debug.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
                "filters": ["context_filter"],
            },
        },
        "loggers": {
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "file_app", "file_error"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file_app"],
                "propagate": False,
            },
            "crewai": {
                "level": "DEBUG",
                "handlers": ["console", "file_app", "file_error", "file_debug"],
                "propagate": False,
            },
            "AICrews": {
                "level": global_level,
                "handlers": ["console", "file_app", "file_error", "file_debug"],
                "propagate": False,
            },
        },
        "root": {
            "level": global_level,
            "handlers": ["console", "file_app", "file_error"],
        },
    }

    for module, level in config.module_levels.items():
        module_level = os.getenv(f"FAIC_LOG_{module.upper()}", level)
        module_logger_key = f"AICrews.{module}"
        dict_config["loggers"][module_logger_key] = {
            "level": module_level,
            "handlers": ["console", "file_app", "file_error", "file_debug"],
            "propagate": False,
        }

    return dict_config


def configure_logging(
    settings: Optional[LoggingConfig] = None, force: bool = False
) -> None:
    """
    统一日志配置入口

    Args:
        settings: 配置对象，如果为 None 则从 settings.py 读取
        force: 是否强制重新配置（即使已有 handlers）
    """
    if settings is None:
        settings = get_settings().logging

    enabled = os.getenv(LOGGING_ENABLED_ENV, "true").lower() == "true"
    if not enabled:
        return

    force_config = os.getenv(LOGGING_FORCE_ENV, "true").lower() == "true"
    if force:
        force_config = True

    if logging.getLogger().handlers and not force_config:
        return

    dict_config = _build_dict_config(settings)

    try:
        logging.config.dictConfig(dict_config)
    except Exception as e:
        sys.stderr.write(f"Failed to configure logging: {e}\n")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


def get_logger(name: str) -> logging.Logger:
    """
    便捷函数：获取标准 Logger

    与 AGENTS.md 规范对齐，返回标准 logging.Logger
    与 AICrews/utils/logger.py 的 get_logger 函数兼容

    Args:
        name: logger 名称，通常使用 __name__

    Returns:
        标准 Logger 实例
    """
    return logging.getLogger(name)


def get_module_logger(
    module: str,
    level: Optional[str] = None,
    base_name: str = "AICrews"
) -> logging.Logger:
    """
    获取指定业务模块的 Logger

    这是推荐的获取 Logger 的方式，用于替代 utils/logger.py 中的同名函数。
    返回的 Logger 名称格式为 "{base_name}.{module}"，例如 "AICrews.crew"。

    Args:
        module: 业务模块名称，建议使用 LogModule 常量
        level: 可选的日志级别 ('DEBUG'/'INFO'/'WARNING'/'ERROR'/'CRITICAL')
        base_name: Logger 基础名称，默认 "AICrews"

    Returns:
        配置好的 Logger 实例

    Examples:
        >>> from AICrews.observability.logging import LogModule, get_module_logger
        >>>
        >>> # 使用 LogModule 常量
        >>> crew_logger = get_module_logger(LogModule.CREW)
        >>> crew_logger.info("Crew execution started")
        >>>
        >>> # 使用字符串
        >>> llm_logger = get_module_logger("llm", level="DEBUG")
        >>> llm_logger.debug("LLM call details...")
    """
    logger_name = f"{base_name}.{module}"
    logger = logging.getLogger(logger_name)

    # 如果指定了级别，设置 logger 级别
    if level:
        log_level = LOG_LEVEL_MAP.get(level.upper(), logging.INFO)
        logger.setLevel(log_level)

    return logger


def reset_logging() -> None:
    """重置日志配置（用于测试）"""
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    root.setLevel(logging.NOTSET)


LOG_RETENTION_POLICY = """
日志留存与清理策略

默认配置：
- app.log: 10MB * 5 = 50MB 滚动备份
- error.log: 10MB * 5 = 50MB 滚动备份
- debug.log: 10MB * 3 = 30MB 滚动备份

生产环境建议使用 logrotate：
```
/path/to/logs/app/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
    postrotate
        kill -HUP $(cat /var/run/uvicorn.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
```

或者通过环境变量配置更大的滚动策略：
- FAIC_LOG_MAX_BYTES: 单个日志文件最大字节数（默认 10MB）
- FAIC_LOG_BACKUP_COUNT: 滚动备份数量（默认 5）
"""
