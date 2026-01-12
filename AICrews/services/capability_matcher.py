"""
Capability Matcher Service - Intelligent tool to capability mapping.

This service implements a multi-dimensional matching engine to suggest
capability mappings for discovered tools from MCP providers.

Matching dimensions:
- Tool name pattern matching (weight: 0.4)
- Tool description semantic matching (weight: 0.3)
- Parameter schema matching (weight: 0.2)
- Historical mapping data (weight: 0.1)
"""
from typing import List, Dict, Optional
import re
from difflib import SequenceMatcher

from AICrews.capabilities.taxonomy import CAPABILITY_METADATA, ALL_CAPABILITIES


class CapabilityMatcher:
    """
    Intelligent matcher for suggesting capability mappings.

    Confidence thresholds:
    - > 0.9: Auto-apply (high confidence)
    - 0.7-0.9: Suggest (medium confidence)
    - < 0.7: Show but don't recommend
    """

    # Pattern-based rules for tool name matching
    TOOL_NAME_PATTERNS = {
        # Equity data patterns
        r"stock.*info|quote|price|spot": "equity_quote",
        r"stock.*(hist|history|ohlc|kline|candle)": "equity_history",
        r"stock.*(fundamental|overview|profile|company)": "equity_fundamentals",
        r"stock.*(financial|balance|income|cash.?flow|statement)": "equity_financials",
        r"stock.*(news|article|headline)": "equity_news",

        # Market data patterns
        r"(macro|economic|gdp|cpi|inflation)": "macro_indicators",
        r"(intraday|minute|tick)": "equity_intraday",
        r"(orderbook|depth|bid.*ask)": "equity_orderbook",
        r"(dividend|split|corporate.*action)": "equity_corporate_actions",
        r"(holder|ownership|shareholder|institution)": "equity_ownership",
        r"(earning|eps|guidance)": "equity_earnings",
        r"(analyst|rating|target|recommendation)": "equity_analyst_research",

        # Index & sector patterns
        r"(index|indices).*hist": "index_history",
        r"(index|indices).*(constituent|component|weight)": "index_constituents",
        r"(sector|industry|classification)": "sector_industry",

        # Other asset classes
        r"(fund.*flow|capital.*flow|money.*flow)": "fund_flow",
        r"(sentiment|fear.*greed|emotion)": "sentiment",
        r"(etf|fund|mutual)": "funds_etfs",
        r"(bond|convertible|fixed.*income)": "bonds",
        r"(option|call|put)": "options",
        r"(crypto|bitcoin|ethereum)": "crypto",
        r"(forex|currency|exchange.*rate|fx)": "forex",
        r"(future|forward|contract)": "futures",
        r"(esg|environmental|social|governance)": "esg",

        # Compute patterns
        r"(indicator|technical|rsi|macd|ma|ema|moving.*average|sma)": "indicator_calc",
        r"(strategy|backtest|evaluate|signal)": "strategy_eval",

        # External IO patterns
        r"(search|query|web.*search)": "web_search",
        r"(scrape|extract|crawl)": "web_scrape",
        r"(browse|navigate|render)": "web_browse",
    }

    # Keyword mapping for description matching
    DESCRIPTION_KEYWORDS = {
        "equity_quote": ["price", "quote", "snapshot", "real-time", "delayed"],
        "equity_history": ["historical", "ohlc", "candlestick", "kline", "daily"],
        "equity_fundamentals": ["fundamental", "overview", "metrics", "valuation"],
        "equity_financials": ["financial", "statement", "balance", "income", "cash flow"],
        "equity_news": ["news", "article", "headline", "press"],
        "macro_indicators": ["gdp", "cpi", "inflation", "unemployment", "interest rate"],
        "indicator_calc": ["indicator", "technical", "rsi", "macd", "moving average"],
        "strategy_eval": ["strategy", "backtest", "signal", "evaluate"],
        "web_search": ["search", "query", "find"],
        "web_scrape": ["scrape", "extract", "parse"],
    }

    def __init__(self):
        """Initialize matcher with compiled patterns."""
        self.compiled_patterns = {
            pattern: cap_id
            for pattern, cap_id in self.TOOL_NAME_PATTERNS.items()
        }

    def suggest_mappings(
        self,
        discovered_tools: List[Dict[str, str]],
        provider_key: Optional[str] = None
    ) -> List[Dict]:
        """
        Suggest capability mappings for discovered tools.

        Args:
            discovered_tools: List of dicts with 'name', 'description', 'inputSchema'
            provider_key: Optional provider key for historical matching

        Returns:
            List of mapping suggestions with confidence scores.
            Only returns suggestions with valid capability IDs from taxonomy.

        Example:
            [
                {
                    "tool_name": "stock_zh_a_spot_em",
                    "capability_id": "equity_quote",
                    "confidence": 0.92,
                    "action": "suggest",
                    "reason": "Pattern match: stock.*spot"
                },
                ...
            ]
        """
        suggestions = []

        for tool in discovered_tools:
            tool_name = tool.get("name", "")
            tool_desc = tool.get("description", "")
            tool_schema = tool.get("inputSchema", {})

            # Calculate scores from different dimensions
            name_score, name_cap = self._match_by_name(tool_name)
            desc_score, desc_cap = self._match_by_description(tool_desc)
            schema_score, schema_cap = self._match_by_schema(tool_schema)

            # Weighted combination - accumulate scores for same capability
            # IMPORTANT: Only consider capabilities that are in the taxonomy
            candidates = {}
            total_weight = 0.0

            if name_score > 0 and name_cap in ALL_CAPABILITIES:
                candidates[name_cap] = candidates.get(name_cap, 0) + name_score * 0.6  # Increased weight
                total_weight += 0.6
            if desc_score > 0 and desc_cap in ALL_CAPABILITIES:
                candidates[desc_cap] = candidates.get(desc_cap, 0) + desc_score * 0.3
                total_weight += 0.3
            if schema_score > 0 and schema_cap in ALL_CAPABILITIES:
                candidates[schema_cap] = candidates.get(schema_cap, 0) + schema_score * 0.1
                total_weight += 0.1

            # Get best match and normalize by actual total weight used
            if candidates:
                best_cap = max(candidates, key=candidates.get)
                raw_confidence = candidates[best_cap]

                # Normalize to 0-1 range based on actual contributing dimensions
                if total_weight > 0:
                    confidence = min(raw_confidence / total_weight, 1.0)
                else:
                    confidence = raw_confidence

                # Determine action based on confidence
                if confidence >= 0.9:
                    action = "auto"
                elif confidence >= 0.7:
                    action = "suggest"
                else:
                    action = "show"

                # Determine reason
                reason = self._get_match_reason(tool_name, tool_desc, best_cap)

                suggestions.append({
                    "tool_name": tool_name,
                    "capability_id": best_cap,
                    "confidence": round(confidence, 2),
                    "action": action,
                    "reason": reason
                })

        return suggestions

    def _match_by_name(self, tool_name: str) -> tuple[float, Optional[str]]:
        """
        Match tool by name patterns.

        Returns:
            (score, capability_id) where score is 0-1
        """
        tool_name_lower = tool_name.lower()

        # Try pattern matching first (high confidence)
        for pattern, cap_id in self.compiled_patterns.items():
            if re.search(pattern, tool_name_lower):
                return (0.95, cap_id)

        # Try fuzzy matching against capability IDs (medium confidence)
        best_ratio = 0.0
        best_cap = None

        for cap_id in ALL_CAPABILITIES:
            # Compare against capability_id (with underscores)
            ratio = SequenceMatcher(None, tool_name_lower, cap_id).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_cap = cap_id

        if best_ratio >= 0.5:
            return (best_ratio * 0.8, best_cap)  # Scale down fuzzy matches

        return (0.0, None)

    def _match_by_description(self, description: str) -> tuple[float, Optional[str]]:
        """
        Match tool by description keywords.

        Returns:
            (score, capability_id) where score is 0-1
        """
        if not description:
            return (0.0, None)

        desc_lower = description.lower()
        best_score = 0.0
        best_cap = None

        for cap_id, keywords in self.DESCRIPTION_KEYWORDS.items():
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in desc_lower)
            score = min(matches / len(keywords), 1.0)  # Normalize to 0-1

            if score > best_score:
                best_score = score
                best_cap = cap_id

        return (best_score, best_cap)

    def _match_by_schema(self, schema: Dict) -> tuple[float, Optional[str]]:
        """
        Match tool by parameter schema.

        Returns:
            (score, capability_id) where score is 0-1
        """
        if not schema or "properties" not in schema:
            return (0.0, None)

        properties = schema.get("properties", {})
        param_names = set(properties.keys())

        # Common parameter patterns
        if "symbol" in param_names or "ticker" in param_names or "stock_code" in param_names:
            # Likely equity-related
            if "start_date" in param_names or "end_date" in param_names:
                return (0.6, "equity_history")
            else:
                return (0.6, "equity_quote")

        if "indicator" in param_names or "period" in param_names:
            return (0.6, "indicator_calc")

        if "query" in param_names or "keyword" in param_names:
            return (0.5, "web_search")

        return (0.0, None)

    def _get_match_reason(self, tool_name: str, description: str, cap_id: str) -> str:
        """Generate human-readable reason for the match."""
        tool_name_lower = tool_name.lower()

        # Check if pattern match
        for pattern, matched_cap in self.compiled_patterns.items():
            if matched_cap == cap_id and re.search(pattern, tool_name_lower):
                # Extract the pattern part that matched
                match = re.search(pattern, tool_name_lower)
                if match:
                    return f"Pattern match: '{match.group()}' → {cap_id}"

        # Check if description match
        if cap_id in self.DESCRIPTION_KEYWORDS:
            keywords = self.DESCRIPTION_KEYWORDS[cap_id]
            desc_lower = description.lower() if description else ""
            matched_kws = [kw for kw in keywords if kw in desc_lower]
            if matched_kws:
                return f"Description contains: {', '.join(matched_kws[:2])}"

        # Fuzzy match
        return f"Fuzzy match with {cap_id}"


# Singleton instance
_matcher = None


def get_capability_matcher() -> CapabilityMatcher:
    """Get singleton capability matcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = CapabilityMatcher()
    return _matcher
