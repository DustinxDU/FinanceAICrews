from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def extract_input_schema_defaults(input_schema: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Extract top-level defaults from a JSONSchema-like input_schema.

    We intentionally only read `properties.<name>.default` so UI-required inputs
    with defaults (e.g., timeframe) can be treated as optional at runtime when
    the caller omits them.
    """
    if not isinstance(input_schema, Mapping):
        return {}

    properties = input_schema.get("properties")
    if not isinstance(properties, Mapping):
        return {}

    defaults: Dict[str, Any] = {}
    for key, schema in properties.items():
        if not isinstance(key, str) or not isinstance(schema, Mapping):
            continue
        if "default" in schema:
            defaults[key] = schema.get("default")
    return defaults


def merge_crew_variables(
    *,
    input_schema: Optional[Mapping[str, Any]],
    default_variables: Optional[Mapping[str, Any]],
    variables: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Return effective variables (schema defaults + crew defaults + provided)."""
    schema_defaults = extract_input_schema_defaults(input_schema)
    crew_defaults = dict(default_variables or {})
    provided = dict(variables or {})
    return {**schema_defaults, **crew_defaults, **provided}

