"""
Redaction utilities for sanitizing sensitive data in logs and events.

This module provides functions to:
- Redact sensitive patterns (API keys, tokens, passwords) from data structures
- Truncate text to prevent excessive log sizes
"""

import re
from typing import Any, Dict, List, Union

# Patterns to redact - matches API keys, tokens, passwords
SENSITIVE_PATTERNS = [
    # OpenAI / Anthropic / other API keys (min 8 chars after prefix)
    (re.compile(r'sk-[a-zA-Z0-9]{8,}'), '[REDACTED_API_KEY]'),
    (re.compile(r'key-[a-zA-Z0-9]{8,}'), '[REDACTED_API_KEY]'),
    # Bearer tokens
    (re.compile(r'Bearer\s+[a-zA-Z0-9._-]{20,}', re.IGNORECASE), 'Bearer [REDACTED_TOKEN]'),
    # Generic API key patterns
    (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9._-]{20,}["\']?', re.IGNORECASE), 'api_key=[REDACTED]'),
    # Password patterns
    (re.compile(r'password["\']?\s*[:=]\s*["\']?[^\s"\']{8,}["\']?', re.IGNORECASE), 'password=[REDACTED]'),
    # Secret patterns
    (re.compile(r'secret["\']?\s*[:=]\s*["\']?[a-zA-Z0-9._-]{20,}["\']?', re.IGNORECASE), 'secret=[REDACTED]'),
    # Token patterns
    (re.compile(r'token["\']?\s*[:=]\s*["\']?[a-zA-Z0-9._-]{20,}["\']?', re.IGNORECASE), 'token=[REDACTED]'),
]

# Keys that should have their values redacted
SENSITIVE_KEYS = {
    'api_key', 'apikey', 'api-key',
    'secret', 'secret_key', 'secretkey',
    'password', 'passwd', 'pwd',
    'token', 'access_token', 'refresh_token',
    'authorization', 'auth',
    'credential', 'credentials',
    'private_key', 'privatekey',
}


def redact_sensitive(obj: Any, max_depth: int = 10) -> Any:
    """Recursively redact sensitive data from an object.

    Handles dicts, lists, and strings. Redacts:
    - Known sensitive key names (api_key, password, token, etc.)
    - Pattern-matched values (sk-xxx, Bearer tokens, etc.)

    Args:
        obj: The object to redact (dict, list, str, or other)
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        A copy of the object with sensitive data redacted
    """
    if max_depth <= 0:
        return "[REDACTED_MAX_DEPTH]"

    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            key_lower = str(key).lower().replace('-', '_')
            if key_lower in SENSITIVE_KEYS:
                result[key] = "[REDACTED]"
            else:
                result[key] = redact_sensitive(value, max_depth - 1)
        return result

    elif isinstance(obj, list):
        return [redact_sensitive(item, max_depth - 1) for item in obj]

    elif isinstance(obj, str):
        return _redact_string(obj)

    else:
        # For other types (int, float, bool, None), return as-is
        return obj


def _redact_string(text: str) -> str:
    """Redact sensitive patterns from a string.

    Args:
        text: The string to redact

    Returns:
        String with sensitive patterns replaced
    """
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def truncate_text(text: str, limit: int = 2000) -> str:
    """Truncate text to a maximum length with ellipsis indicator.

    Args:
        text: The text to truncate
        limit: Maximum length (default 2000 characters)

    Returns:
        Truncated text with "..." suffix if exceeded limit
    """
    if not isinstance(text, str):
        return text

    if len(text) <= limit:
        return text

    return text[:limit] + "..."
