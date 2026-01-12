"""
ToolsFactory - Unified factory for instantiating builtin CrewAI tools.

This factory handles creation of builtin tools only. MCP tools are NOT instantiated
here - they're passed as configs to CrewAI Agent(mcps=[...]).

Architecture:
- Builtin tools: Instantiated by ToolsFactory -> returned as BaseTool instances
- MCP tools: NOT instantiated -> passed as configs to CrewAI Agent

Provider Types:
- builtin_external: External API tools (DuckDuckGoSearchTool, SerperDevTool, ScrapeWebsiteTool, etc.)
- builtin_compute: Local computation tools (indicator_calc, strategy_eval)

Tool Selection:
- Uses raw_tool_name from database to select the correct tool implementation
- Provider priority determines which provider is selected for a capability
- No hardcoded tool selection in code - fully configuration-driven
"""

from AICrews.observability.logging import get_logger
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable

logger = get_logger(__name__)


@dataclass
class ToolSpec:
    """
    Specification for instantiating a builtin tool.

    Attributes:
        provider_key: Unique provider identifier (e.g., "builtin:serper")
        provider_type: Type of provider ("builtin_external", "builtin_compute")
        raw_tool_name: Original tool name used to select the tool implementation
        capability_id: Capability identifier (e.g., "web_search")
        connection_schema: Schema defining env requirements and config
    """
    provider_key: str
    provider_type: str
    raw_tool_name: str
    capability_id: str
    connection_schema: Dict[str, Any]


# =============================================================================
# Lazy Import Functions - Avoid import errors when tools not installed
# =============================================================================

def _import_duckduckgo_search():
    """Import pure DuckDuckGo search tool (free, no API key)."""
    from AICrews.tools.external_tools import duckduckgo_search
    return duckduckgo_search


def _import_serper_dev_tool():
    """Import fixed SerperDevTool with complete schema.

    Uses our fixed version that adds search_type to the schema,
    preventing LLM from hallucinating incorrect parameter formats.
    """
    from AICrews.tools.external_tools import create_fixed_serper_dev_tool
    tool = create_fixed_serper_dev_tool()
    if tool is None:
        # Fallback to original if our fix fails
        from crewai_tools import SerperDevTool
        return SerperDevTool()
    return tool


def _import_scrape_website_tool():
    """Import ScrapeWebsiteTool from crewai_tools."""
    from crewai_tools import ScrapeWebsiteTool
    return ScrapeWebsiteTool()


def _import_firecrawl_tool():
    """Import FirecrawlScrapeWebsiteTool from crewai_tools."""
    from crewai_tools import FirecrawlScrapeWebsiteTool
    return FirecrawlScrapeWebsiteTool()


def _import_scrape_element_tool():
    """Import ScrapeElementFromWebsiteTool from crewai_tools."""
    from crewai_tools import ScrapeElementFromWebsiteTool
    return ScrapeElementFromWebsiteTool()


def _import_website_search_tool():
    """Import WebsiteSearchTool from crewai_tools."""
    from crewai_tools import WebsiteSearchTool
    return WebsiteSearchTool()


def _import_code_interpreter_tool():
    """Import CodeInterpreterTool from crewai_tools."""
    from crewai_tools import CodeInterpreterTool
    return CodeInterpreterTool()


def _import_file_writer_tool():
    """Import FileWriterTool from crewai_tools."""
    from crewai_tools import FileWriterTool
    return FileWriterTool()


def _import_file_read_tool():
    """Import FileReadTool from crewai_tools."""
    from crewai_tools import FileReadTool
    return FileReadTool()


def _import_file_compressor_tool():
    """Import FileCompressorTool from crewai_tools (may not exist in all versions)."""
    from crewai_tools import FileCompressorTool
    return FileCompressorTool()


def _import_vision_tool():
    """Import VisionTool from crewai_tools."""
    from crewai_tools import VisionTool
    return VisionTool()


def _import_ocr_tool():
    """Import OCRTool from crewai_tools (may require pytesseract)."""
    from crewai_tools import OCRTool
    return OCRTool()


def _import_indicator_calc():
    """Import calculate_indicator tool from quant_tools."""
    from AICrews.tools.quant_tools import calculate_indicator
    return calculate_indicator


def _import_strategy_eval():
    """Import evaluate_strategy tool from expression_tools."""
    from AICrews.tools.expression_tools import evaluate_strategy
    return evaluate_strategy


# =============================================================================
# Report Generation Tools - For Reporter Agent
# =============================================================================

def _import_chart_generator():
    """Import chart_generator tool from report_tools."""
    from AICrews.tools.report_tools import chart_generator
    return chart_generator


def _import_table_formatter():
    """Import table_formatter tool from report_tools."""
    from AICrews.tools.report_tools import table_formatter
    return table_formatter


def _import_markdown_exporter():
    """Import markdown_exporter tool from report_tools."""
    from AICrews.tools.report_tools import markdown_exporter
    return markdown_exporter


