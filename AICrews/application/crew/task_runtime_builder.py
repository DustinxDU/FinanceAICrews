"""
Task Runtime Builder - Strategy layer for Task structured output configuration.

This module provides the central logic for deciding how to configure CrewAI
Task kwargs based on output_mode and provider capabilities:

- **native_pydantic/native_json**: Use CrewAI's built-in output_pydantic/output_json
  (only when provider supports function calling)
- **soft_pydantic/soft_json**: Don't use native output; use guardrails for parsing
  and validation (works with any provider)
- **raw**: No structured output, free-form text

The builder also handles:
- Automatic fallback (native -> soft when provider doesn't support)
- Schema resolution from registry
- Guardrail construction
- Diagnostics for observability
"""

from AICrews.observability.logging import get_logger
import os
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from AICrews.application.crew.task_output_spec import TaskOutputMode
from AICrews.application.crew.task_output_registry import resolve_output_model
from AICrews.application.crew.task_guardrails import build_guardrails

logger = get_logger(__name__)


def build_task_kwargs(
    *,
    t_data: Dict[str, Any],
    compiled_variables: Dict[str, Any],
    provider_capabilities: Dict[str, Any],
) -> Dict[str, Any]:
    """Build Task kwargs based on output spec and provider capabilities.

    This is the core strategy function that determines whether to use
    native structured output (output_pydantic/output_json) or soft
    structured output (guardrail-based parsing and validation).

    Args:
        t_data: Task data dict containing output spec fields:
            - name: Task name
            - output_mode: raw|native_json|native_pydantic|soft_json|soft_pydantic
            - output_schema_key: Registry key for schema
            - guardrail_keys: List of guardrail keys
            - guardrail_max_retries: Max retries on guardrail failure
            - strict_mode: If True, missing schema/guardrail raises error
        compiled_variables: Runtime variables (ticker, date, etc.)
        provider_capabilities: Provider info (supports_function_calling, etc.)

    Returns:
        Dict of kwargs to pass to CrewAI Task(...), including:
        - output_pydantic/output_json (for native modes)
        - guardrails (list of callables/strings)
        - guardrail_max_retries
        - _diagnostics (internal metadata for tracking)

    Raises:
        ValueError: If strict_mode=True and schema_key is unknown
    """
    task_name = t_data.get("name", "unknown")
    output_mode_str = t_data.get("output_mode", "raw") or "raw"
    schema_key = t_data.get("output_schema_key")
    guardrail_keys = t_data.get("guardrail_keys", []) or []
    max_retries = t_data.get("guardrail_max_retries", 3) or 3
    strict_mode = t_data.get("strict_mode", False) or False

    # Parse output mode
    try:
        output_mode = TaskOutputMode(output_mode_str)
    except ValueError:
        logger.warning(f"Invalid output_mode '{output_mode_str}', defaulting to raw")
        output_mode = TaskOutputMode.RAW

    # Initialize result
    kwargs: Dict[str, Any] = {}
    diagnostics: Dict[str, Any] = {
        "requested_mode": output_mode.value,
        "effective_mode": output_mode.value,
        "schema_key": schema_key,
        "schema_resolved": False,
        "degraded": False,
        "warnings": [],
    }

    # Handle raw mode - no structured output
    if output_mode == TaskOutputMode.RAW:
        effective_guardrail_keys = list(guardrail_keys)

        default_raw_guardrails = os.getenv("FAIC_DEFAULT_RAW_TASK_GUARDRAILS", "1")
        enable_defaults = str(default_raw_guardrails).strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )
        if enable_defaults:
            for key in ("non_empty", "not_fence_only"):
                if key not in effective_guardrail_keys:
                    effective_guardrail_keys.append(key)

        if effective_guardrail_keys:
            kwargs["guardrails"] = build_guardrails(
                effective_guardrail_keys, compiled_variables, task_name
            )
            kwargs["guardrail_max_retries"] = max_retries
        kwargs["_diagnostics"] = diagnostics
        return kwargs

    # Resolve schema for non-raw modes
    model_class: Optional[Type[BaseModel]] = None
    if schema_key:
        model_class = resolve_output_model(schema_key)
        diagnostics["schema_resolved"] = model_class is not None

    if model_class is None:
        if strict_mode:
            raise ValueError(
                f"Unknown output schema '{schema_key}' for task '{task_name}'"
            )
        else:
            logger.warning(
                f"Unknown schema '{schema_key}' for task '{task_name}', "
                f"degrading to raw mode"
            )
            diagnostics["effective_mode"] = "raw"
            diagnostics["degraded"] = True
            diagnostics["warnings"].append(f"Schema '{schema_key}' not found")
            kwargs["_diagnostics"] = diagnostics
            return kwargs

    # Check provider capability for native modes
    # Native modes require BOTH function_calling AND json_schema support
    supports_function_calling = provider_capabilities.get(
        "supports_function_calling", False
    )
    supports_json_schema = provider_capabilities.get("supports_json_schema", False)
    supports_native = supports_function_calling and supports_json_schema

    # Determine effective mode based on capabilities
    effective_mode = output_mode

    if TaskOutputMode.is_native(output_mode) and not supports_native:
        if strict_mode:
            missing = []
            if not supports_function_calling:
                missing.append("function_calling")
            if not supports_json_schema:
                missing.append("json_schema")
            raise ValueError(
                f"Provider lacks required capabilities {missing} for "
                f"{output_mode.value} mode on task '{task_name}'"
            )
        else:
            # Degrade native -> soft
            if output_mode == TaskOutputMode.NATIVE_PYDANTIC:
                effective_mode = TaskOutputMode.SOFT_PYDANTIC
            else:
                effective_mode = TaskOutputMode.SOFT_JSON

            reason = []
            if not supports_function_calling:
                reason.append("function_calling")
            if not supports_json_schema:
                reason.append("json_schema")

            logger.info(
                f"Degrading {output_mode.value} -> {effective_mode.value} "
                f"for task '{task_name}' (provider lacks {', '.join(reason)})"
            )
            diagnostics["effective_mode"] = effective_mode.value
            diagnostics["degraded"] = True
            diagnostics["warnings"].append(
                f"Provider doesn't support {', '.join(reason)}, using soft mode"
            )

    # Build kwargs based on effective mode
    if effective_mode == TaskOutputMode.NATIVE_PYDANTIC:
        kwargs["output_pydantic"] = model_class
        # Native modes can still have guardrails for extra validation
        if guardrail_keys:
            kwargs["guardrails"] = build_guardrails(
                guardrail_keys, compiled_variables, task_name
            )
            kwargs["guardrail_max_retries"] = max_retries

    elif effective_mode == TaskOutputMode.NATIVE_JSON:
        kwargs["output_json"] = model_class
        if guardrail_keys:
            kwargs["guardrails"] = build_guardrails(
                guardrail_keys, compiled_variables, task_name
            )
            kwargs["guardrail_max_retries"] = max_retries

    elif effective_mode == TaskOutputMode.SOFT_PYDANTIC:
        # Soft pydantic: use guardrails for parsing + validation
        # Auto-prepend robust JSON extraction and parsing guardrails
        effective_guardrail_keys = [
            "json_no_fence",
            "json_extract_object",
            "json_parseable",
        ]
        # Add user-specified guardrails
        effective_guardrail_keys.extend(guardrail_keys)
        # Auto-add pydantic_validate guardrail if not already present
        pydantic_validate_key = f"pydantic_validate:{schema_key}"
        if pydantic_validate_key not in effective_guardrail_keys:
            effective_guardrail_keys.append(pydantic_validate_key)

        kwargs["guardrails"] = build_guardrails(
            effective_guardrail_keys, compiled_variables, task_name
        )
        kwargs["guardrail_max_retries"] = max_retries

    elif effective_mode == TaskOutputMode.SOFT_JSON:
        # Soft JSON: use guardrails for parsing + validation
        # Auto-prepend robust JSON extraction and parsing guardrails
        effective_guardrail_keys = [
            "json_no_fence",
            "json_extract_object",
            "json_parseable",
        ]
        # Add user-specified guardrails
        effective_guardrail_keys.extend(guardrail_keys)
        # Auto-add json_validate guardrail if not already present
        json_validate_key = f"json_validate:{schema_key}"
        if json_validate_key not in effective_guardrail_keys:
            effective_guardrail_keys.append(json_validate_key)

        kwargs["guardrails"] = build_guardrails(
            effective_guardrail_keys, compiled_variables, task_name
        )
        kwargs["guardrail_max_retries"] = max_retries

    kwargs["_diagnostics"] = diagnostics
    return kwargs


