"""
Sentiment Analysis Tools - 情感分析工具集

基于规则和关键词的情感分析工具，用于分析新闻、报告、社交媒体等文本内容的情感倾向。
"""

import re
from AICrews.observability.logging import get_logger
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from crewai.tools import tool

logger = get_logger(__name__)

class SentimentType(Enum):
    """情感类型枚举"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"

@dataclass
class SentimentResult:
    """情感分析结果"""
    sentiment: str
    score: float  # -1 to 1
    confidence: float  # 0 to 1
    keywords: list
    aspects: Dict[str, float]  # 各方面情感

class SentimentEngine:
    """情感分析引擎
    
    基于金融领域词典和规则的情感分析
    """
    
    # 金融领域正面词汇
    BULLISH_KEYWORDS = {
        # 增长类
        "growth", "increase", "rise", "surge", "soar", "jump", "gain", "advance",
        "expand", "improve", "strengthen", "recover", "rebound",
        "beat", "exceed", "outperform", "record", "high",
        # 盈利类
        "profit", "earnings", "revenue", "margin", "dividend", "buyback",
        "cash flow", "cashflow",
        # 乐观类
        "optimistic", "confident", "positive", "strong", "robust", "healthy",
        "attractive", "opportunity", "upgrade", "target", "potential",
        # 创新类
        "innovation", "innovative", "breakthrough", "leader", "leading",
        # 订单类
        "order", "contract", "deal", "partnership", "collaboration",
    }
    
    # 金融领域负面词汇
    BEARISH_KEYWORDS = {
        # 下降类
        "decline", "decrease", "drop", "fall", "slump", "plunge", "tumble",
        "loss", "shrink", "contract", "weak", "weaken", "worsen", "deteriorate",
        "miss", "below", "underperform", "low", "cut", "reduce",
        # 风险类
        "risk", "threat", "challenge", "uncertainty", "concern",
        "worry", "anxiety", "fear", "volatility", "crash",
        "bubble", "recession", "downturn", "crisis",
        # 负面类
        "negative", "pessimistic", "trouble", "problem", "issue", "fail",
        "failure", "lawsuit", "investigation", "scandal", "fraud",
        # 债务类
        "debt", "liability", "default", "bankruptcy", "insolvency",
    }
    
    # 方面词典
    ASPECT_KEYWORDS = {
        "earnings": ["earnings", "profit", "revenue", "quarterly", "annual"],
        "guidance": ["guidance", "forecast", "outlook", "estimate", "target"],
        "valuation": ["valuation", "pe", "multiple", "expensive", "cheap", "overvalued", "undervalued"],
        "momentum": ["momentum", "trend", "direction", "strength", "weakness"],
        "news": ["news", "announcement", "report", "release"],
    }
    
    def __init__(self):
        self.bullish_pattern = self._build_pattern(self.BULLISH_KEYWORDS)
        self.bearish_pattern = self._build_pattern(self.BEARISH_KEYWORDS)
    
    def _build_pattern(self, keywords: set) -> re.Pattern:
        """构建正则表达式模式"""
        escaped = [re.escape(kw) for kw in keywords]
        return re.compile(r'\b(' + '|'.join(escaped) + r')\b', re.IGNORECASE)
    
    def _tokenize(self, text: str) -> list:
        """简单分词"""
        return re.findall(r'\b\w+\b', text.lower())
    
    def analyze_sentiment(self, text: str) -> SentimentResult:
        """分析文本情感"""
        if not text or not text.strip():
            return SentimentResult(
                sentiment=SentimentType.UNKNOWN.value,
                score=0.0,
                confidence=0.0,
                keywords=[],
                aspects={}
            )
        
        text_lower = text.lower()
        
        # 统计情感词
        bullish_count = 0
        bearish_count = 0
        found_keywords = []
        
        for match in self.bullish_pattern.finditer(text):
            bullish_count += 1
            keyword = match.group().lower()
            if keyword not in found_keywords:
                found_keywords.append(keyword)
        
        for match in self.bearish_pattern.finditer(text):
            bearish_count += 1
            keyword = match.group().lower()
            if keyword not in found_keywords:
                found_keywords.append(keyword)
        
        # 计算情感分数 (-1 到 1)
        total = bullish_count + bearish_count
        if total == 0:
            score = 0.0
        else:
            score = (bullish_count - bearish_count) / total
        
        # 确定情感类型
        if score > 0.2:
            sentiment = SentimentType.BULLISH.value if bullish_count > bearish_count else SentimentType.POSITIVE.value
        elif score < -0.2:
            sentiment = SentimentType.BEARISH.value if bearish_count > bullish_count else SentimentType.NEGATIVE.value
        else:
            sentiment = SentimentType.NEUTRAL.value
        
        # 计算置信度
        confidence = min(1.0, total / 10.0)  # 最多10个词达到最高置信度
        
        # 分析各方面情感
        aspects = self._analyze_aspects(text_lower)
        
        return SentimentResult(
            sentiment=sentiment,
            score=score,
            confidence=confidence,
            keywords=found_keywords,
            aspects=aspects
        )
    
    def _analyze_aspects(self, text: str) -> Dict[str, float]:
        """分析各方面情感"""
        aspects = {}
        
        for aspect, keywords in self.ASPECT_KEYWORDS.items():
            aspect_score = 0.0
            found = []
            
            for keyword in keywords:
                if keyword in text:
                    aspect_score += 1
                    found.append(keyword)
            
            if found:
                aspects[aspect] = aspect_score / len(found)
        
        return aspects

# 初始化全局实例
_sentiment_engine = SentimentEngine()

@tool("analyze_stock_sentiment")
def analyze_stock_sentiment(text: str) -> str:
    """
    Analyze the sentiment of a financial text (news, report, etc.).
    Returns sentiment type (bullish/bearish/neutral), score, and keywords.
    """
    try:
        result = _sentiment_engine.analyze_sentiment(text)
        
        # 格式化输出
        output = f"""
Sentiment Analysis Result:
- Sentiment: {result.sentiment.upper()}
- Score: {result.score:.2f} (Range: -1.0 to 1.0)
- Confidence: {result.confidence:.2f}
- Key Aspects:
"""
        for aspect, score in result.aspects.items():
            output += f"  - {aspect.title()}: {score:.2f}\n"
            
        if result.keywords:
            output += f"- Keywords Found: {', '.join(result.keywords[:10])}..."
            
        return output.strip()
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return f"Error: {str(e)}"
