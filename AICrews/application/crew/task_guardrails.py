"""
Task Guardrails - Deterministic guardrail functions for Task outputs.

This module provides guardrail callables that follow CrewAI's expected
return semantics:
- Success: return (True, task_output) - unchanged output
- Failure: return (False, error_message) - string feedback for retry

IMPORTANT: Guardrails must NEVER raise exceptions. All errors must be
caught internally and returned as (False, error_message) to trigger
CrewAI's built-in retry mechanism.
"""

import json
import re
from typing import Any, Callable, Dict, List, Tuple, Union

from crewai.tasks.task_output import TaskOutput

from AICrews.application.crew.task_output_registry import resolve_output_model
from AICrews.observability.logging import get_logger

logger = get_logger(__name__)

# Type alias for guardrail return value
GuardrailResult = Tuple[bool, Union[TaskOutput, str]]

# Type alias for guardrail callable
GuardrailCallable = Callable[[TaskOutput], GuardrailResult]


def _wrap_guardrail(
    fn: Callable[[TaskOutput], GuardrailResult],
    name: str,
) -> GuardrailCallable:
    """Wrap a guardrail function to catch any exceptions.

    This ensures guardrails NEVER raise - any exception becomes
    (False, error_message) to trigger CrewAI retry.
    """
    def wrapper(task_output: TaskOutput) -> GuardrailResult:
        try:
            return fn(task_output)
        except Exception as e:
            logger.exception(f"Guardrail '{name}' raised exception")
            return (False, f"Guardrail '{name}' error: {str(e)}")

    wrapper.__name__ = f"guardrail_{name}"
    return wrapper


# =============================================================================
# Deterministic Guardrail Implementations
# =============================================================================


def _guardrail_non_empty(task_output: TaskOutput) -> GuardrailResult:
    """Check that output is not empty."""
    raw = getattr(task_output, "raw", "") or ""
    if not raw.strip():
        return (False, "Output is empty. Please provide a substantive response.")
    return (True, task_output)


def _guardrail_not_fence_only(task_output: TaskOutput) -> GuardrailResult:
    """Reject outputs that are only a markdown code fence marker.

    This is a pragmatic guardrail for a common tool-agent failure mode where
    the model returns only the opening fence (```), often due to stop-sequence
    truncation or malformed formatting.
    """
    raw = getattr(task_output, "raw", "") or ""
    stripped = raw.strip()

    # Exactly a fence, or a fence with only a language tag (no content).
    if stripped == "```" or re.fullmatch(r"```[a-zA-Z0-9_-]*", stripped):
        return (
            False,
            "Output was only a markdown code fence marker (```), which is invalid. "
            "Please provide the full answer content (markdown is fine), and do not return only ```.",
        )

    return (True, task_output)


def _guardrail_json_parseable(task_output: TaskOutput) -> GuardrailResult:
    """Check that output is valid JSON."""
    raw = getattr(task_output, "raw", "") or ""
    try:
        json.loads(raw)
        return (True, task_output)
    except json.JSONDecodeError as e:
        return (
            False,
            f"Output is not valid JSON: {e}. "
            f"Please respond with properly formatted JSON only."
        )


def _guardrail_json_no_fence(task_output: TaskOutput) -> GuardrailResult:
    """Clean markdown code fences from JSON output.

    If fences are detected, returns (True, cleaned_string) which tells
    CrewAI to replace the raw output. If no fences, returns unchanged.
    """
    raw = getattr(task_output, "raw", "") or ""

    # Pattern to match ```json ... ``` or ``` ... ```
    fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    match = re.search(fence_pattern, raw, re.DOTALL)

    if match:
        cleaned = match.group(1).strip()
        logger.debug(f"Cleaned JSON fence from output")
        return (True, cleaned)

    return (True, task_output)


