"""
Capability Taxonomy - Standard capability definitions.

This module defines the flat capability taxonomy used across the system.
Capabilities are the stable abstraction layer between providers and skills.

Groups (for UI display only, not in loadout schema):
- market_data: Data from financial markets
- compute: Calculation and analysis
- external_io: External web/API access
"""
from typing import Dict, List, Set

# =============================================================================
# MARKET DATA CAPABILITIES
# =============================================================================

# Core capabilities (default exposed in UI)
CORE_CAPABILITIES: List[str] = [
    "equity_quote",        # Real-time stock quote/snapshot
    "equity_history",      # Historical OHLCV data
    "equity_fundamentals", # Company overview/key metrics
    "equity_financials",   # Financial statements
    "equity_news",         # Company/market news
    "macro_indicators",    # Macroeconomic data
]

# Extended capabilities (collapsed in UI by default)
EXTENDED_CAPABILITIES: List[str] = [
    "equity_intraday",          # Minute/pre-market data
    "equity_orderbook",         # Order book/bid-ask
    "equity_corporate_actions", # Dividends/splits/buybacks
    "equity_ownership",         # Shareholders/holdings
    "equity_earnings",          # Earnings/guidance/calendar
    "equity_analyst_research",  # Ratings/targets/reports
    "market_overview",          # Market/sector/trending
    "index_history",            # Index historical data
    "index_constituents",       # Index components/weights
    "sector_industry",          # Sector/concept data
    "fund_flow",                # Capital flow data
    "sentiment",                # Market sentiment
    "funds_etfs",               # ETF/mutual fund data
    "bonds",                    # Bond/convertible data
    "options",                  # Options data
    "crypto",                   # Cryptocurrency data
    "forex",                    # Foreign exchange data
    "futures",                  # Futures data
    "esg",                      # ESG data
]

# =============================================================================
# COMPUTE CAPABILITIES (built-in primitives)
# =============================================================================

COMPUTE_CAPABILITIES: List[str] = [
    "indicator_calc",  # Technical indicator calculation
    "strategy_eval",   # Formula/strategy evaluation
]

# =============================================================================
# EXTERNAL IO CAPABILITIES
# =============================================================================

EXTERNAL_CAPABILITIES: List[str] = [
    "web_search",   # Web search
    "web_scrape",   # Web page scraping
    "web_browse",   # Browser interaction
]

# =============================================================================
# INFRASTRUCTURE CAPABILITIES (file/code operations)
# =============================================================================

INFRASTRUCTURE_CAPABILITIES: List[str] = [
    "file_read",       # Read file contents
    "directory_read",  # List directory contents
    "code_execute",    # Execute code (Python, etc.)
]

# =============================================================================
# COMBINED
# =============================================================================

ALL_CAPABILITIES: List[str] = (
    CORE_CAPABILITIES +
    EXTENDED_CAPABILITIES +
    COMPUTE_CAPABILITIES +
    EXTERNAL_CAPABILITIES +
    INFRASTRUCTURE_CAPABILITIES
)

ALL_CAPABILITIES_SET: Set[str] = set(ALL_CAPABILITIES)

# =============================================================================
# CAPABILITY METADATA
# =============================================================================

