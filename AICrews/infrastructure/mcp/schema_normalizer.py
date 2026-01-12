"""
MCP Schema Normalizer

Monkey patches CrewAI's MCPClient to normalize tool schemas before they reach LLMs.

Problem:
  MCP servers (like OpenBB) return complex schemas with anyOf structures that confuse LLMs.
  Example: adjustment parameter has 3 different enum sets for different providers.

  Additionally, CrewAI's MCPToolWrapper expects `args_schema` (Pydantic BaseModel class),
  but MCP servers return `inputSchema` (JSON Schema dict). Without conversion, the enum
  constraints are never passed to the LLM.

Solution:
  Intercept MCPClient.list_tools() and:
  1. Normalize schemas: merge anyOf enum values into single enum
  2. Convert inputSchema (JSON Schema) to args_schema (Pydantic BaseModel)

This ensures LLMs receive clear, unambiguous parameter constraints with proper validation.
"""

import copy
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)

# Flag to prevent double-patching
_PATCHED = False

# Cache for dynamically created Enum classes to avoid recreation
_enum_cache: Dict[str, Type[Enum]] = {}


def _create_enum_class(name: str, values: List[str]) -> Type[Enum]:
    """Create a dynamic Enum class for parameter validation.

    Args:
        name: Name for the Enum class
        values: List of valid enum values

    Returns:
        Dynamic Enum class
    """
    # Filter out empty strings and None values
    valid_values = [v for v in values if v]
    if not valid_values:
        raise ValueError(f"No valid enum values for {name}")

    cache_key = f"{name}_{','.join(sorted(valid_values))}"
    if cache_key in _enum_cache:
        return _enum_cache[cache_key]

    # Create enum members: {"VALUE_NAME": "value_name", ...}
    members = {}
    for v in valid_values:
        # Convert value to valid Python identifier for enum member name
        member_name = v.upper().replace("-", "_").replace(".", "_").replace(" ", "_")
        # Handle empty member name (shouldn't happen after filtering, but be safe)
        if not member_name:
            member_name = f"VALUE_{len(members)}"
        # Handle leading digits
        if member_name[0].isdigit():
            member_name = f"V_{member_name}"
        # Handle duplicate member names
        if member_name in members:
            member_name = f"{member_name}_{len(members)}"
        members[member_name] = v

    enum_class = Enum(name, members, type=str)
    _enum_cache[cache_key] = enum_class
    return enum_class


def _json_type_to_python(json_type: str, prop_schema: Dict[str, Any], prop_name: str) -> Any:
    """Convert JSON Schema type to Python type annotation.

    Args:
        json_type: JSON Schema type string
        prop_schema: Full property schema (may contain enum, format, etc.)
        prop_name: Property name (used for enum class naming)

    Returns:
        Python type annotation
    """
    # Handle enum constraint - create Enum class for validation
    if "enum" in prop_schema:
        enum_values = prop_schema["enum"]
        if enum_values and isinstance(enum_values, list):
            # Filter out None values and convert to strings for enum class
            str_values = [str(v) for v in enum_values if v is not None]
            if str_values:
                enum_name = f"{prop_name.title().replace('_', '')}Enum"
                return _create_enum_class(enum_name, str_values)

    # Standard type mapping
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return type_map.get(json_type, Any)


