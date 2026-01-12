/**
 * Frontend Capability Taxonomy
 *
 * Simplified version of AICrews/capabilities/taxonomy.py
 * Used for UI display and capability mapping
 */

export const CORE_CAPABILITIES = [
  "equity_quote",
  "equity_history",
  "equity_fundamentals",
  "equity_financials",
  "equity_news",
  "macro_indicators",
];

export const EXTENDED_CAPABILITIES = [
  "equity_intraday",
  "equity_orderbook",
  "equity_corporate_actions",
  "equity_ownership",
  "equity_earnings",
  "equity_analyst_research",
  "market_overview",
  "index_history",
  "index_constituents",
  "sector_industry",
  "fund_flow",
  "sentiment",
  "funds_etfs",
  "bonds",
  "options",
  "crypto",
  "forex",
  "futures",
  "esg",
];

export const COMPUTE_CAPABILITIES = [
  "indicator_calc",
  "strategy_eval",
];

export const EXTERNAL_CAPABILITIES = [
  "web_search",
  "web_scrape",
  "web_browse",
];

export const INFRASTRUCTURE_CAPABILITIES = [
  "file_read",
  "directory_read",
  "code_execute",
];

export const ALL_CAPABILITIES = [
  ...CORE_CAPABILITIES,
  ...EXTENDED_CAPABILITIES,
  ...COMPUTE_CAPABILITIES,
  ...EXTERNAL_CAPABILITIES,
  ...INFRASTRUCTURE_CAPABILITIES,
];

export const CAPABILITY_METADATA: Record<string, {
  display_name: string;
  description: string;
  group: string;
  icon?: string;
}> = {
  // Core Market Data
  equity_quote: {
    display_name: "Stock Quote",
    description: "Real-time or delayed stock price snapshot",
    group: "market_data",
    icon: "trending-up",
  },
  equity_history: {
    display_name: "Historical Prices",
    description: "Historical OHLCV candlestick data",
    group: "market_data",
    icon: "bar-chart-2",
  },
  equity_fundamentals: {
    display_name: "Fundamentals",
    description: "Company overview, key metrics, valuation",
    group: "market_data",
    icon: "file-text",
  },
  equity_financials: {
    display_name: "Financial Statements",
    description: "Income statement, balance sheet, cash flow",
    group: "market_data",
    icon: "dollar-sign",
  },
  equity_news: {
    display_name: "News",
    description: "Company and market news articles",
    group: "market_data",
    icon: "newspaper",
  },
  macro_indicators: {
    display_name: "Macro Indicators",
    description: "GDP, CPI, interest rates, economic data",
    group: "market_data",
    icon: "globe",
  },

  // Extended Market Data
  equity_intraday: {
    display_name: "Intraday Data",
    description: "Minute-level and pre-market data",
    group: "market_data",
    icon: "clock",
  },
  equity_orderbook: {
    display_name: "Order Book",
    description: "Bid/ask prices and volumes",
    group: "market_data",
    icon: "layers",
  },
  equity_corporate_actions: {
    display_name: "Corporate Actions",
    description: "Dividends, splits, buybacks, pledges",
    group: "market_data",
    icon: "git-branch",
  },
  equity_ownership: {
    display_name: "Ownership",
    description: "Major shareholders and institutional holdings",
    group: "market_data",
    icon: "users",
  },
  equity_earnings: {
    display_name: "Earnings",
    description: "Earnings reports, guidance, calendar",
    group: "market_data",
    icon: "dollar-sign",
  },
  equity_analyst_research: {
    display_name: "Analyst Research",
    description: "Analyst ratings, price targets, research reports",
    group: "market_data",
    icon: "file-text",
  },
  market_overview: {
    display_name: "Market Overview",
    description: "Market summary, sector performance, trending stocks",
    group: "market_data",
    icon: "trending-up",
  },
  index_history: {
    display_name: "Index History",
    description: "Historical index data",
    group: "market_data",
    icon: "bar-chart-2",
  },
  index_constituents: {
    display_name: "Index Constituents",
    description: "Index components and weights",
    group: "market_data",
    icon: "list",
  },
  sector_industry: {
    display_name: "Sector/Industry",
    description: "Sector and industry classification data",
    group: "market_data",
    icon: "folder",
  },
  fund_flow: {
    display_name: "Fund Flow",
    description: "Capital flow and fund movement data",
    group: "market_data",
    icon: "trending-up",
  },
  sentiment: {
    display_name: "Market Sentiment",
    description: "Market sentiment and mood indicators",
    group: "market_data",
    icon: "activity",
  },
  funds_etfs: {
    display_name: "Funds & ETFs",
    description: "ETF and mutual fund data",
    group: "market_data",
    icon: "briefcase",
  },
  bonds: {
    display_name: "Bonds",
    description: "Bond and convertible bond data",
    group: "market_data",
    icon: "file-text",
  },
  options: {
    display_name: "Options",
    description: "Options chain and derivatives data",
    group: "market_data",
    icon: "git-branch",
  },
  crypto: {
    display_name: "Cryptocurrency",
    description: "Cryptocurrency prices and data",
    group: "market_data",
    icon: "bitcoin",
  },
  forex: {
    display_name: "Forex",
    description: "Foreign exchange rates",
    group: "market_data",
    icon: "dollar-sign",
  },
  futures: {
    display_name: "Futures",
    description: "Futures contracts and prices",
    group: "market_data",
    icon: "trending-up",
  },
  esg: {
    display_name: "ESG",
    description: "Environmental, Social, Governance ratings",
    group: "market_data",
    icon: "leaf",
  },

  // Compute Capabilities
  indicator_calc: {
    display_name: "Indicator Calculation",
    description: "Calculate technical indicators",
    group: "compute",
    icon: "activity",
  },
  strategy_eval: {
    display_name: "Strategy Evaluation",
    description: "Evaluate trading strategies",
    group: "compute",
    icon: "zap",
  },

  // External IO
  web_search: {
    display_name: "Web Search",
    description: "Search the web for information",
    group: "external_io",
    icon: "search",
  },
  web_scrape: {
    display_name: "Web Scraping",
    description: "Scrape content from web pages",
    group: "external_io",
    icon: "download",
  },
  web_browse: {
    display_name: "Web Browsing",
    description: "Interactive browser automation",
    group: "external_io",
    icon: "globe",
  },

  // Infrastructure
  file_read: {
    display_name: "File Read",
    description: "Read file contents from filesystem",
    group: "infrastructure",
    icon: "file",
  },
  directory_read: {
    display_name: "Directory Read",
    description: "List directory contents",
    group: "infrastructure",
    icon: "folder",
  },
  code_execute: {
    display_name: "Code Execute",
    description: "Execute code in sandbox environment",
    group: "infrastructure",
    icon: "code",
  },
};