def _import_pdf_exporter():
    """Import pdf_exporter tool from report_tools."""
    from AICrews.tools.report_tools import pdf_exporter
    return pdf_exporter


def _import_ppt_generator():
    """Import ppt_generator tool from report_tools."""
    from AICrews.tools.report_tools import ppt_generator
    return ppt_generator


def _import_infograph_generator():
    """Import infograph_generator tool from report_tools."""
    from AICrews.tools.report_tools import infograph_generator
    return infograph_generator


# =============================================================================
# Tool Name to Import Function Mapping - Configuration-Driven Tool Selection
# =============================================================================

# This mapping allows the database's raw_tool_name to control which tool is created.
# Provider priority determines which provider is selected for a capability.
# No hardcoded tool selection in code - fully configuration-driven.

BUILTIN_EXTERNAL_TOOL_MAP: Dict[str, Callable[[], Any]] = {
    # Web search tools (provider priority controls selection, not hardcoded fallback)
    "duckduckgo_search": _import_duckduckgo_search,  # Pure DuckDuckGo (free)
    "duckduckgo_search_tool": _import_duckduckgo_search,  # DB uses this name
    "serper_dev_tool": _import_serper_dev_tool,  # SerperDevTool (requires API key)
    # NOTE: "web_search" (hybrid Serper->DDG) removed - use pure tools via provider priority

    # Web scraping tools
    "scrape_website_tool": _import_scrape_website_tool,
    "firecrawl_tool": _import_firecrawl_tool,
    "scrape_element_from_website_tool": _import_scrape_element_tool,
    "website_search_tool": _import_website_search_tool,

    # Code & file tools
    "code_interpreter_tool": _import_code_interpreter_tool,
    "file_writer_tool": _import_file_writer_tool,
    "file_read_tool": _import_file_read_tool,
    "file_compressor_tool": _import_file_compressor_tool,

    # Vision & OCR tools
    "vision_tool": _import_vision_tool,
    "ocr_tool": _import_ocr_tool,
}

# Builtin compute tool mapping - local computation tools
BUILTIN_COMPUTE_TOOL_MAP: Dict[str, Callable[[], Any]] = {
    "indicator_calc": _import_indicator_calc,
    "strategy_eval": _import_strategy_eval,
    # Report generation tools (for Reporter Agent)
    "chart_generator": _import_chart_generator,
    "table_formatter": _import_table_formatter,
    "markdown_exporter": _import_markdown_exporter,
    "pdf_exporter": _import_pdf_exporter,
    "ppt_generator": _import_ppt_generator,
    "infograph_generator": _import_infograph_generator,
}

# Legacy tool name mappings for backward compatibility
# Maps old class-style names to new snake_case names
LEGACY_TOOL_NAME_MAP: Dict[str, str] = {
    "DuckDuckGoSearchTool": "duckduckgo_search",  # Maps to pure DuckDuckGo
    "SerperDevTool": "serper_dev_tool",
    "ScrapeWebsiteTool": "scrape_website_tool",
    "FirecrawlScrapeWebsiteTool": "firecrawl_tool",
    "ScrapeElementFromWebsiteTool": "scrape_element_from_website_tool",
    "WebsiteSearchTool": "website_search_tool",
    "CodeInterpreterTool": "code_interpreter_tool",
    "FileWriterTool": "file_writer_tool",
    "FileReadTool": "file_read_tool",
    "FileCompressorTool": "file_compressor_tool",
    "VisionTool": "vision_tool",
    "OCRTool": "ocr_tool",
}


