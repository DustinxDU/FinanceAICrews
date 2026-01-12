"""
LLM 模块

统一 LLM 管理 - 使用 unified_manager.py
系统 LLM 配置 - 使用 system_config.py (环境变量驱动，支持热更新)
辅助函数 - 使用 helpers.py (简化服务层调用)
"""

from .unified_manager import UnifiedLLMManager, get_unified_llm_manager
from .system_config import (
    SystemLLMConfig,
    SystemLLMConfigStore,
    get_system_llm_config_store,
    SYSTEM_SCOPES,
)
from .helpers import (
    get_system_llm,
    get_system_llm_or_none,
    is_system_llm_configured,
    get_system_llm_config,
)

__all__ = [
    'UnifiedLLMManager',
    'get_unified_llm_manager',
    'SystemLLMConfig',
    'SystemLLMConfigStore',
    'get_system_llm_config_store',
    'SYSTEM_SCOPES',
    # Helper functions
    'get_system_llm',
    'get_system_llm_or_none',
    'is_system_llm_configured',
    'get_system_llm_config',
]
