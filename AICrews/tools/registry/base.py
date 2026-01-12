"""
Base Tool - 工具基础类

定义工具的基础接口和枚举类型。
"""

from __future__ import annotations

from typing import Optional, Callable, Any
from enum import Enum


class ToolSource(str, Enum):
    """工具来源枚举"""
    
    # 内置工具 (crewai-tools 等)
    BUILTIN = "builtin"
    
    # MCP 服务器提供的工具
    MCP = "mcp"
    
    # 自定义函数工具
    CUSTOM = "custom"
    
    # Python 工具
    PYTHON = "python"
    
    # 文件工具
    FILE = "file"
    
    # 网络工具
    WEB = "web"
    
    # 其他
    OTHER = "other"


class ToolTier(str, Enum):
    """工具层级枚举
    
    按照 MIGRATION_TODO.md 中的 4-Tier Loadout 配置：
    - Tier 1: Builtin Tools - 内置基础工具
    - Tier 2: Data Connectors - 数据连接器 (MCP)
    - Tier 3: Knowledge RAG - 知识检索
    - Tier 4: Agent Actions - Agent 特定工具
    """
    
    # Tier 1: 内置工具 (crewai-tools 内置等)
    TIER_1_BUILTIN = "tier_1_builtin"
    
    # Tier 2: 数据连接器 (MCP Servers)
    TIER_2_DATA = "tier_2_data"
    
    # Tier 3: 知识检索 (Vector DB)
    TIER_3_KNOWLEDGE = "tier_3_knowledge"
    
    # Tier 4: Agent 特定工具
    TIER_4_AGENT = "tier_4_agent"
    
    @classmethod
    def from_str(cls, value: str) -> ToolTier:
        """从字符串转换为枚举
        
        Args:
            value: 字符串值
            
        Returns:
            ToolTier 枚举值
        """
        value_map = {
            "builtin": cls.TIER_1_BUILTIN,
            "data": cls.TIER_2_DATA,
            "knowledge": cls.TIER_3_KNOWLEDGE,
            "agent": cls.TIER_4_AGENT,
        }
        return value_map.get(value.lower(), cls.TIER_1_BUILTIN)


class BaseTool:
    """工具基类
    
    所有工具类都应该继承此基类，或者实现相同的接口。
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        source: ToolSource = ToolSource.BUILTIN,
        tier: ToolTier = ToolTier.TIER_1_BUILTIN,
        category: str = "general",
        icon: Optional[str] = None,
        is_active: bool = True,
        requires_api_key: bool = False,
        api_key_provider: Optional[str] = None,
        config_schema: Optional[dict] = None
    ):
        """初始化工具
        
        Args:
            name: 工具名称 (唯一标识)
            description: 工具描述
            source: 工具来源
            tier: 工具层级
            category: 工具分类
            icon: 工具图标
            is_active: 是否激活
            requires_api_key: 是否需要 API Key
            api_key_provider: API Key 提供商
            config_schema: 配置 schema
        """
        self.name = name
        self.description = description
        self.source = source
        self.tier = tier
        self.category = category
        self.icon = icon
        self.is_active = is_active
        self.requires_api_key = requires_api_key
        self.api_key_provider = api_key_provider
        self.config_schema = config_schema or {}
    
    def to_dict(self) -> dict:
        """转换为字典
        
        Returns:
            工具信息的字典表示
        """
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source.value,
            "tier": self.tier.value,
            "category": self.category,
            "icon": self.icon,
            "is_active": self.is_active,
            "requires_api_key": self.requires_api_key,
            "api_key_provider": self.api_key_provider,
            "config_schema": self.config_schema,
        }
    
    def execute(self, *args, **kwargs) -> Any:
        """执行工具
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            执行结果
            
        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("Tool must implement execute method")


__all__ = ["BaseTool", "ToolSource", "ToolTier"]
