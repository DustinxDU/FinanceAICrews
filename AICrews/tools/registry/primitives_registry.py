"""
Primitives Registry - Maps capability_ids to callable primitives

Provides a lazy-loaded registry of primitive tools (callables) that WrapperFactory
uses to generate skill wrappers. Primitives are the atomic building blocks:
- Builtin tools from AICrews/tools/*.py
- MCP tools (to be implemented)
- System utilities

Usage:
    registry = PrimitivesRegistry()
    primitives = registry.get_primitives()
    tool = WrapperFactory().generate_tool(skill, primitives=primitives)
"""

from AICrews.observability.logging import get_logger
from typing import Dict, Callable, Optional

logger = get_logger(__name__)


class PrimitivesRegistry:
    """
    Registry for primitive tools (capability_id → callable mapping).

    Lazy-loads builtin tools on first access. Future: support MCP tool loading.
    """

    def __init__(self):
        self._primitives: Optional[Dict[str, Callable]] = None
        self._loaded = False

    def get_primitives(self) -> Dict[str, Callable]:
        """
        Get all registered primitives as {capability_id: callable} dict.

        Lazy-loads on first call.

        Returns:
            Dict mapping capability_id to callable primitive tool
        """
        if not self._loaded:
            self._load_primitives()
            self._loaded = True

        return self._primitives or {}

    def _load_primitives(self) -> None:
        """Load all primitive tools from builtin sources."""
        self._primitives = {}

        # Load builtin tools
        self._load_builtin_tools()

        logger.info(f"PrimitivesRegistry loaded {len(self._primitives)} primitives")

    def _load_builtin_tools(self) -> None:
        """Load builtin tools from AICrews/tools/*.py"""
        try:
            # Import individual @tool decorated functions from tool modules
            # These are CrewAI Tool objects, can be used directly as primitives

            # Quant tools
            try:
                from AICrews.tools.quant_tools import get_technical_summary, calculate_indicator
                self._primitives['technical_summary'] = get_technical_summary
                self._primitives['indicator_calc'] = calculate_indicator
                logger.debug("Loaded quant tools")
            except ImportError as e:
                logger.warning(f"Failed to import quant tools: {e}")

            # Expression tools (for strategy evaluation)
            try:
                from AICrews.tools.expression_tools import evaluate_strategy
                self._primitives['strategy_eval'] = evaluate_strategy
                logger.debug("Loaded expression tools")
            except ImportError as e:
                logger.warning(f"Failed to import expression tools: {e}")

            # Sentiment tools
            try:
                from AICrews.tools.sentiment_tools import analyze_stock_sentiment
                self._primitives['sentiment_analysis'] = analyze_stock_sentiment
                logger.debug("Loaded sentiment tools")
            except ImportError as e:
                logger.warning(f"Failed to import sentiment tools: {e}")

            # Market data tools
            try:
                from AICrews.tools.market_data_tools import get_stock_price, get_stock_fundamentals, get_stock_news
                self._primitives['equity_quote'] = get_stock_price
                self._primitives['equity_fundamentals'] = get_stock_fundamentals
                self._primitives['equity_news'] = get_stock_news
                logger.debug("Loaded market data tools")
            except ImportError as e:
                logger.warning(f"Failed to import market data tools: {e}")

            logger.debug(f"Loaded {len(self._primitives)} builtin primitives")

        except Exception as e:
            logger.error(f"Error loading builtin primitives: {e}")

    def register_primitive(self, capability_id: str, callable_fn: Callable) -> None:
        """
        Manually register a primitive tool.

        Args:
            capability_id: Capability identifier (e.g., 'equity_quote')
            callable_fn: Callable function or tool
        """
        # Ensure primitives dict is initialized
        if self._primitives is None:
            self._primitives = {}

        self._primitives[capability_id] = callable_fn
        # Mark as loaded if not already (manual registration shouldn't trigger reload)
        if not self._loaded:
            self._loaded = True
        logger.debug(f"Registered primitive: {capability_id}")

    def unregister_primitive(self, capability_id: str) -> bool:
        """
        Remove a primitive from the registry.

        Args:
            capability_id: Capability identifier to remove

        Returns:
            True if removed, False if not found
        """
        if self._primitives and capability_id in self._primitives:
            del self._primitives[capability_id]
            logger.debug(f"Unregistered primitive: {capability_id}")
            return True
        return False

    def clear(self) -> None:
        """Clear all registered primitives."""
        if self._primitives:
            self._primitives.clear()
        self._loaded = False
        logger.debug("Cleared primitives registry")


# Global singleton instance
_registry_instance: Optional[PrimitivesRegistry] = None


def get_primitives_registry() -> PrimitivesRegistry:
    """
    Get the global primitives registry instance (singleton).

    Returns:
        Global PrimitivesRegistry instance
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = PrimitivesRegistry()
    return _registry_instance
