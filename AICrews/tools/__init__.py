"""
工具模块 (Tool Layer)

提供所有 Agent 可用的工具函数，支持 4 层架构

模块结构:
- market_data_tools.py: 市场数据工具 (yfinance)
- quant_tools.py: 本地技术分析 (pandas-ta)
- sentiment_tools.py: 情绪分析扩展
- expression_tools.py: 表达式引擎
- external_tools.py: 外部工具包

NOTE: MCP 工具现在通过 backend/app/tools/registry.py 动态加载
See: AICrews/core/mcp_config.py for CrewAI native MCP integration

使用方式:
1. 导入工具类: from AICrews.tools import MarketDataClient, QuantEngine
2. 使用 ToolRegistry 获取工具实例 (推荐)
"""

# 市场数据
from .market_data_tools import MarketDataClient
# 量化工具
from .quant_tools import QuantEngine
# 情绪工具
from .sentiment_tools import SentimentEngine
# 表达式工具
from .expression_tools import ExpressionEngine
# 外部工具函数（独立函数，不再使用 ExternalToolKit 类）
from .external_tools import web_search, duckduckgo_search, scrape_website

__all__ = [
    # 市场数据
    'MarketDataClient',

    # 量化工具
    'QuantEngine',

    # 情绪工具
    'SentimentEngine',

    # 表达式工具
    'ExpressionEngine',

    # 外部工具函数
    'web_search',
    'duckduckgo_search',
    'scrape_website',
]
