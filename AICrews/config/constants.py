"""
常量定义

存放项目中不随环境变化的固定值
"""

from typing import List, Dict, Any

# 支持的市场列表
MARKETS: List[Dict[str, str]] = [
    {"name": "🇺🇸 US Market (NASDAQ/NYSE)", "value": "US"},
    {"name": "🇨🇳 CN A-Share (SSE/SZSE)", "value": "CN"},
    {"name": "🇭🇰 HK Market (HKEX)", "value": "HK"},
    {"name": "🇸🇬 SG Market (SGX)", "value": "SG"},
    {"name": "🇯🇵 JP Market (TSE)", "value": "JP"},
    {"name": "🇬🇧 UK Market (LSE)", "value": "UK"},
    {"name": "🇮🇳 IN Market (NSE/BSE)", "value": "IN"},
    {"name": "🇨🇦 CA Market (TSX)", "value": "CA"},
    {"name": "🇦🇺 AU Market (ASX)", "value": "AU"},
    {"name": "🇩🇪 DE Market (XETRA)", "value": "DE"},
]

# 市场默认股票代码
MARKET_DEFAULT_TICKERS: Dict[str, str] = {
    "US": "NVDA",
    "CN": "600519",
    "HK": "0700",
    "SG": "D05",
    "JP": "7203",
    "UK": "SHEL",
    "IN": "RELIANCE",
    "CA": "RY",
    "AU": "BHP",
    "DE": "SAP",
}

# 辩论轮次选项
DEBATE_ROUNDS: List[Dict[str, Any]] = [
    {"name": "1 Round (Quick Check)", "value": 1},
    {"name": "2 Rounds (Balanced Debate)", "value": 2},
    {"name": "3 Rounds (Deep Research)", "value": 3},
    {"name": "5 Rounds (Stress Test)", "value": 5},
]

# 默认分析师配置
DEFAULT_ANALYSTS: List[str] = ["Fundamental", "Technical", "Sentiment"]

# 分析师选项（用于 CLI 展示）
ANALYST_CHOICES: List[Dict[str, Any]] = [
    {"name": "Fundamental Analyst (10-K/Financials)", "value": "Fundamental", "checked": True},
    {"name": "Technical Analyst (Price/Indicators)", "value": "Technical", "checked": True},
    {"name": "Sentiment Analyst (News/Social)", "value": "Sentiment", "checked": True},
]

# 报告类型
REPORT_TYPES: Dict[str, str] = {
    "analysis": "分析报告",
    "plan": "交易计划",
    "critique": "评论/辩论",
}

# Agent 角色与报告类型映射
AGENT_ROLE_TO_REPORT_TYPE: Dict[str, str] = {
    "Analyst": "analysis",
    "Trader": "plan",
    "Manager": "plan",
    "Researcher": "critique",
}

# 数据供应商配置
DATA_VENDORS: Dict[str, List[str]] = {
    "FREE": ["yfinance", "yahooquery", "akshare"],
    "PAID": ["fmp"],
}

# LLM 提供商显示名称
LLM_PROVIDER_DISPLAY_NAMES: Dict[str, str] = {
    "volcengine": "Volcengine (Doubao)",
    "zhipu_ai": "Zhipu AI (GLM)",
    "kimi_moonshot": "Kimi (Moonshot)",
    "qianwen_dashscope": "Qwen (DashScope)",
    "openai": "OpenAI",
}