def _guardrail_json_extract_object(task_output: TaskOutput) -> GuardrailResult:
    """Extract first top-level JSON object from text.

    This is more aggressive than json_no_fence. It:
    1. Removes markdown fences if present
    2. If still not valid JSON, tries to regex-extract first {...} object
    3. Returns (True, extracted_json_string) on success
    4. Returns (False, reason) to trigger retry on failure

    Never raises exceptions.
    """
    raw = getattr(task_output, "raw", "") or ""

    # Step 1: Remove markdown fences
    fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    match = re.search(fence_pattern, raw, re.DOTALL)
    if match:
        raw = match.group(1).strip()

    # Step 2: Try to parse as-is
    try:
        json.loads(raw)
        # Already valid JSON, return as-is
        return (True, raw)
    except json.JSONDecodeError:
        pass

    # Step 3: Try to extract first {...} object using regex
    # Pattern: find first { ... } that might be a JSON object
    # Use a greedy match but stop at the first balanced closing brace
    object_pattern = r"\{(?:[^{}]|\{[^{}]*\})*\}"
    match = re.search(object_pattern, raw, re.DOTALL)

    if match:
        extracted = match.group(0)
        # Verify it's valid JSON
        try:
            json.loads(extracted)
            logger.debug("Extracted JSON object from text using regex")
            return (True, extracted)
        except json.JSONDecodeError:
            pass

    # Failed to extract valid JSON
    return (
        False,
        "Could not extract valid JSON object from response. "
        "Please respond with a properly formatted JSON object."
    )


def _make_has_ticker_guardrail(ticker: str) -> GuardrailCallable:
    """Create a guardrail that checks for ticker presence."""
    def guardrail(task_output: TaskOutput) -> GuardrailResult:
        raw = getattr(task_output, "raw", "") or ""
        if ticker.upper() not in raw.upper():
            return (
                False,
                f"Output does not mention the ticker '{ticker}'. "
                f"Please include analysis specifically for {ticker}."
            )
        return (True, task_output)

    guardrail.__name__ = f"guardrail_has_ticker_{ticker}"
    return guardrail


def _guardrail_no_secrets(task_output: TaskOutput) -> GuardrailResult:
    """Check that output doesn't contain potential secrets."""
    raw = getattr(task_output, "raw", "") or ""

    # Patterns that might indicate leaked secrets
    secret_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI-style keys
        r"AKIA[A-Z0-9]{16}",  # AWS access keys
        r"-----BEGIN.*PRIVATE KEY-----",  # Private keys
        r"password\s*[=:]\s*['\"][^'\"]+['\"]",  # Password assignments
    ]

    for pattern in secret_patterns:
        if re.search(pattern, raw, re.IGNORECASE):
            return (
                False,
                "Output appears to contain sensitive information. "
                "Please remove any API keys, passwords, or credentials."
            )

    return (True, task_output)


def _make_pydantic_validate_guardrail(schema_key: str) -> GuardrailCallable:
    """Create a guardrail that validates output against a Pydantic schema.

    This is the core guardrail for soft_pydantic mode. It:
    1. Parses the raw output as JSON
    2. Validates against the schema
    3. Sets task_output.json_dict and task_output.pydantic on success
    """
    def guardrail(task_output: TaskOutput) -> GuardrailResult:
        raw = getattr(task_output, "raw", "") or ""

        # Resolve the model
        model_class = resolve_output_model(schema_key)
        if model_class is None:
            return (
                False,
                f"Unknown output schema: '{schema_key}'. "
                f"Please configure a valid schema_key."
            )

        # Parse JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return (
                False,
                f"Output is not valid JSON: {e}. "
                f"Please respond with properly formatted JSON matching the schema."
            )

        # Validate against schema
        try:
            validated = model_class.model_validate(data)
        except Exception as e:
            return (
                False,
                f"Output does not match schema '{schema_key}': {e}. "
                f"Please ensure all required fields are present with correct types."
            )

        # Set structured data on task_output
        task_output.json_dict = data
        task_output.pydantic = validated

        return (True, task_output)

    guardrail.__name__ = f"guardrail_pydantic_validate_{schema_key}"
    return guardrail


def _make_json_validate_guardrail(schema_key: str) -> GuardrailCallable:
    """Create a guardrail that validates JSON structure (without Pydantic model).

    Similar to pydantic_validate but only sets json_dict, not pydantic.
    """
    def guardrail(task_output: TaskOutput) -> GuardrailResult:
        raw = getattr(task_output, "raw", "") or ""

        # Resolve the model for schema validation
        model_class = resolve_output_model(schema_key)
        if model_class is None:
            return (
                False,
                f"Unknown output schema: '{schema_key}'. "
                f"Please configure a valid schema_key."
            )

        # Parse JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return (
                False,
                f"Output is not valid JSON: {e}. "
                f"Please respond with properly formatted JSON."
            )

        # Validate structure (but store as dict, not pydantic)
        try:
            model_class.model_validate(data)
        except Exception as e:
            return (
                False,
                f"Output does not match schema '{schema_key}': {e}. "
                f"Please ensure all required fields are present."
            )

        task_output.json_dict = data
        return (True, task_output)

    guardrail.__name__ = f"guardrail_json_validate_{schema_key}"
    return guardrail


