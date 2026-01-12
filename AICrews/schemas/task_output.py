"""
Task Output Schemas - Pydantic models for structured task outputs.

This module defines the schema contracts that Tasks can produce when
configured with output_mode != 'raw'. These schemas are registered
in task_output_registry.py for lookup by schema_key.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    """Trading signal type for financial analysis."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class FinanceReportV1(BaseModel):
    """Standard financial analysis report output.

    This is the primary structured output format for financial analysis tasks.
    It captures the key recommendation, signal strength, and detailed summary.
    """

    recommendation: str = Field(
        ...,
        min_length=1,
        description="Actionable recommendation (e.g., 'Buy AAPL with target $200')",
    )
    signal: SignalType = Field(
        ...,
        description="Trading signal: bullish, bearish, neutral, strong_buy, strong_sell",
    )
    summary: str = Field(
        ...,
        min_length=10,
        description="Detailed analysis summary in markdown format",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1",
    )
    target_price: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Target price if applicable",
    )
    risk_factors: Optional[List[str]] = Field(
        default=None,
        description="List of identified risk factors",
    )
    sources: Optional[List[str]] = Field(
        default=None,
        description="List of data sources used in the analysis",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "recommendation": "Buy AAPL with a 12-month target of $220",
                    "signal": "bullish",
                    "summary": "## Analysis\n\nApple shows strong momentum...",
                    "confidence": 0.85,
                    "target_price": 220.0,
                    "risk_factors": ["Regulatory pressure in EU", "Supply chain risks"],
                    "sources": ["SEC filings", "Earnings transcript Q4 2025"],
                }
            ]
        }
    }


class TechnicalAnalysisV1(BaseModel):
    """Technical analysis output with indicators and chart patterns."""

    ticker: str = Field(..., description="Stock ticker symbol")
    timeframe: str = Field(
        ..., description="Analysis timeframe (e.g., '1D', '1W', '1M')"
    )
    trend: str = Field(
        ..., description="Current trend: uptrend, downtrend, sideways"
    )
    support_levels: List[float] = Field(
        default_factory=list, description="Key support price levels"
    )
    resistance_levels: List[float] = Field(
        default_factory=list, description="Key resistance price levels"
    )
    indicators: dict = Field(
        default_factory=dict,
        description="Technical indicators (RSI, MACD, etc.)",
    )
    patterns: Optional[List[str]] = Field(
        default=None, description="Identified chart patterns"
    )
    signal: SignalType = Field(..., description="Overall technical signal")
    summary: str = Field(..., description="Technical analysis summary")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ticker": "AAPL",
                    "timeframe": "1D",
                    "trend": "uptrend",
                    "support_levels": [175.0, 170.0],
                    "resistance_levels": [185.0, 190.0],
                    "indicators": {"rsi": 65, "macd": "bullish_crossover"},
                    "patterns": ["cup_and_handle"],
                    "signal": "bullish",
                    "summary": "Price above 50-day MA with bullish MACD crossover",
                }
            ]
        }
    }


class SentimentAnalysisV1(BaseModel):
    """Sentiment analysis output from news and social media."""

    ticker: str = Field(..., description="Stock ticker symbol")
    overall_sentiment: str = Field(
        ..., description="Overall sentiment: positive, negative, neutral, mixed"
    )
    sentiment_score: float = Field(
        ..., ge=-1.0, le=1.0, description="Sentiment score from -1 to 1"
    )
    news_sentiment: Optional[float] = Field(
        default=None, ge=-1.0, le=1.0, description="News-specific sentiment"
    )
    social_sentiment: Optional[float] = Field(
        default=None, ge=-1.0, le=1.0, description="Social media sentiment"
    )
    key_topics: List[str] = Field(
        default_factory=list, description="Key topics mentioned"
    )
    notable_events: Optional[List[str]] = Field(
        default=None, description="Notable events affecting sentiment"
    )
    summary: str = Field(..., description="Sentiment analysis summary")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ticker": "TSLA",
                    "overall_sentiment": "positive",
                    "sentiment_score": 0.65,
                    "news_sentiment": 0.7,
                    "social_sentiment": 0.6,
                    "key_topics": ["Model Y sales", "FSD update", "Earnings beat"],
                    "notable_events": ["Q4 delivery numbers exceeded expectations"],
                    "summary": "Positive sentiment driven by strong delivery numbers",
                }
            ]
        }
    }
