"""
统一配置管理

整合原 default_config.py 和 dataflows/config.py
提供类型安全的配置访问和环境变量支持
标准化命名规范：FAIC_{MODULE}_{KEY}
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field

# 优雅处理 dotenv 缺失的情况
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv 未安装，跳过加载 .env 文件
    pass


@dataclass
class LoggingConfig:
    """日志配置"""
    global_level: str = "INFO"
    console_level: str = "INFO"
    file_level: str = "DEBUG"
    log_dir: str = "logs"
    enable_level_split: bool = True
    
    # 模块级别配置
    module_levels: Dict[str, str] = field(default_factory=lambda: {
        "trading": "INFO",
        "risk": "WARNING",
        "data": "INFO",
        "crew": "INFO",
        "database": "WARNING",
        "llm": "INFO",
        "analysis": "INFO",
        "performance": "DEBUG",
    })
    
    # 日志格式
    console_format: str = "%(name)s - %(message)s"
    file_format: str = "%(asctime)s | %(name)s | [%(levelname)s] | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "volcengine"
    # 模型名称不再硬编码，从环境变量或 CLI 选择获取
    default_model: str = ""
    backend_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    
    # Embedding 配置
    embedding_backend_url: str = "http://localhost:11434/v1"
    embedding_api_key: str = "ollama"


@dataclass
class DataConfig:
    """数据源配置"""
    # 分类级别默认供应商
    core_stock_apis: str = "yfinance"
    technical_indicators: str = "yfinance"
    fundamental_data: str = "yfinance"
    news_data: str = "yfinance"
    
    # 工具级别覆盖（多级降级策略）
    tool_vendors: Dict[str, str] = field(default_factory=lambda: {
        "get_global_news": "yfinance",
        "get_news": "yfinance",
        "get_fundamentals": "yfinance",
    })
    
    # 性能优化：早停策略
    max_successful_vendors: int = 2


@dataclass
class DebateConfig:
    """辩论配置"""
    max_debate_rounds: int = 1
    max_risk_discuss_rounds: int = 1
    max_recur_limit: int = 100


@dataclass
class MCPConfig:
    """MCP 配置"""
    # 功能开关
    enabled: bool = False  # 是否启用 MCP（用于渐进式迁移）
    use_mcp_for_agents: bool = False  # Agent 是否使用 MCP
    agent_tool_filters: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class TrackingConfig:
    """事件追踪配置

    控制 CrewAI EventBus 和 litellm 回调的事件追踪级别。

    Levels:
    - "full": 追踪所有事件（开发环境）
        - Tool: Started + Finished + Error
        - LLM: PreCall + Success + Failure
    - "minimal": 只追踪完成/错误事件（生产环境）
        - Tool: Finished + Error
        - LLM: Success + Failure
    """
    event_tracking_level: str = "minimal"  # "full" or "minimal"


@dataclass
class SyncConfig:
    """数据同步配置

    控制 unified_sync_service 的同步行为参数。
    所有参数支持通过 FAIC_SYNC_* 环境变量覆盖。
    
    v2.0 更新：将默认同步间隔从 60 秒增加到 300 秒（5分钟），
    避免触发 YFinance API 速率限制（尤其是订阅大量资产时）。
    """
    default_interval: int = 300     # 默认同步间隔（秒）- v2.0: 从60改为300
    base_interval: int = 300        # 基础同步间隔（秒）- v2.0: 从60改为300
    max_interval: int = 1800        # 最大同步间隔（秒）- v2.0: 从600改为1800（30分钟）
    max_errors: int = 5             # 最大连续错误次数 - v2.0: 从3改为5（更宽容）
    retry_delay: int = 10           # 重试延迟（秒）- v2.0: 从5改为10

    def __post_init__(self):
        # 从环境变量覆盖
        self.default_interval = int(os.getenv("FAIC_SYNC_DEFAULT_INTERVAL", str(self.default_interval)))
        self.base_interval = int(os.getenv("FAIC_SYNC_BASE_INTERVAL", str(self.base_interval)))
        self.max_interval = int(os.getenv("FAIC_SYNC_MAX_INTERVAL", str(self.max_interval)))
        self.max_errors = int(os.getenv("FAIC_SYNC_MAX_ERRORS", str(self.max_errors)))
        self.retry_delay = int(os.getenv("FAIC_SYNC_RETRY_DELAY", str(self.retry_delay)))



@dataclass
class Settings:
    """
    统一配置类
    
    使用 dataclass 提供类型安全的配置访问
    支持从环境变量和配置文件加载
    """
    # 路径配置
    project_dir: str = field(default_factory=lambda: os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    ))
    results_dir: str = field(default_factory=lambda: os.getenv(
        "FAIC_APP_RESULTS_DIR", os.getenv("FINANCEAICREWS_RESULTS_DIR", "./results")
    ))
    data_cache_dir: str = ""
    
    # 子配置
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    data: DataConfig = field(default_factory=DataConfig)
    debate: DebateConfig = field(default_factory=DebateConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)

    def __post_init__(self):
        # 路径配置
        if not self.data_cache_dir:
            self.data_cache_dir = os.getenv(
                "FAIC_APP_DATA_CACHE_DIR", 
                os.path.join(self.project_dir, ".cache/data_cache")
            )
            
        # 从环境变量覆盖日志配置
        self.logging.global_level = os.getenv("FAIC_INFRA_LOG_LEVEL", os.getenv("LOG_LEVEL", self.logging.global_level))
        self.logging.console_level = os.getenv("CONSOLE_LOG_LEVEL", self.logging.console_level)
        self.logging.file_level = os.getenv("FILE_LOG_LEVEL", self.logging.file_level)
        self.logging.log_dir = os.getenv("FAIC_PATH_LOGS", self.logging.log_dir)
        
        # 从环境变量覆盖 MCP 配置
        self.mcp.enabled = os.getenv("FAIC_MCP_ENABLED", os.getenv("MCP_ENABLED", "false")).lower() == "true"
        self.mcp.use_mcp_for_agents = os.getenv("FAIC_MCP_USE_FOR_AGENTS", os.getenv("MCP_USE_FOR_AGENTS", "false")).lower() == "true"

        # 从环境变量覆盖 Tracking 配置
        event_level = os.getenv("FAIC_EVENT_TRACKING_LEVEL")
        if event_level and event_level.lower() in ("full", "minimal"):
            self.tracking.event_tracking_level = event_level.lower()

        # 模块级日志级别
        module_env_map = {
            "trading": "TRADING_LOG_LEVEL",
            "risk": "RISK_LOG_LEVEL",
            "data": "DATA_LOG_LEVEL",
            "crew": "CREW_LOG_LEVEL",
            "database": "DATABASE_LOG_LEVEL",
            "llm": "LLM_LOG_LEVEL",
            "analysis": "ANALYSIS_LOG_LEVEL",
            "performance": "PERF_LOG_LEVEL",
        }
        for module, env_name in module_env_map.items():
            level = os.getenv(f"FAIC_LOG_{module.upper()}", os.getenv(env_name))
            if level:
                self.logging.module_levels[module] = level.upper()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（兼容旧代码）"""
        return {
            "project_dir": self.project_dir,
            "results_dir": self.results_dir,
            "data_cache_dir": self.data_cache_dir,
            
            # LLM 配置（扁平化）
            "llm_provider": self.llm.provider,
            "default_llm": self.llm.default_model,
            "backend_url": self.llm.backend_url,
            "embedding_backend_url": self.llm.embedding_backend_url,
            "embedding_api_key": self.llm.embedding_api_key,
            
            # 辩论配置
            "max_debate_rounds": self.debate.max_debate_rounds,
            "max_risk_discuss_rounds": self.debate.max_risk_discuss_rounds,
            "max_recur_limit": self.debate.max_recur_limit,
            
            # 数据供应商配置
            "data_vendors": {
                "core_stock_apis": self.data.core_stock_apis,
                "technical_indicators": self.data.technical_indicators,
                "fundamental_data": self.data.fundamental_data,
                "news_data": self.data.news_data,
            },
            "tool_vendors": self.data.tool_vendors,
            "max_successful_vendors": self.data.max_successful_vendors,
            
            # 日志配置
            "logging": {
                "global_level": self.logging.global_level,
                "console_level": self.logging.console_level,
                "file_level": self.logging.file_level,
                "module_levels": self.logging.module_levels,
                "log_dir": self.logging.log_dir,
                "enable_level_split": self.logging.enable_level_split,
                "format": {
                    "console": self.logging.console_format,
                    "file": self.logging.file_format,
                    "datetime": self.logging.datetime_format,
                },
            },
            
            # MCP 配置
            "mcp": {
                "enabled": self.mcp.enabled,
                "use_mcp_for_agents": self.mcp.use_mcp_for_agents,
                "agent_tool_filters": self.mcp.agent_tool_filters,
            },

            # Tracking 配置
            "tracking": {
                "event_tracking_level": self.tracking.event_tracking_level,
            },

            # Sync 配置
            "sync": {
                "default_interval": self.sync.default_interval,
                "base_interval": self.sync.base_interval,
                "max_interval": self.sync.max_interval,
                "max_errors": self.sync.max_errors,
                "retry_delay": self.sync.retry_delay,
            },
        }
    
    def update(self, updates: Dict[str, Any]) -> None:
        """更新配置（兼容旧代码）"""
        for key, value in updates.items():
            if key == "llm_provider":
                self.llm.provider = value
            elif key == "default_llm":
                self.llm.default_model = value
            elif key == "backend_url":
                self.llm.backend_url = value
            elif key == "max_debate_rounds":
                self.debate.max_debate_rounds = value


# 全局设置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def set_settings(settings: Settings) -> None:
    """设置全局配置实例"""
    global _settings
    _settings = settings


# ============================================================
# 兼容层：保持与旧 default_config.py 和 dataflows/config.py 的兼容
# ============================================================

def get_config() -> Dict[str, Any]:
    """兼容旧的 get_config() 调用"""
    return get_settings().to_dict()


def set_config(config: Dict[str, Any]) -> None:
    """兼容旧的 set_config() 调用"""
    settings = get_settings()
    settings.update(config)


# 导出兼容的 DEFAULT_CONFIG
DEFAULT_CONFIG = get_settings().to_dict()