# =============================================================================
# Registry and Builder
# =============================================================================

# Mapping of guardrail keys to factory functions
_GUARDRAIL_REGISTRY: Dict[str, Callable[..., GuardrailCallable]] = {
    "non_empty": lambda **_: _wrap_guardrail(_guardrail_non_empty, "non_empty"),
    "not_fence_only": lambda **_: _wrap_guardrail(_guardrail_not_fence_only, "not_fence_only"),
    "json_parseable": lambda **_: _wrap_guardrail(_guardrail_json_parseable, "json_parseable"),
    "json_no_fence": lambda **_: _wrap_guardrail(_guardrail_json_no_fence, "json_no_fence"),
    "json_extract_object": lambda **_: _wrap_guardrail(_guardrail_json_extract_object, "json_extract_object"),
    "no_secrets": lambda **_: _wrap_guardrail(_guardrail_no_secrets, "no_secrets"),
    "has_ticker": lambda variables, **_: _wrap_guardrail(
        _make_has_ticker_guardrail(variables.get("ticker", "")),
        "has_ticker"
    ),
}


def build_guardrails(
    guardrail_keys: List[str],
    variables: Dict[str, Any],
    task_name: str,
) -> List[Union[GuardrailCallable, str]]:
    """Build a list of guardrail callables from keys.

    Args:
        guardrail_keys: List of guardrail keys (e.g., ['non_empty', 'json_parseable'])
        variables: Runtime variables (for ticker, date, etc.)
        task_name: Task name for logging

    Returns:
        List of guardrail callables or strings (for LLM guardrails)

    Special key formats:
    - 'llm:<description>': Passed through as string for CrewAI LLMGuardrail
    - 'pydantic_validate:<schema_key>': Validates against registered schema
    - 'json_validate:<schema_key>': Validates JSON against registered schema
    """
    result: List[Union[GuardrailCallable, str]] = []

    for key in guardrail_keys:
        # LLM guardrails are passed through as strings
        if key.startswith("llm:"):
            llm_description = key[4:].strip()
            result.append(llm_description)
            continue

        # Pydantic validation guardrail
        if key.startswith("pydantic_validate:"):
            schema_key = key[18:].strip()
            guardrail = _wrap_guardrail(
                _make_pydantic_validate_guardrail(schema_key),
                f"pydantic_validate:{schema_key}"
            )
            result.append(guardrail)
            continue

        # JSON validation guardrail
        if key.startswith("json_validate:"):
            schema_key = key[14:].strip()
            guardrail = _wrap_guardrail(
                _make_json_validate_guardrail(schema_key),
                f"json_validate:{schema_key}"
            )
            result.append(guardrail)
            continue

        # Standard guardrails from registry
        factory = _GUARDRAIL_REGISTRY.get(key)
        if factory:
            guardrail = factory(variables=variables, task_name=task_name)
            result.append(guardrail)
        else:
            logger.warning(
                f"Unknown guardrail key '{key}' for task '{task_name}', skipping"
            )

    return result


def get_available_guardrails() -> List[Dict[str, str]]:
    """Get list of available guardrail keys with descriptions.

    Returns:
        List of dicts with 'key' and 'description' for each guardrail
    """
    return [
        {"key": "non_empty", "description": "Ensure output is not empty"},
        {"key": "json_parseable", "description": "Ensure output is valid JSON"},
        {"key": "json_no_fence", "description": "Clean markdown code fences from JSON"},
        {"key": "json_extract_object", "description": "Extract first JSON object from text (aggressive)"},
        {"key": "has_ticker", "description": "Ensure ticker is mentioned (requires 'ticker' variable)"},
        {"key": "no_secrets", "description": "Check for potential leaked secrets"},
        {"key": "pydantic_validate:<schema_key>", "description": "Validate against Pydantic schema"},
        {"key": "json_validate:<schema_key>", "description": "Validate JSON against schema"},
        {"key": "llm:<description>", "description": "LLM-based guardrail with custom prompt"},
    ]