class ToolsFactory:
    """
    Factory for creating builtin CrewAI tools.

    Uses raw_tool_name from database to select tool implementation.
    This replaces hardcoded if/elif chains with a mapping-based approach.

    Supports:
    - builtin_external: Web search, scraping, file, vision tools
    - builtin_compute: indicator_calc, strategy_eval

    Does NOT handle:
    - MCP tools (those are passed as configs to Agent)
    """

    def __init__(self):
        """Initialize the factory with empty custom tool registry."""
        self._custom_tools: Dict[str, type] = {}
        logger.info("ToolsFactory initialized")

    def register_custom(self, tool_name: str, tool_class: type) -> None:
        """
        Register a custom tool class.

        Args:
            tool_name: Name to register the tool under
            tool_class: Tool class (must be callable)

        Example:
            factory.register_custom("my_tool", MyCustomTool)
        """
        if not callable(tool_class):
            raise ValueError(f"Tool class {tool_class} must be callable")

        self._custom_tools[tool_name] = tool_class
        logger.info(f"Registered custom tool: {tool_name}")

    def check_env_requirements(self, connection_schema: Dict[str, Any]) -> bool:
        """
        Validate that all required environment variables are present.

        Args:
            connection_schema: Schema containing 'requires_env' list

        Returns:
            True if all required env vars are present, False otherwise
        """
        required_env = connection_schema.get("requires_env", [])
        if not required_env:
            return True

        missing = [var for var in required_env if not os.getenv(var)]
        if missing:
            logger.warning(
                f"Missing required environment variables: {missing}"
            )
            return False

        return True

    def create_tool(self, spec: ToolSpec) -> Optional[Any]:
        """
        Main tool creation method - dispatches to appropriate creator.

        Args:
            spec: ToolSpec containing all necessary information

        Returns:
            Instantiated tool instance or None if creation fails
        """
        # Check environment requirements first
        if not self.check_env_requirements(spec.connection_schema):
            logger.warning(
                f"Skipping tool {spec.raw_tool_name} due to missing env vars"
            )
            return None

        # Dispatch based on provider_type
        if spec.provider_type == "builtin_external":
            return self._create_builtin_external(spec)

        elif spec.provider_type == "builtin_compute":
            return self._create_builtin_compute(spec)

        elif spec.provider_type == "builtin":
            # Legacy "builtin" type - route based on raw_tool_name, NOT hardcoded capability_id
            if spec.raw_tool_name in BUILTIN_COMPUTE_TOOL_MAP:
                return self._create_builtin_compute(spec)
            elif spec.raw_tool_name in BUILTIN_EXTERNAL_TOOL_MAP:
                return self._create_builtin_external(spec)
            else:
                logger.warning(
                    f"Legacy 'builtin' provider with unknown raw_tool_name: {spec.raw_tool_name}. "
                    f"Consider migrating to 'builtin_external' or 'builtin_compute' type."
                )
                return None

        else:
            logger.error(f"Unknown provider type: {spec.provider_type}")
            return None

    def _create_builtin_external(self, spec: ToolSpec) -> Optional[Any]:
        """
        Create external API tools using raw_tool_name mapping.

        This method uses the raw_tool_name from the database to select
        the correct tool implementation, respecting provider priority.

        Args:
            spec: ToolSpec for the external tool

        Returns:
            Instantiated tool or None if creation fails
        """
        raw_tool_name = spec.raw_tool_name

        # Check for legacy tool name and map to new name
        if raw_tool_name in LEGACY_TOOL_NAME_MAP:
            mapped_name = LEGACY_TOOL_NAME_MAP[raw_tool_name]
            logger.debug(f"Mapped legacy tool name '{raw_tool_name}' to '{mapped_name}'")
            raw_tool_name = mapped_name

        # Check mapping first (configuration-driven)
        if raw_tool_name in BUILTIN_EXTERNAL_TOOL_MAP:
            try:
                return BUILTIN_EXTERNAL_TOOL_MAP[raw_tool_name]()
            except ImportError as e:
                logger.warning(f"Failed to import {raw_tool_name}: {e}")
                return None
            except Exception as e:
                logger.error(f"Failed to create {raw_tool_name}: {e}", exc_info=True)
                return None

        # Check custom tools registry (for user-registered tools)
        if raw_tool_name in self._custom_tools:
            try:
                return self._custom_tools[raw_tool_name]()
            except Exception as e:
                logger.error(f"Failed to create custom tool {raw_tool_name}: {e}")
                return None

        logger.warning(
            f"Unknown builtin_external tool: {raw_tool_name}. "
            f"Register it in BUILTIN_EXTERNAL_TOOL_MAP or via register_custom()."
        )
        return None

    def _create_builtin_compute(self, spec: ToolSpec) -> Optional[Any]:
        """
        Create local computation tools using raw_tool_name mapping.

        Args:
            spec: ToolSpec for the compute tool

        Returns:
            Instantiated tool or None if creation fails
        """
        raw_tool_name = spec.raw_tool_name

        if raw_tool_name in BUILTIN_COMPUTE_TOOL_MAP:
            try:
                return BUILTIN_COMPUTE_TOOL_MAP[raw_tool_name]()
            except ImportError as e:
                logger.warning(f"Failed to import {raw_tool_name}: {e}")
                return None
            except Exception as e:
                logger.error(f"Failed to create {raw_tool_name}: {e}", exc_info=True)
                return None

        # Check custom tools
        if raw_tool_name in self._custom_tools:
            try:
                return self._custom_tools[raw_tool_name]()
            except Exception as e:
                logger.error(f"Failed to create custom tool {raw_tool_name}: {e}")
                return None

        logger.warning(f"Unknown builtin_compute tool: {raw_tool_name}")
        return None

    def create_tools_batch(self, specs: List[ToolSpec]) -> List[Any]:
        """
        Create multiple tools in batch.

        Args:
            specs: List of ToolSpec instances

        Returns:
            List of successfully created tool instances (excludes None)
        """
        tools = []

        for spec in specs:
            tool = self.create_tool(spec)
            if tool is not None:
                tools.append(tool)
                logger.debug(
                    f"Created tool: {spec.raw_tool_name} "
                    f"(capability: {spec.capability_id})"
                )

        logger.info(
            f"Batch creation complete: {len(tools)}/{len(specs)} tools created"
        )
        return tools
