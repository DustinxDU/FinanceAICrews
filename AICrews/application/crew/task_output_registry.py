"""
Task Output Registry - Registry for task output schemas with metadata.

This module provides a central registry for looking up output schemas by key
and retrieving metadata for UI display (titles, descriptions, examples).
"""

from AICrews.observability.logging import get_logger
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from AICrews.schemas.task_output import (
    FinanceReportV1,
    TechnicalAnalysisV1,
    SentimentAnalysisV1,
)

logger = get_logger(__name__)


# Registry mapping schema_key -> (model_class, metadata)
_REGISTRY: Dict[str, Dict[str, Any]] = {
    "finance_report_v1": {
        "model": FinanceReportV1,
        "title": "Finance Report V1",
        "description": "Standard financial analysis report with recommendation, signal, and summary.",
        "category": "analysis",
        "recommended_guardrails": ["non_empty", "json_parseable"],
        "example": {
            "recommendation": "Buy AAPL with a 12-month target of $220",
            "signal": "bullish",
            "summary": "## Analysis\n\nApple shows strong momentum with revenue growth of 15% YoY...",
            "confidence": 0.85,
            "target_price": 220.0,
            "risk_factors": ["Regulatory pressure in EU", "Supply chain risks"],
        },
    },
    "technical_analysis_v1": {
        "model": TechnicalAnalysisV1,
        "title": "Technical Analysis V1",
        "description": "Technical analysis with indicators, support/resistance levels, and patterns.",
        "category": "analysis",
        "recommended_guardrails": ["non_empty", "json_parseable"],
        "example": {
            "ticker": "AAPL",
            "timeframe": "1D",
            "trend": "uptrend",
            "support_levels": [175.0, 170.0],
            "resistance_levels": [185.0, 190.0],
            "indicators": {"rsi": 65, "macd": "bullish_crossover"},
            "signal": "bullish",
            "summary": "Price above 50-day MA with bullish MACD crossover",
        },
    },
    "sentiment_analysis_v1": {
        "model": SentimentAnalysisV1,
        "title": "Sentiment Analysis V1",
        "description": "Sentiment analysis from news and social media sources.",
        "category": "analysis",
        "recommended_guardrails": ["non_empty", "json_parseable"],
        "example": {
            "ticker": "TSLA",
            "overall_sentiment": "positive",
            "sentiment_score": 0.65,
            "key_topics": ["Model Y sales", "FSD update"],
            "summary": "Positive sentiment driven by strong delivery numbers",
        },
    },
}


def resolve_output_model(schema_key: str) -> Optional[Type[BaseModel]]:
    """Resolve a schema key to its Pydantic model class.

    Args:
        schema_key: The registry key (e.g., 'finance_report_v1')

    Returns:
        The Pydantic model class, or None if not found
    """
    entry = _REGISTRY.get(schema_key)
    if entry:
        return entry["model"]
    return None


def list_output_schemas() -> List[Dict[str, Any]]:
    """List all registered output schemas with metadata.

    Returns:
        List of schema metadata dictionaries, each containing:
        - schema_key: The registry key
        - title: Human-readable title
        - description: Description of the schema
        - category: Category for grouping (e.g., 'analysis')
        - recommended_guardrails: List of recommended guardrail keys
        - example: Example output matching the schema
        - json_schema: The JSON Schema for frontend validation
    """
    result = []
    for schema_key, entry in _REGISTRY.items():
        model: Type[BaseModel] = entry["model"]
        result.append({
            "schema_key": schema_key,
            "title": entry.get("title", schema_key),
            "description": entry.get("description", ""),
            "category": entry.get("category", "general"),
            "recommended_guardrails": entry.get("recommended_guardrails", []),
            "example": entry.get("example", {}),
            "json_schema": model.model_json_schema(),
        })
    return result


def get_schema_metadata(schema_key: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific schema.

    Args:
        schema_key: The registry key

    Returns:
        Metadata dictionary or None if not found
    """
    entry = _REGISTRY.get(schema_key)
    if not entry:
        return None

    model: Type[BaseModel] = entry["model"]
    return {
        "schema_key": schema_key,
        "title": entry.get("title", schema_key),
        "description": entry.get("description", ""),
        "category": entry.get("category", "general"),
        "recommended_guardrails": entry.get("recommended_guardrails", []),
        "example": entry.get("example", {}),
        "json_schema": model.model_json_schema(),
    }


def register_output_schema(
    schema_key: str,
    model: Type[BaseModel],
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    recommended_guardrails: Optional[List[str]] = None,
    example: Optional[Dict[str, Any]] = None,
) -> None:
    """Register a new output schema.

    This allows dynamic registration of custom schemas at runtime.

    Args:
        schema_key: Unique key for the schema
        model: Pydantic model class
        title: Human-readable title
        description: Schema description
        category: Category for grouping
        recommended_guardrails: List of recommended guardrail keys
        example: Example output
    """
    if schema_key in _REGISTRY:
        logger.warning(f"Overwriting existing schema: {schema_key}")

    _REGISTRY[schema_key] = {
        "model": model,
        "title": title or schema_key,
        "description": description or model.__doc__ or "",
        "category": category,
        "recommended_guardrails": recommended_guardrails or [],
        "example": example or {},
    }
    logger.info(f"Registered output schema: {schema_key}")
