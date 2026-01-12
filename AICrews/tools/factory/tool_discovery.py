"""Tool discovery utilities for builtin providers."""

from AICrews.observability.logging import get_logger
from typing import List

logger = get_logger(__name__)


def discover_builtin_tools(provider, db) -> List[str]:
    """
    Discover available tools for a builtin provider.

    Uses ToolsFactory to validate that tools can be instantiated.
    Only returns tools that are actually available.

    Args:
        provider: The CapabilityProvider instance
        db: Database session (for accessing mappings)

    Returns:
        List of available tool names, sorted alphabetically
    """
    from AICrews.tools.factory.tools_factory import ToolsFactory, ToolSpec

    # Get all mappings for this provider
    mappings = provider.mappings

    if not mappings:
        logger.warning(f"No mappings found for provider {provider.provider_key}")
        return []

    factory = ToolsFactory()
    available_tools = []

    for mapping in mappings:
        if not mapping.raw_tool_name:
            continue

        try:
            # Create ToolSpec for validation
            spec = ToolSpec(
                provider_key=provider.provider_key,
                provider_type=provider.provider_type,
                raw_tool_name=mapping.raw_tool_name,
                capability_id=mapping.capability_id,
                connection_schema=provider.connection_schema or {}
            )

            # Try to instantiate the tool
            tool = factory.create_tool(spec)
            if tool is not None:
                available_tools.append(mapping.raw_tool_name)
                logger.debug(f"Discovered available tool: {mapping.raw_tool_name}")
            else:
                logger.warning(
                    f"Tool {mapping.raw_tool_name} not available "
                    f"(missing env vars or not implemented)"
                )
        except Exception as e:
            logger.error(f"Error discovering tool {mapping.raw_tool_name}: {e}")

    return sorted(available_tools)
