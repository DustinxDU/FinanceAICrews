"""
FinanceAICrews 核心包

一个基于 CrewAI 的多智能体金融分析系统
支持配置驱动的 4 层架构

Architecture:
1. Config Layer - YAML 配置 (agents.yaml, tasks.yaml, crews/*.yaml)
2. Core Layer - 工厂模式、工具注册表、MCP 管理器
3. Tool Layer - 本地工具 + MCP 工具
4. Data Layer - PostgreSQL + pgvector
"""

__version__ = "0.3.0"
__author__ = "FinanceAICrews Team"

# 配置模块 (无第三方依赖，可直接导入)
from AICrews.config import get_settings, set_settings, Settings
from AICrews.config.settings import get_config, set_config, DEFAULT_CONFIG

# 以下模块使用延迟导入，避免在没有安装依赖时报错

def __getattr__(name):
    """延迟导入：只有在访问时才加载模块"""
    # Services
    if name == "AnalysisService":
        from AICrews.services import AnalysisService
        return AnalysisService

    # New 4-Layer Architecture
    elif name == "CrewFactory":
        from AICrews.core import CrewFactory
        return CrewFactory
    elif name == "get_crew_factory":
        from AICrews.core import get_crew_factory
        return get_crew_factory
    elif name == "CrewRunner":
        from AICrews.runner import CrewRunner
        return CrewRunner
    elif name == "run_analysis":
        from AICrews.runner import run_analysis
        return run_analysis
    elif name == "list_available_crews":
        from AICrews.runner import list_available_crews
        return list_available_crews
    
    raise AttributeError(f"module 'AICrews' has no attribute '{name}'")

__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    
    # 配置
    'get_settings',
    'set_settings',
    'Settings',
    'DEFAULT_CONFIG',
    'get_config',
    'set_config',
    
    # New: 4-Layer Architecture
    'CrewFactory',
    'get_crew_factory',
    
    # New: Simplified Runner
    'CrewRunner',
    'run_analysis',
    'list_available_crews',
]