def json_schema_to_pydantic(
    schema: Dict[str, Any],
    model_name: str = "DynamicModel"
) -> Type[BaseModel]:
    """Convert JSON Schema to Pydantic BaseModel class.

    This is the key function that bridges MCP's inputSchema (JSON Schema)
    to CrewAI's args_schema (Pydantic BaseModel).

    Args:
        schema: JSON Schema dictionary with properties, required, etc.
        model_name: Name for the generated Pydantic model

    Returns:
        Dynamically created Pydantic BaseModel class
    """
    if not schema or not isinstance(schema, dict):
        # Return empty model if no schema
        return create_model(model_name)

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    # Build field definitions for create_model
    field_definitions: Dict[str, Any] = {}

    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            continue

        # Determine Python type
        json_type = prop_schema.get("type", "string")
        python_type = _json_type_to_python(json_type, prop_schema, prop_name)

        # Get description and default
        description = prop_schema.get("description", f"Parameter: {prop_name}")
        default = prop_schema.get("default")

        # Build Field with constraints
        field_kwargs = {"description": description}

        # Add enum constraint info to description for LLM clarity
        if "enum" in prop_schema:
            enum_values = prop_schema["enum"]
            if enum_values:
                enum_str = ", ".join(f"'{v}'" for v in enum_values if v is not None)
                field_kwargs["description"] = f"{description} Valid values: [{enum_str}]"

        # Handle required vs optional
        if prop_name in required:
            if default is not None:
                field_definitions[prop_name] = (python_type, Field(default=default, **field_kwargs))
            else:
                field_definitions[prop_name] = (python_type, Field(..., **field_kwargs))
        else:
            # Optional field
            if default is not None:
                field_definitions[prop_name] = (Optional[python_type], Field(default=default, **field_kwargs))
            else:
                field_definitions[prop_name] = (Optional[python_type], Field(default=None, **field_kwargs))

    # Create and return the model
    try:
        model = create_model(model_name, **field_definitions)
        logger.debug(f"Created Pydantic model '{model_name}' with {len(field_definitions)} fields")
        return model
    except Exception as e:
        logger.warning(f"Failed to create Pydantic model '{model_name}': {e}")
        # Return basic model on failure
        return create_model(model_name)


