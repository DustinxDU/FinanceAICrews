// Constants for Crew Builder - Scenario Templates and Router Templates

export const SCENARIO_TEMPLATES: Record<string, any> = {
  single_asset: {
    name: "Single Asset Deep Dive",
    description: "Comprehensive analysis of a single stock including fundamentals and technicals.",
    schema: [
      { key: "ticker", label: "Ticker Symbol", type: "search_dropdown", placeholder: "e.g. US:NVDA, HK:0700", required: true },
      { key: "focus_area", label: "Focus Area", type: "select", options: ["Comprehensive Health Check", "Fundamentals/Earnings", "Technicals/Trend", "Institutional Flow"], default: "Comprehensive Health Check" },
      { key: "timeframe", label: "Timeframe", type: "radio", options: ["Short (1w)", "Medium (1Q)", "Long (1-3y)"], default: "Medium (1Q)" },
      { key: "extra_context", label: "Extra Context", type: "textarea", placeholder: "e.g. Focus on inventory turnover issues..." }
    ]
  },
  peer_comparison: {
    name: "Peer Comparison",
    description: "Side-by-side comparison of multiple assets against specific metrics.",
    schema: [
      { key: "assets_list", label: "Assets List", type: "multi_tag", placeholder: "e.g. KO, PEP", required: true },
      { key: "metrics", label: "Comparison Metrics", type: "checkbox_group", options: ["Valuation (PE/PB)", "Profitability (ROE/Margin)", "Dividend Yield", "Market Sentiment"], default: ["Valuation (PE/PB)", "Profitability (ROE/Margin)"] },
      { key: "benchmark", label: "Benchmark", type: "select", options: ["S&P 500", "Nasdaq 100", "Sector Avg", "None"], default: "Sector Avg" }
    ]
  },
  macro_sector: {
    name: "Macro & Sector Scan",
    description: "Top-down analysis of market sectors and macroeconomic trends.",
    schema: [
      { key: "target_sector", label: "Target Market/Sector", type: "tree_select", placeholder: "e.g. US > Tech > Semi", required: true },
      { key: "keywords", label: "Keywords/Events", type: "text", placeholder: "e.g. Rate cuts, AI Bubble", required: true },
      { key: "sources", label: "Source Preference", type: "checkbox_group", options: ["Investment Bank Reports", "Social Sentiment", "Official Press"], default: ["Investment Bank Reports"] }
    ]
  },
  event_driven: {
    name: "Event-Driven Analysis",
    description: "Impact analysis of specific news or calendar events.",
    schema: [
      { key: "event_type", label: "Event Type", type: "select", options: ["Earnings Call", "FOMC Meeting", "Product Launch", "Black Swan"], default: "Earnings Call" },
      { key: "entity", label: "Related Entity", type: "text", placeholder: "e.g. Tesla, Jerome Powell", required: true },
      { key: "goal", label: "Analysis Goal", type: "radio", options: ["Predict Volatility", "Summarize Key Points", "Arbitrage Opportunity"], default: "Summarize Key Points" }
    ]
  },
  portfolio_audit: {
    name: "Portfolio Audit",
    description: "Risk assessment and health check for a basket of holdings.",
    schema: [
      { key: "holdings", label: "Holdings (CSV/Text)", type: "textarea", placeholder: "AAPL, MSFT, GOOGL...", required: true },
      { key: "risk_profile", label: "Risk Profile", type: "slider", min: 1, max: 5, labels: ["Conservative", "Aggressive"], default: 3 },
      { key: "depth", label: "Report Depth", type: "select", options: ["Quick Scan", "Deep Stress Test"], default: "Quick Scan" }
    ]
  }
};

export const ROUTER_TEMPLATES: Record<string, any> = {
  sentiment: {
    label: "📈 Market Sentiment",
    instruction: "Analyze the previous agent's report and classify the market sentiment for the target asset.",
    routes: [
      { id: "bullish", label: "Bullish", criteria: "Report indicates positive price action, strong fundamentals, or buying pressure.", color: "text-green-400 border-green-500/50 bg-green-900/20" },
      { id: "bearish", label: "Bearish", criteria: "Report indicates negative trends, weak fundamentals, or selling pressure.", color: "text-red-400 border-red-500/50 bg-red-900/20" },
      { id: "neutral", label: "Neutral", criteria: "Signals are mixed, unclear, or indicate sideways consolidation.", color: "text-zinc-400 border-zinc-500/50 bg-zinc-900/20" }
    ]
  },
  risk: {
    label: "⚠️ Risk Level",
    instruction: "Evaluate the risk level associated with the proposed trade or investment thesis.",
    routes: [
      { id: "high_risk", label: "High Risk", criteria: "Volatile asset, regulatory uncertainty, or speculative nature.", color: "text-red-400 border-red-500/50 bg-red-900/20" },
      { id: "med_risk", label: "Medium Risk", criteria: "Standard market volatility with solid backing.", color: "text-yellow-400 border-yellow-500/50 bg-yellow-900/20" },
      { id: "low_risk", label: "Low Risk", criteria: "Blue chip, stable dividend, or hedged position.", color: "text-green-400 border-green-500/50 bg-green-900/20" }
    ]
  },
  approval: {
    label: "✅ Approval Gate",
    instruction: "Review the draft report for quality, compliance, and completeness.",
    routes: [
      { id: "approved", label: "Approved", criteria: "Report meets all criteria and is ready for publication.", color: "text-green-400 border-green-500/50 bg-green-900/20" },
      { id: "revision", label: "Needs Revision", criteria: "Missing key data points or logic is flawed.", color: "text-orange-400 border-orange-500/50 bg-orange-900/20" },
      { id: "rejected", label: "Rejected", criteria: "Violates compliance rules or is factually incorrect.", color: "text-red-400 border-red-500/50 bg-red-900/20" }
    ]
  }
};

export const LLM_ROUTING_TIERS = [
  { value: "agents_fast", label: "agents_fast" },
  { value: "agents_balanced", label: "agents_balanced" },
  { value: "agents_best", label: "agents_best" },
];

export const DEFAULT_LLM_TIER = "agents_balanced";

export const formatRoutingTier = (tier?: string): string => {
  if (!tier) return DEFAULT_LLM_TIER;
  const match = LLM_ROUTING_TIERS.find((option) => option.value === tier);
  return match ? match.label : tier;
};

export const MCP_TOOLS_FALLBACK = [
  { id: "google_search", name: "Google Search", icon: "search" },
  { id: "yahoo_finance", name: "Yahoo Finance", icon: "bar-chart-2" },
  { id: "sec_edgar", name: "SEC Edgar", icon: "file-text" },
  { id: "calculator", name: "Calculator", icon: "calculator" },
  { id: "twitter_scraper", name: "Twitter Scraper", icon: "twitter" }
];
