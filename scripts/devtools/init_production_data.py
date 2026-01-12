#!/usr/bin/env python3
"""
Production Data Initialization Script

Initializes database with:
1. System MCP servers and tools
2. Sample knowledge sources
3. Default user configurations
4. Test data for development

Ensures frontend can display and manage MCP tools and knowledge sources properly.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from AICrews.database.db_manager import DBManager
from AICrews.database.models import (
    User, MCPServer, MCPTool, KnowledgeSource, 
    UserKnowledgeSubscription, UserMCPSubscription,
    AgentDefinition, CrewDefinition
)


def init_mcp_servers_and_tools(session):
    """Initialize system MCP servers and tools"""
    print("🔧 Initializing MCP servers and tools...")
    
    # 1. Akshare MCP Server (Financial Data)
    akshare_server = MCPServer(
        server_key="akshare",
        display_name="Akshare Financial Data",
        description="Chinese financial market data provider with stock prices, news, and analysis",
        transport_type="http_sse",
        url="http://localhost:8001",
        requires_auth=False,
        provider="akshare",
        is_active=True,
        is_system=True,
        icon="📈",
        documentation_url="https://akshare.akfamily.xyz/",
        category="financial_data"
    )
    session.add(akshare_server)
    session.flush()
    
    # Akshare tools
    akshare_tools = [
        {
            "tool_name": "get_stock_info",
            "display_name": "Stock Basic Info",
            "description": "Get basic information about a stock including name, industry, market cap",
            "category": "stock_data",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol (e.g., 000001)"}
                },
                "required": ["symbol"]
            }
        },
        {
            "tool_name": "get_stock_price",
            "display_name": "Stock Price Data",
            "description": "Get current and historical stock price data",
            "category": "stock_data",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol"},
                    "period": {"type": "string", "enum": ["1d", "5d", "1m", "3m", "6m", "1y"]}
                },
                "required": ["symbol"]
            }
        },
        {
            "tool_name": "get_stock_news",
            "display_name": "Stock News",
            "description": "Get latest news and announcements for a stock",
            "category": "news",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["symbol"]
            }
        }
    ]
    
    for tool_data in akshare_tools:
        tool = MCPTool(
            server_id=akshare_server.id,
            tool_name=tool_data["tool_name"],
            display_name=tool_data["display_name"],
            description=tool_data["description"],
            category=tool_data["category"],
            input_schema=tool_data["input_schema"],
            requires_api_key=False,
            is_active=True,
            tags=["financial", "stock", "data"]
        )
        session.add(tool)
    
    # 2. OpenBB MCP Server (Advanced Financial Analytics)
    openbb_server = MCPServer(
        server_key="openbb",
        display_name="OpenBB Financial Analytics",
        description="Advanced financial analytics and market data platform",
        transport_type="http_sse",
        url="http://localhost:8002",
        requires_auth=True,
        provider="openbb",
        is_active=True,
        is_system=True,
        icon="📊",
        documentation_url="https://openbb.co/",
        category="financial_analytics"
    )
    session.add(openbb_server)
    session.flush()
    
    # OpenBB tools
    openbb_tools = [
        {
            "tool_name": "technical_analysis",
            "display_name": "Technical Analysis",
            "description": "Perform technical analysis on stock data with indicators",
            "category": "analysis",
            "requires_api_key": True,
            "api_key_provider": "openbb"
        },
        {
            "tool_name": "fundamental_analysis",
            "display_name": "Fundamental Analysis",
            "description": "Get fundamental analysis data including P/E, ROE, debt ratios",
            "category": "analysis",
            "requires_api_key": True,
            "api_key_provider": "openbb"
        },
        {
            "tool_name": "market_sentiment",
            "display_name": "Market Sentiment",
            "description": "Analyze market sentiment from news and social media",
            "category": "sentiment",
            "requires_api_key": True,
            "api_key_provider": "openbb"
        }
    ]
    
    for tool_data in openbb_tools:
        tool = MCPTool(
            server_id=openbb_server.id,
            tool_name=tool_data["tool_name"],
            display_name=tool_data["display_name"],
            description=tool_data["description"],
            category=tool_data["category"],
            requires_api_key=tool_data.get("requires_api_key", False),
            api_key_provider=tool_data.get("api_key_provider"),
            is_active=True,
            tags=["financial", "analytics", "premium"]
        )
        session.add(tool)
    
    print(f"✅ Created {2} MCP servers with {len(akshare_tools) + len(openbb_tools)} tools")


def init_knowledge_sources(session):
    """Initialize system knowledge sources"""
    print("📚 Initializing knowledge sources...")
    
    knowledge_sources = [
        {
            "source_key": "buffett_letters",
            "display_name": "Warren Buffett Annual Letters",
            "description": "Complete collection of Warren Buffett's annual letters to Berkshire Hathaway shareholders",
            "category": "investment_philosophy",
            "scope": "system",
            "tier": "free",
            "file_path": "/knowledge/buffett/annual_letters.pdf",
            "tags": ["buffett", "value_investing", "philosophy"]
        },
        {
            "source_key": "graham_intelligent_investor",
            "display_name": "The Intelligent Investor",
            "description": "Benjamin Graham's classic book on value investing principles",
            "category": "investment_books",
            "scope": "system", 
            "tier": "free",
            "file_path": "/knowledge/books/intelligent_investor.pdf",
            "tags": ["graham", "value_investing", "classic"]
        },
        {
            "source_key": "fed_minutes",
            "display_name": "Federal Reserve Meeting Minutes",
            "description": "Recent Federal Reserve FOMC meeting minutes and policy statements",
            "category": "monetary_policy",
            "scope": "system",
            "tier": "premium",
            "file_path": "/knowledge/fed/fomc_minutes.json",
            "tags": ["fed", "monetary_policy", "macroeconomics"]
        },
        {
            "source_key": "earnings_transcripts",
            "display_name": "S&P 500 Earnings Call Transcripts",
            "description": "Recent earnings call transcripts from major S&P 500 companies",
            "category": "earnings",
            "scope": "system",
            "tier": "premium", 
            "file_path": "/knowledge/earnings/sp500_transcripts.json",
            "tags": ["earnings", "transcripts", "sp500"]
        },
        {
            "source_key": "market_research",
            "display_name": "Institutional Research Reports",
            "description": "Research reports from major investment banks and institutions",
            "category": "research",
            "scope": "system",
            "tier": "premium",
            "file_path": "/knowledge/research/institutional_reports.json",
            "tags": ["research", "institutional", "analysis"]
        }
    ]
    
    for ks_data in knowledge_sources:
        ks = KnowledgeSource(
            source_key=ks_data["source_key"],
            display_name=ks_data["display_name"],
            description=ks_data["description"],
            source_type="file",  # Required field
            category=ks_data["category"],
            scope=ks_data["scope"],
            tier=ks_data["tier"],
            file_path=ks_data["file_path"],
            tags=ks_data["tags"],
            is_active=True,
            usage_count=0
        )
        session.add(ks)
    
    print(f"✅ Created {len(knowledge_sources)} knowledge sources")


def init_test_user_and_subscriptions(session):
    """Initialize test user with subscriptions"""
    print("👤 Initializing test user and subscriptions...")
    
    # Check if test user exists
    test_user = session.query(User).filter(User.email == "test@financeai.com").first()
    if not test_user:
        test_user = User(
            email="test@financeai.com",
            password_hash="test_hash_123",  # Required field
            subscription_level="premium"  # Give premium access for testing
        )
        session.add(test_user)
        session.flush()
    
    # Subscribe to free knowledge sources
    free_sources = session.query(KnowledgeSource).filter(
        KnowledgeSource.tier == "free"
    ).all()
    
    for source in free_sources:
        existing_sub = session.query(UserKnowledgeSubscription).filter(
            UserKnowledgeSubscription.user_id == test_user.id,
            UserKnowledgeSubscription.source_id == source.id
        ).first()
        
        if not existing_sub:
            subscription = UserKnowledgeSubscription(
                user_id=test_user.id,
                source_id=source.id,
                is_active=True,
                subscribed_at=datetime.now()
            )
            session.add(subscription)
    
    # Subscribe to some premium sources (simulate paid user)
    premium_sources = session.query(KnowledgeSource).filter(
        KnowledgeSource.tier == "premium"
    ).limit(2).all()
    
    for source in premium_sources:
        existing_sub = session.query(UserKnowledgeSubscription).filter(
            UserKnowledgeSubscription.user_id == test_user.id,
            UserKnowledgeSubscription.source_id == source.id
        ).first()
        
        if not existing_sub:
            subscription = UserKnowledgeSubscription(
                user_id=test_user.id,
                source_id=source.id,
                is_active=True,
                subscribed_at=datetime.now(),
                valid_until=datetime.now() + timedelta(days=365)  # 1 year subscription
            )
            session.add(subscription)
    
    # Subscribe to MCP servers
    mcp_servers = session.query(MCPServer).filter(MCPServer.is_system == True).all()
    
    for server in mcp_servers:
        existing_sub = session.query(UserMCPSubscription).filter(
            UserMCPSubscription.user_id == test_user.id,
            UserMCPSubscription.server_id == server.id
        ).first()
        
        if not existing_sub:
            subscription = UserMCPSubscription(
                user_id=test_user.id,
                server_id=server.id,
                is_active=True,
                api_key="test_api_key_123" if server.requires_auth else None
            )
            session.add(subscription)
    
    print(f"✅ Set up test user with subscriptions")
    return test_user.id


def init_sample_agents_and_crews(session, user_id):
    """Initialize sample agents and crews for testing"""
    print("🤖 Initializing sample agents and crews...")
    
    # Create sample agents
    agents_data = [
        {
            "name": "Financial Research Agent",
            "role": "Senior Financial Analyst",
            "goal": "Research and analyze financial data for {ticker} using market data and news",
            "backstory": "You are an experienced financial analyst with 10+ years in equity research. You specialize in fundamental analysis and market sentiment evaluation.",
            "llm_config": {"model": "gpt-4o", "temperature": 0.1},
            "tool_ids": [1, 2, 3],  # Akshare tools
            "knowledge_source_ids": [1, 2],  # Free knowledge sources
            "mcp_server_ids": [1]  # Akshare server
        },
        {
            "name": "Technical Analysis Agent", 
            "role": "Technical Analyst",
            "goal": "Perform technical analysis on {ticker} using advanced charting and indicators",
            "backstory": "You are a technical analysis expert who specializes in chart patterns, technical indicators, and market timing.",
            "llm_config": {"model": "gpt-4o", "temperature": 0.2},
            "tool_ids": [4, 5],  # OpenBB tools
            "knowledge_source_ids": [],
            "mcp_server_ids": [2]  # OpenBB server
        },
        {
            "name": "Investment Strategist",
            "role": "Investment Strategist", 
            "goal": "Synthesize research and technical analysis to provide investment recommendations for {ticker}",
            "backstory": "You are a senior investment strategist who combines fundamental and technical analysis to make informed investment decisions.",
            "llm_config": {"model": "gpt-4o", "temperature": 0.3},
            "tool_ids": [],
            "knowledge_source_ids": [1, 2, 3],  # Include premium sources
            "mcp_server_ids": []
        }
    ]
    
    created_agents = []
    for agent_data in agents_data:
        agent = AgentDefinition(
            user_id=user_id,
            name=agent_data["name"],
            role=agent_data["role"],
            goal=agent_data["goal"],
            backstory=agent_data["backstory"],
            llm_config=agent_data["llm_config"],
            tool_ids=agent_data["tool_ids"],
            knowledge_source_ids=agent_data["knowledge_source_ids"],
            mcp_server_ids=agent_data["mcp_server_ids"],
            verbose=True,
            is_template=False,
            is_active=True
        )
        session.add(agent)
        session.flush()
        created_agents.append(agent)
    
    # Create sample crew with UI state
    ui_state = {
        "nodes": [
            {
                "id": "start-1",
                "type": "start",
                "data": {
                    "inputMode": "custom",
                    "variables": [
                        {"name": "ticker", "label": "Stock Symbol", "type": "text"}
                    ]
                }
            },
            {
                "id": "agent-research",
                "type": "agent", 
                "data": {
                    "agent_id": created_agents[0].id,
                    "role": "Senior Financial Analyst",
                    "taskDescription": "Research {ticker} using financial data and news sources",
                    "expectedOutput": "Comprehensive fundamental analysis report",
                    "tools": [{"id": 1}, {"id": 2}, {"id": 3}],
                    "mcpTools": [{"server_id": 1, "serverId": 1}]
                }
            },
            {
                "id": "agent-technical",
                "type": "agent",
                "data": {
                    "agent_id": created_agents[1].id,
                    "role": "Technical Analyst", 
                    "taskDescription": "Perform technical analysis on {ticker}",
                    "expectedOutput": "Technical analysis with chart patterns and indicators",
                    "tools": [{"id": 4}, {"id": 5}],
                    "mcpTools": [{"server_id": 2, "serverId": 2}]
                }
            },
            {
                "id": "agent-strategist",
                "type": "agent",
                "data": {
                    "agent_id": created_agents[2].id,
                    "role": "Investment Strategist",
                    "taskDescription": "Synthesize research and provide investment recommendation for {ticker}",
                    "expectedOutput": "Final investment recommendation with rationale"
                }
            },
            {
                "id": "end-1",
                "type": "end",
                "data": {
                    "outputFormat": "Markdown",
                    "aggregationMethod": "llm_summary",
                    "summaryModel": "gpt-4o"
                }
            }
        ],
        "edges": [
            {"from": "start-1", "to": "agent-research", "type": "control"},
            {"from": "start-1", "to": "agent-technical", "type": "control"},
            {"from": "agent-research", "to": "agent-strategist", "type": "control"},
            {"from": "agent-technical", "to": "agent-strategist", "type": "control"},
            {"from": "agent-strategist", "to": "end-1", "type": "control"}
        ],
        "viewport": {"x": 0, "y": 0, "k": 1}
    }
    
    sample_crew = CrewDefinition(
        user_id=user_id,
        name="Comprehensive Stock Analysis Crew",
        description="A complete stock analysis crew combining fundamental research, technical analysis, and investment strategy",
        process="sequential",
        structure=[],  # Will be compiled
        ui_state=ui_state,
        input_schema={},  # Will be compiled
        router_config={},
        memory_enabled=True,
        cache_enabled=True,
        verbose=True,
        is_template=False,
        is_active=True
    )
    session.add(sample_crew)
    session.flush()
    
    print(f"✅ Created {len(created_agents)} sample agents and 1 sample crew")
    return sample_crew.id


def main():
    """Main initialization function"""
    print("🚀 Starting production data initialization...")
    
    db = DBManager()
    session = db.get_session()
    
    try:
        # Initialize all components
        init_mcp_servers_and_tools(session)
        init_knowledge_sources(session)
        user_id = init_test_user_and_subscriptions(session)
        crew_id = init_sample_agents_and_crews(session, user_id)
        
        # Commit all changes
        session.commit()
        
        print("\n🎉 Production data initialization completed successfully!")
        print(f"\nCreated resources:")
        print(f"  - MCP Servers: 2 (Akshare, OpenBB)")
        print(f"  - MCP Tools: 6 total")
        print(f"  - Knowledge Sources: 5 (2 free, 3 premium)")
        print(f"  - Test User: test@financeai.com")
        print(f"  - Sample Agents: 3")
        print(f"  - Sample Crew: ID {crew_id}")
        
        print(f"\n📋 Next steps:")
        print(f"  1. Start backend server: python -m backend.app.main")
        print(f"  2. Start frontend: cd frontend && npm run dev")
        print(f"  3. Test MCP tools in Agent configuration")
        print(f"  4. Test knowledge sources in Knowledge panel")
        print(f"  5. Load sample crew ID {crew_id} in Crew Builder")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        session.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
