"""
MCP Integration Examples

Examples of how to use the MCP integration in different agent types.
"""

import asyncio
import logging
from AICrews.tools.mcp._infra.interface import MCPInterface
from AICrews.tools.mcp._infra.tool_registry import AgentType

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def market_analyzer_example():
    """市场分析师 Agent 使用示例"""
    print("\n=== 市场分析师示例 ===")
    
    # 创建 MCP 接口
    mcp_interface = MCPInterface(AgentType.MARKET_ANALYZER)
    await mcp_interface.initialize()
    
    try:
        # 获取股票价格（自动选择最优数据源）
        response = await mcp_interface.get_stock_price("AAPL")
        if response.success:
            print(f"获取 AAPL 价格成功，数据源: {response.source.value}")
            print(f"数据: {response.data}")
        else:
            print(f"获取失败: {response.error}")
        
        # 获取相关新闻
        response = await mcp_interface.get_news(tickers=["AAPL", "MSFT"])
        if response.success:
            print(f"\n获取新闻成功，数据源: {response.source.value}")
            print(f"新闻数量: {len(response.data) if isinstance(response.data, list) else 0}")
        
        # 查看可用工具
        tools = mcp_interface.get_available_tools()
        print(f"\n可用工具数量: {len(tools['tools'])}")
        for tool in tools['tools'][:3]:  # 显示前3个
            print(f"- {tool['name']}: {tool['description']}")
    
    finally:
        await mcp_interface.close()


async def fundamental_analyst_example():
    """基本面分析师 Agent 使用示例"""
    print("\n=== 基本面分析师示例 ===")
    
    mcp_interface = MCPInterface(AgentType.FUNDAMENTAL_ANALYST)
    await mcp_interface.initialize()
    
    try:
        # 获取基本面数据
        response = await mcp_interface.get_fundamentals("AAPL")
        if response.success:
            print(f"获取 AAPL 基本面数据成功，数据源: {response.source.value}")
            print(f"数据类型: {type(response.data)}")
        
        # 搜索股票
        response = await mcp_interface.search_symbols("Tesla")
        if response.success:
            print(f"\n搜索结果，数据源: {response.source.value}")
            print(f"找到 {len(response.data) if isinstance(response.data, list) else 0} 个结果")
    
    finally:
        await mcp_interface.close()


async def chinese_market_example():
    """中国市场数据示例（使用 Akshare）"""
    print("\n=== 中国市场数据示例 ===")
    
    mcp_interface = MCPInterface(AgentType.MARKET_ANALYZER)
    await mcp_interface.initialize()
    
    try:
        # 获取中国股票价格（自动使用 Akshare）
        response = await mcp_interface.get_stock_price("000001")
        if response.success:
            print(f"获取平安银行价格成功，数据源: {response.source.value}")
            print(f"数据: {response.data}")
        
        # 获取中国宏观经济数据
        response = await mcp_interface.get_economic_data("GDP", country="CN")
        if response.success:
            print(f"\n获取中国GDP数据成功，数据源: {response.source.value}")
    
    finally:
        await mcp_interface.close()


async def fallback_strategy_example():
    """降级策略示例"""
    print("\n=== 降级策略示例 ===")
    
    mcp_interface = await create_mcp_interface(AgentType.MARKET_ANALYZER)
    
    try:
        # 尝试获取数据，如果 MCP 不可用会自动降级到 legacy
        response = await mcp_interface.get_stock_price("TSLA")
        print(f"获取 TSLA 价格结果:")
        print(f"- 成功: {response.success}")
        print(f"- 数据源: {response.source.value}")
        print(f"- 元数据: {response.metadata}")
        
        if not response.success:
            print(f"- 错误: {response.error}")
    
    finally:
        await mcp_interface.close()


async def agent_tool_filtering_example():
    """Agent 工具过滤示例"""
    print("\n=== Agent 工具过滤示例 ===")
    
    from AICrews.tools.mcp._infra.tool_registry import get_tool_registry
    
    registry = get_tool_registry()
    
    # 不同 Agent 的可用工具
    agents = [
        AgentType.MARKET_ANALYZER,
        AgentType.FUNDAMENTAL_ANALYST,
        AgentType.NEWS_ANALYZER,
        AgentType.TRADING_BOT
    ]
    
    for agent_type in agents:
        tools = registry.get_tools_for_agent(agent_type)
        print(f"\n{agent_type.value} 可用工具 ({len(tools)} 个):")
        for tool in tools:
            print(f"  - {tool.name} (优先级: {tool.priority}, 提供商: {tool.provider})")


async def configuration_example():
    """配置示例"""
    print("\n=== 配置示例 ===")
    
    from AICrews.tools.mcp._infra.openbb_config import get_openbb_config
    from AICrews.config.settings import get_settings
    
    # 获取 OpenBB 配置
    openbb_config = get_openbb_config()
    print(f"OpenBB 可用数据源: {openbb_config.enabled_providers}")
    print(f"股票价格优先级: {openbb_config.get_provider_for_data_type('stock_price')}")
    
    # 获取全局设置
    settings = get_settings()
    print(f"\nMCP 启用状态: {settings.mcp.enabled}")
    print(f"Agent 使用 MCP: {settings.mcp.use_mcp_for_agents}")


async def main():
    """运行所有示例"""
    print("MCP 集成示例\n")
    
    # 运行各个示例
    await market_analyzer_example()
    await fundamental_analyst_example()
    await chinese_market_example()
    await fallback_strategy_example()
    await agent_tool_filtering_example()
    await configuration_example()
    
    print("\n\n所有示例运行完成！")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