CAPABILITY_METADATA: Dict[str, Dict] = {
    # Core Market Data
    "equity_quote": {
        "display_name": "Stock Quote",
        "description": "Real-time or delayed stock price snapshot",
        "group": "market_data",
        "icon": "trending-up",
    },
    "equity_history": {
        "display_name": "Historical Prices",
        "description": "Historical OHLCV candlestick data",
        "group": "market_data",
        "icon": "bar-chart-2",
    },
    "equity_fundamentals": {
        "display_name": "Fundamentals",
        "description": "Company overview, key metrics, valuation",
        "group": "market_data",
        "icon": "file-text",
    },
    "equity_financials": {
        "display_name": "Financial Statements",
        "description": "Income statement, balance sheet, cash flow",
        "group": "market_data",
        "icon": "dollar-sign",
    },
    "equity_news": {
        "display_name": "News",
        "description": "Company and market news articles",
        "group": "market_data",
        "icon": "newspaper",
    },
    "macro_indicators": {
        "display_name": "Macro Indicators",
        "description": "GDP, CPI, interest rates, economic data",
        "group": "market_data",
        "icon": "globe",
    },

    # Extended Market Data
    "equity_intraday": {
        "display_name": "Intraday Data",
        "description": "Minute-level and pre-market data",
        "group": "market_data",
        "icon": "clock",
    },
    "equity_orderbook": {
        "display_name": "Order Book",
        "description": "Bid/ask prices and volumes",
        "group": "market_data",
        "icon": "layers",
    },
    "equity_corporate_actions": {
        "display_name": "Corporate Actions",
        "description": "Dividends, splits, buybacks, pledges",
        "group": "market_data",
        "icon": "git-branch",
    },
    "equity_ownership": {
        "display_name": "Ownership",
        "description": "Major shareholders and institutional holdings",
        "group": "market_data",
        "icon": "users",
    },
    "equity_earnings": {
        "display_name": "Earnings",
        "description": "Earnings reports, guidance, calendar",
        "group": "market_data",
        "icon": "calendar",
    },
    "equity_analyst_research": {
        "display_name": "Analyst Research",
        "description": "Ratings, price targets, research reports",
        "group": "market_data",
        "icon": "star",
    },
    "market_overview": {
        "display_name": "Market Overview",
        "description": "Market indices, sectors, trending stocks",
        "group": "market_data",
        "icon": "activity",
    },
    "index_history": {
        "display_name": "Index History",
        "description": "Historical index data",
        "group": "market_data",
        "icon": "bar-chart",
    },
    "index_constituents": {
        "display_name": "Index Constituents",
        "description": "Index components and weights",
        "group": "market_data",
        "icon": "list",
    },
    "sector_industry": {
        "display_name": "Sector/Industry",
        "description": "Sector and industry classification data",
        "group": "market_data",
        "icon": "grid",
    },
    "fund_flow": {
        "display_name": "Fund Flow",
        "description": "Capital flow and money movement data",
        "group": "market_data",
        "icon": "arrow-right-circle",
    },
    "sentiment": {
        "display_name": "Market Sentiment",
        "description": "Fear/greed index, sentiment indicators",
        "group": "market_data",
        "icon": "heart",
    },
    "funds_etfs": {
        "display_name": "Funds & ETFs",
        "description": "Mutual fund and ETF data",
        "group": "market_data",
        "icon": "package",
    },
    "bonds": {
        "display_name": "Bonds",
        "description": "Bond and convertible securities data",
        "group": "market_data",
        "icon": "credit-card",
    },
    "options": {
        "display_name": "Options",
        "description": "Options chain and pricing data",
        "group": "market_data",
        "icon": "shuffle",
    },
    "crypto": {
        "display_name": "Cryptocurrency",
        "description": "Cryptocurrency prices and data",
        "group": "market_data",
        "icon": "bitcoin",
    },
    "forex": {
        "display_name": "Forex",
        "description": "Foreign exchange rates",
        "group": "market_data",
        "icon": "repeat",
    },
    "futures": {
        "display_name": "Futures",
        "description": "Futures contracts data",
        "group": "market_data",
        "icon": "fast-forward",
    },
    "esg": {
        "display_name": "ESG",
        "description": "Environmental, Social, Governance data",
        "group": "market_data",
        "icon": "leaf",
    },

    # Compute
    "indicator_calc": {
        "display_name": "Indicator Calculation",
        "description": "Calculate technical indicators (RSI, MACD, MA, etc.)",
        "group": "compute",
        "icon": "cpu",
    },
    "strategy_eval": {
        "display_name": "Strategy Evaluation",
        "description": "Evaluate formula-based trading strategies",
        "group": "compute",
        "icon": "zap",
    },

    # External IO
    "web_search": {
        "display_name": "Web Search",
        "description": "Search the web for information",
        "group": "external_io",
        "icon": "search",
    },
    "web_scrape": {
        "display_name": "Web Scrape",
        "description": "Extract content from web pages",
        "group": "external_io",
        "icon": "download",
    },
    "web_browse": {
        "display_name": "Web Browse",
        "description": "Interactive web browsing",
        "group": "external_io",
        "icon": "globe",
    },

    # Infrastructure
    "file_read": {
        "display_name": "File Read",
        "description": "Read file contents from filesystem",
        "group": "infrastructure",
        "icon": "file",
    },
    "directory_read": {
        "display_name": "Directory Read",
        "description": "List directory contents",
        "group": "infrastructure",
        "icon": "folder",
    },
    "code_execute": {
        "display_name": "Code Execute",
        "description": "Execute code in sandbox environment",
        "group": "infrastructure",
        "icon": "code",
    },
}

# =============================================================================
# CAPABILITY DEPENDENCIES
# =============================================================================

# Some capabilities require others to function
CAPABILITY_DEPENDENCIES: Dict[str, List[str]] = {
    "indicator_calc": ["equity_history"],
    "strategy_eval": ["equity_history"],
}


def is_valid_capability(capability_id: str) -> bool:
    """Check if a capability_id is valid."""
    return capability_id in ALL_CAPABILITIES_SET


def get_capability_group(capability_id: str) -> str:
    """Get the group for a capability."""
    meta = CAPABILITY_METADATA.get(capability_id, {})
    return meta.get("group", "unknown")


def get_capability_dependencies(capability_id: str) -> List[str]:
    """Get dependencies for a capability."""
    return CAPABILITY_DEPENDENCIES.get(capability_id, [])


def get_capabilities_by_group(group: str) -> List[str]:
    """Get all capabilities in a group."""
    return [
        cap_id for cap_id, meta in CAPABILITY_METADATA.items()
        if meta.get("group") == group
    ]
