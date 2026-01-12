#!/usr/bin/env python3
"""
MCP 数据库初始化脚本

创建 MCP 相关表并初始化默认的系统级 MCP 服务器
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from AICrews.database.models import (
    Base, MCPServer, MCPTool, UserMCPServer, UserMCPTool,
    UserToolConfig, AgentToolBinding
)
from AICrews.config import get_settings


def init_mcp_tables(engine):
    """创建 MCP 相关表"""
    print("Creating MCP tables...")
    
    # 只创建 MCP 相关表
    mcp_tables = [
        MCPServer.__table__,
        MCPTool.__table__,
        UserMCPServer.__table__,
        UserMCPTool.__table__,
        UserToolConfig.__table__,
        AgentToolBinding.__table__,
    ]
    
    for table in mcp_tables:
        try:
            table.create(engine, checkfirst=True)
            print(f"  ✓ Created table: {table.name}")
        except Exception as e:
            print(f"  ⚠ Table {table.name} may already exist: {e}")


def init_system_servers(session):
    """初始化系统级 MCP 服务器"""
    print("\nInitializing system MCP servers...")
    
    # 检查是否已初始化
    existing = session.query(MCPServer).count()
    if existing > 0:
        print(f"  ⚠ Already initialized with {existing} servers, skipping...")
        return
    
    default_servers = [
        MCPServer(
            server_key="openbb",
            display_name="OpenBB Platform",
            description="OpenBB Platform MCP 服务器，提供 170+ 金融数据工具。覆盖股票、期权、外汇、加密货币、宏观经济等数据。支持多个数据源：FMP、Polygon、Yahoo Finance 等。",
            transport_type="http_sse",
            url=os.getenv("OPENBB_MCP_URL", "http://localhost:8008/mcp"),
            requires_auth=True,
            auth_type="api_key",
            default_api_key_env="OPENBB_TOKEN",
            provider="openbb",
            capabilities={
                "caching": True,
                "rate_limit": 60,
                "supports_streaming": True,
            },
            is_system=True,
            is_active=True,
            icon="trending-up",
            documentation_url="https://docs.openbb.co/platform",
            sort_order=1,
        ),
        MCPServer(
            server_key="china_market",
            display_name="中国市场数据",
            description="基于 Akshare 的中国市场数据服务。提供 A股、港股历史行情、实时行情、财务报表、宏观经济数据等。免费且无需 API Key。",
            transport_type="http_sse",
            url=os.getenv("CHINA_MCP_URL", "http://localhost:8009/mcp"),
            requires_auth=False,
            provider="akshare",
            capabilities={
                "caching": True,
                "rate_limit": 60,
            },
            is_system=True,
            is_active=True,
            icon="flag",
            sort_order=2,
        ),
    ]
    
    for server in default_servers:
        session.add(server)
        print(f"  ✓ Added server: {server.display_name}")
    
    session.commit()
    print(f"\n  ✓ Initialized {len(default_servers)} system MCP servers")


def init_mock_tools(session):
    """初始化模拟工具（用于开发和演示）"""
    print("\nInitializing mock tools for development...")
    
    # 检查是否已有工具
    existing = session.query(MCPTool).count()
    if existing > 0:
        print(f"  ⚠ Already have {existing} tools, skipping...")
        return
    
    # 获取服务器
    openbb = session.query(MCPServer).filter_by(server_key="openbb").first()
    china = session.query(MCPServer).filter_by(server_key="china_market").first()
    
    if not openbb or not china:
        print("  ⚠ System servers not found, skipping tool init...")
        return
    
    # OpenBB 工具
    openbb_tools = [
        MCPTool(
            server_id=openbb.id,
            tool_name="equity_price_historical",
            display_name="股票历史价格",
            description="Get historical OHLCV price data for stocks. Supports multiple providers: yfinance, fmp, polygon.",
            category="market_data",
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol"},
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "provider": {"type": "string", "description": "Data provider"}
                },
                "required": ["symbol"]
            },
            required_params=["symbol"],
            requires_api_key=False,
            tags=["stock", "price", "historical", "ohlcv"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="equity_price_quote",
            display_name="股票实时报价",
            description="Get real-time quote for stocks including bid/ask prices, volume, and market cap.",
            category="market_data",
            requires_api_key=False,
            tags=["stock", "price", "quote", "realtime"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="equity_fundamental_overview",
            display_name="公司基本面概览",
            description="Get company fundamental overview including PE ratio, market cap, revenue, and key metrics.",
            category="fundamental",
            requires_api_key=True,
            api_key_provider="Financial Modeling Prep",
            api_key_env="FMP_API_KEY",
            tags=["fundamental", "overview", "metrics"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="equity_fundamental_income",
            display_name="利润表",
            description="Get income statement data including revenue, expenses, and net income.",
            category="fundamental",
            requires_api_key=True,
            api_key_provider="Financial Modeling Prep",
            tags=["fundamental", "income", "financial_statement"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="equity_fundamental_balance",
            display_name="资产负债表",
            description="Get balance sheet data including assets, liabilities, and equity.",
            category="fundamental",
            requires_api_key=True,
            api_key_provider="Financial Modeling Prep",
            tags=["fundamental", "balance_sheet", "financial_statement"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="equity_fundamental_cash",
            display_name="现金流量表",
            description="Get cash flow statement data including operating, investing, and financing activities.",
            category="fundamental",
            requires_api_key=True,
            api_key_provider="Financial Modeling Prep",
            tags=["fundamental", "cashflow", "financial_statement"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="news_company",
            display_name="公司新闻",
            description="Get latest news articles for a specific company.",
            category="news",
            requires_api_key=False,
            tags=["news", "company", "sentiment"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="technical_sma",
            display_name="简单移动平均线 (SMA)",
            description="Calculate Simple Moving Average for a stock.",
            category="technical",
            requires_api_key=False,
            tags=["technical", "sma", "indicator"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="technical_rsi",
            display_name="相对强弱指数 (RSI)",
            description="Calculate Relative Strength Index for a stock.",
            category="technical",
            requires_api_key=False,
            tags=["technical", "rsi", "momentum"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="technical_macd",
            display_name="MACD 指标",
            description="Calculate MACD indicator including signal line and histogram.",
            category="technical",
            requires_api_key=False,
            tags=["technical", "macd", "trend"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="economy_gdp",
            display_name="GDP 数据",
            description="Get Gross Domestic Product data for countries.",
            category="macro",
            requires_api_key=False,
            tags=["economy", "gdp", "macro"],
            is_active=True,
        ),
        MCPTool(
            server_id=openbb.id,
            tool_name="economy_cpi",
            display_name="CPI 通胀数据",
            description="Get Consumer Price Index inflation data.",
            category="macro",
            requires_api_key=False,
            tags=["economy", "cpi", "inflation"],
            is_active=True,
        ),
    ]
    
    # 中国市场工具
    china_tools = [
        MCPTool(
            server_id=china.id,
            tool_name="stock_zh_a_hist",
            display_name="A股历史行情",
            description="获取A股股票历史行情数据，包括日K、周K、月K。",
            category="market_data",
            requires_api_key=False,
            tags=["china", "a_share", "historical"],
            is_active=True,
        ),
        MCPTool(
            server_id=china.id,
            tool_name="stock_zh_a_spot",
            display_name="A股实时行情",
            description="获取A股股票实时行情数据，包括最新价、涨跌幅、成交量。",
            category="market_data",
            requires_api_key=False,
            tags=["china", "a_share", "realtime"],
            is_active=True,
        ),
        MCPTool(
            server_id=china.id,
            tool_name="stock_hk_hist",
            display_name="港股历史行情",
            description="获取港股股票历史行情数据。",
            category="market_data",
            requires_api_key=False,
            tags=["china", "hk", "historical"],
            is_active=True,
        ),
        MCPTool(
            server_id=china.id,
            tool_name="stock_financial_report",
            display_name="A股财务报表",
            description="获取A股公司财务报表数据，包括资产负债表、利润表、现金流量表。",
            category="fundamental",
            requires_api_key=False,
            tags=["china", "financial", "report"],
            is_active=True,
        ),
        MCPTool(
            server_id=china.id,
            tool_name="macro_china_gdp",
            display_name="中国GDP数据",
            description="获取中国国内生产总值历史数据。",
            category="macro",
            requires_api_key=False,
            tags=["china", "gdp", "macro"],
            is_active=True,
        ),
        MCPTool(
            server_id=china.id,
            tool_name="news_cctv",
            display_name="央视财经新闻",
            description="获取央视财经频道的最新新闻。",
            category="news",
            requires_api_key=False,
            tags=["china", "news", "cctv"],
            is_active=True,
        ),
    ]
    
    all_tools = openbb_tools + china_tools
    for tool in all_tools:
        session.add(tool)
    
    session.commit()
    print(f"  ✓ Initialized {len(all_tools)} mock tools")


def main():
    print("=" * 60)
    print("MCP Database Initialization")
    print("=" * 60)
    
    # 获取数据库 URL - 直接从环境变量获取
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        # 尝试从各个部分构建
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "trading_agents")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    print(f"\nDatabase: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    
    # 创建引擎
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 初始化表
        init_mcp_tables(engine)
        
        # 初始化系统服务器
        init_system_servers(session)
        
        # 初始化模拟工具（开发用）
        init_mock_tools(session)
        
        print("\n" + "=" * 60)
        print("✓ MCP database initialization completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