def normalize_tool_schema(input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize MCP tool schema to be more LLM-friendly.
    
    Transformations:
    - anyOf with enum values → single enum with merged values
    - Missing default → use first enum value or infer reasonable default
    - Complex nested anyOf → simplified structure
    
    Args:
        input_schema: Original tool input schema from MCP server
        
    Returns:
        Normalized schema with simplified enum structures
    """
    if not input_schema or not isinstance(input_schema, dict):
        return input_schema
    
    # Deep copy to avoid modifying original
    schema = copy.deepcopy(input_schema)
    
    # Process properties
    properties = schema.get("properties", {})
    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            continue
        
        # Handle anyOf with enum values
        if "anyOf" in prop_schema:
            any_of = prop_schema["anyOf"]
            if isinstance(any_of, list):
                # Collect all enum values from anyOf branches
                all_enums = set()
                for branch in any_of:
                    if isinstance(branch, dict) and "enum" in branch:
                        if isinstance(branch["enum"], list):
                            all_enums.update(branch["enum"])
                
                # If we found enum values, replace anyOf with single enum
                if all_enums:
                    # Sort for consistency (prefer common defaults first)
                    # Handle non-string values safely
                    def sort_key(x):
                        if not isinstance(x, str):
                            return (2, str(x))  # Non-strings go last
                        x_lower = x.lower()
                        if x in ("splits_only", "none", "default", "auto"):
                            return (0, x)
                        if "split" in x_lower or "dividend" in x_lower:
                            return (1, x)
                        return (2, x)

                    sorted_enums = sorted(all_enums, key=sort_key)
                    
                    # Preserve existing default or use first enum value
                    default = prop_schema.get("default")
                    if not default or default not in all_enums:
                        default = sorted_enums[0]
                    
                    # Replace anyOf with single enum
                    prop_schema.pop("anyOf")
                    prop_schema["enum"] = sorted_enums
                    prop_schema["default"] = default
                    
                    # Enhance description if missing or vague
                    if "description" not in prop_schema or len(prop_schema.get("description", "")) < 20:
                        prop_schema["description"] = f"Valid values: {', '.join(sorted_enums)}. Default: {default}"
                    
                    logger.debug(
                        f"Normalized {prop_name}: merged {len(any_of)} anyOf branches into "
                        f"single enum with {len(sorted_enums)} values, default='{default}'"
                    )
    
    return schema


def normalize_tool_list(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize schemas for all tools in a list.

    This function does two critical things:
    1. Normalizes inputSchema (merges anyOf enums, sets defaults)
    2. Converts inputSchema to args_schema (Pydantic BaseModel) for CrewAI

    Args:
        tools: List of tool definitions from MCPClient.list_tools()

    Returns:
        List of tools with normalized input schemas AND args_schema (Pydantic BaseModel)
    """
    normalized = []
    for tool in tools:
        if not isinstance(tool, dict):
            normalized.append(tool)
            continue

        tool_copy = copy.deepcopy(tool)
        tool_name = tool.get("name", "UnknownTool")

        # Normalize inputSchema if present
        if "inputSchema" in tool and isinstance(tool["inputSchema"], dict):
            # Step 1: Normalize the JSON Schema (merge anyOf enums, etc.)
            normalized_schema = normalize_tool_schema(tool["inputSchema"])
            tool_copy["inputSchema"] = normalized_schema

            # Step 2: Convert to Pydantic BaseModel for CrewAI's args_schema
            # This is the KEY fix - CrewAI expects args_schema, not inputSchema
            model_name = f"{tool_name.replace('.', '_').replace('-', '_').title()}Args"
            try:
                args_schema = json_schema_to_pydantic(normalized_schema, model_name)
                tool_copy["args_schema"] = args_schema
                logger.debug(f"Created args_schema for tool '{tool_name}': {args_schema}")
            except Exception as e:
                logger.warning(f"Failed to create args_schema for tool '{tool_name}': {e}")

        normalized.append(tool_copy)

    return normalized


def patch_mcp_client():
    """Monkey patch CrewAI to normalize tool schemas and use them properly.

    This patches two places:
    1. MCPClient.list_tools() - to normalize schemas and create args_schema
    2. Agent._get_native_mcp_tools() - to USE the args_schema we created

    The second patch is critical because CrewAI's Agent ignores args_schema
    from list_tools() and re-converts using its own _json_schema_to_pydantic()
    which doesn't handle enum constraints properly.

    This should be called once during application startup before any
    agents are created.
    """
    global _PATCHED

    if _PATCHED:
        logger.debug("MCPClient already patched, skipping")
        return

    try:
        from crewai.mcp.client import MCPClient

        # Save original method
        original_list_tools = MCPClient.list_tools

        # Create wrapped method
        async def list_tools_with_normalization(self, use_cache: bool | None = None):
            """Wrapped list_tools that normalizes schemas."""
            # Call original method
            tools = await original_list_tools(self, use_cache=use_cache)

            # Normalize schemas
            normalized_tools = normalize_tool_list(tools)

            logger.info(f"Normalized schemas for {len(normalized_tools)} MCP tools")
            return normalized_tools

        # Replace method
        MCPClient.list_tools = list_tools_with_normalization

        logger.info("Successfully patched MCPClient.list_tools with schema normalizer")

    except Exception as e:
        logger.error(f"Failed to patch MCPClient: {e}", exc_info=True)
        raise

    # Patch 2: Make Agent use our args_schema instead of re-converting
    try:
        from crewai import Agent

        # Save original method
        original_json_schema_to_pydantic = Agent._json_schema_to_pydantic

        def json_schema_to_pydantic_with_enum_support(
            self, tool_name: str, json_schema: Dict[str, Any]
        ) -> type:
            """Enhanced _json_schema_to_pydantic that handles enum constraints.

            This replaces CrewAI's default implementation which ignores enum values.
            We first normalize the schema (merge anyOf enums) then convert properly.
            """
            # Normalize the schema first (handles anyOf with enums)
            normalized_schema = normalize_tool_schema(json_schema)

            # Use our converter which properly handles enums
            model_name = f"{tool_name.replace('-', '_').replace(' ', '_')}Schema"
            try:
                model = json_schema_to_pydantic(normalized_schema, model_name)
                logger.debug(f"Created enhanced args_schema for '{tool_name}' with enum support")
                return model
            except Exception as e:
                logger.warning(f"Enhanced schema conversion failed for '{tool_name}': {e}, falling back to original")
                return original_json_schema_to_pydantic(self, tool_name, json_schema)

        # Replace method
        Agent._json_schema_to_pydantic = json_schema_to_pydantic_with_enum_support

        logger.info("Successfully patched Agent._json_schema_to_pydantic with enum support")

    except Exception as e:
        logger.error(f"Failed to patch Agent._json_schema_to_pydantic: {e}", exc_info=True)
        # Don't raise - MCPClient patch is still useful

    _PATCHED = True


def is_patched() -> bool:
    """Check if MCPClient has been patched."""
    return _PATCHED