def get_provider_capabilities(
    provider_key: str,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Get capabilities for a provider/model combination.

    Uses compatibility_service as single source of truth for function calling
    support (avoiding split-brain). Other capabilities read from ConfigStore.

    Args:
        provider_key: Provider key (e.g., 'openai', 'anthropic', 'volcengine')
        model_name: Optional model name for model-specific capabilities

    Returns:
        Dict of capabilities including:
        - supports_function_calling: bool
        - supports_json_schema: bool (OpenAI Structured Outputs)
        - supports_json_mode: bool
    """
    from AICrews.llm.core.config_store import get_config_store
    from AICrews.llm.services.compatibility_service import (
        get_compatibility_service,
        FunctionCallingSupport,
    )

    # Single source of truth for function calling support
    compat = get_compatibility_service()
    fc_support, _ = compat.check_function_calling_support(provider_key, model_name)
    supports_function_calling = fc_support in (
        FunctionCallingSupport.FULL,
        FunctionCallingSupport.PARTIAL,
    )

    # Get other capabilities from ConfigStore
    store = get_config_store()
    provider_config = store.get_provider(provider_key)

    if provider_config and provider_config.capabilities:
        return {
            "supports_function_calling": supports_function_calling,
            "supports_json_schema": provider_config.capabilities.supports_json_schema,
            "supports_json_mode": provider_config.capabilities.supports_json_mode,
        }

    # Fallback if provider not found or no capabilities defined
    logger.warning(
        f"Provider '{provider_key}' not found in config or missing capabilities, "
        f"assuming no json_schema/json_mode support"
    )
    return {
        "supports_function_calling": supports_function_calling,
        "supports_json_schema": False,
        "supports_json_mode": False,
    }
