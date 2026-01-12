"""
Provider Schemas - Provider-related Pydantic models and utilities.

Contains:
- Provider namespace definitions
- Provider key normalization logic
- Provider-related request/response schemas
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ProviderKeyNamespace(str, Enum):
    """Provider key namespace prefixes."""
    MCP = "mcp"
    BUILTIN = "builtin"
    CUSTOM = "custom"


class ProviderType(str, Enum):
    """Provider type enumeration."""
    MCP = "mcp"
    BUILTIN = "builtin"
    CUSTOM = "custom"


def normalize_provider_key(
    provider_type: str,
    raw_key: str,
    user_id: Optional[int] = None,
    instance_id: str = "default"
) -> str:
    """
    Normalize provider key to namespace format.

    Namespace formats:
    - mcp:{server_key}:{instance_id}    # MCP multi-instance support
    - builtin:{category}:{name}         # Built-in categorization
    - custom:{user_id}:{name}           # User-defined

    Examples:
        >>> normalize_provider_key("mcp", "akshare", instance_id="default")
        'mcp:akshare:default'

        >>> normalize_provider_key("mcp", "akshare", instance_id="cn_market")
        'mcp:akshare:cn_market'

        >>> normalize_provider_key("builtin", "code:python")
        'builtin:code:python'

        >>> normalize_provider_key("custom", "my_provider", user_id=123)
        'custom:123:my_provider'

    Args:
        provider_type: Type of provider ("mcp", "builtin", "custom")
        raw_key: Raw provider key (may or may not have prefix)
        user_id: User ID for custom providers
        instance_id: Instance ID for MCP providers (default: "default")

    Returns:
        Normalized provider key with namespace prefix
    """
    # Strip existing namespace prefix if present
    for prefix in ["mcp:", "builtin:", "custom:"]:
        if raw_key.startswith(prefix):
            raw_key = raw_key[len(prefix):]
            break

    if provider_type == ProviderType.MCP:
        # MCP format: mcp:{server_key}:{instance_id}
        # If raw_key already has instance_id, preserve it
        if ":" in raw_key and instance_id == "default":
            server_key, existing_instance = raw_key.split(":", 1)
            return f"mcp:{server_key}:{existing_instance}"
        else:
            return f"mcp:{raw_key}:{instance_id}"

    elif provider_type == ProviderType.BUILTIN:
        # Builtin format: builtin:{category}:{name}
        if ":" not in raw_key:
            # Default category is "general"
            return f"builtin:general:{raw_key}"
        else:
            # Already has category
            return f"builtin:{raw_key}"

    elif provider_type == ProviderType.CUSTOM:
        # Custom format: custom:{user_id}:{name}
        if user_id is None:
            raise ValueError("user_id is required for custom providers")
        return f"custom:{user_id}:{raw_key}"

    else:
        # Unknown type, return as-is with warning
        return raw_key


def parse_provider_key(provider_key: str) -> dict:
    """
    Parse a namespaced provider key into components.

    Examples:
        >>> parse_provider_key("mcp:akshare:default")
        {'namespace': 'mcp', 'server_key': 'akshare', 'instance_id': 'default'}

        >>> parse_provider_key("builtin:code:python")
        {'namespace': 'builtin', 'category': 'code', 'name': 'python'}

        >>> parse_provider_key("custom:123:my_provider")
        {'namespace': 'custom', 'user_id': 123, 'name': 'my_provider'}

    Args:
        provider_key: Namespaced provider key

    Returns:
        Dict with parsed components
    """
    parts = provider_key.split(":")

    if len(parts) < 2:
        # No namespace, assume legacy format
        return {"namespace": None, "raw": provider_key}

    namespace = parts[0]

    if namespace == "mcp":
        # mcp:{server_key}:{instance_id}
        return {
            "namespace": "mcp",
            "server_key": parts[1] if len(parts) > 1 else None,
            "instance_id": parts[2] if len(parts) > 2 else "default",
        }

    elif namespace == "builtin":
        # builtin:{category}:{name}
        return {
            "namespace": "builtin",
            "category": parts[1] if len(parts) > 1 else "general",
            "name": parts[2] if len(parts) > 2 else parts[1],
        }

    elif namespace == "custom":
        # custom:{user_id}:{name}
        return {
            "namespace": "custom",
            "user_id": int(parts[1]) if len(parts) > 1 else None,
            "name": parts[2] if len(parts) > 2 else None,
        }

    else:
        return {"namespace": namespace, "raw": ":".join(parts[1:])}


class CreateProviderRequest(BaseModel):
    """Request to create a new provider."""
    provider_key: str = Field(..., description="Provider key (will be normalized)")
    provider_type: ProviderType = Field(..., description="Provider type")
    url: Optional[str] = Field(None, description="Provider URL (for MCP providers)")
    config: Optional[dict] = Field(None, description="Provider configuration")
    priority: int = Field(0, description="Provider priority (higher = preferred)")
    instance_id: str = Field("default", description="Instance ID for MCP providers")

    @field_validator("provider_key")
    @classmethod
    def normalize_key(cls, v: str, info) -> str:
        """Auto-normalize provider key on creation."""
        # Normalization will happen in the endpoint with user context
        return v


class ProviderResponse(BaseModel):
    """Provider summary response."""
    id: int
    provider_key: str
    provider_type: str
    url: Optional[str]
    enabled: bool
    healthy: bool
    priority: int
    last_health_check: Optional[str] = None  # ISO format datetime

    class Config:
        from_attributes = True


# ============================================
# Capability Provider API Schemas (from endpoints)
# ============================================

from datetime import datetime
from typing import Any, List


class CapabilityMappingRequest(BaseModel):
    """Request to map capabilities to a provider.

    Supports two formats:
    1. Legacy: { capability_id: raw_tool_name } - one tool per capability
    2. New: { raw_tool_name: capability_id } - multiple tools can map to same capability

    The API auto-detects the format based on whether keys are valid capability IDs.
    """
    mappings: dict[str, Optional[str]]  # {capability_id: raw_tool_name} OR {raw_tool_name: capability_id}


class CapabilityProviderResponse(BaseModel):
    """Provider summary response (Capability Provider API)."""
    id: int
    provider_key: str
    provider_type: str
    url: Optional[str]
    enabled: bool
    healthy: bool
    priority: int
    last_health_check: Optional[datetime]
    capabilities: List[str]  # List of capability_ids

    class Config:
        from_attributes = True


class CapabilityProviderDetailResponse(BaseModel):
    """Detailed provider response with mappings (Capability Provider API)."""
    id: int
    provider_key: str
    provider_type: str
    url: Optional[str]
    config: Optional[dict]
    enabled: bool
    healthy: bool
    priority: int
    last_health_check: Optional[datetime]
    mappings: List[dict]  # [{capability_id, raw_tool_name, config}]

    class Config:
        from_attributes = True


class SaveApiKeyRequest(BaseModel):
    """Request to save API key (Capability Provider API)."""
    api_key: str


class VerifyApiKeyResponse(BaseModel):
    """Response from API key validation (Capability Provider API)."""
    valid: bool
    message: str
    latency_ms: int


class CredentialStatusResponse(BaseModel):
    """Credential status for a provider (Capability Provider API)."""
    provider_id: int
    provider_key: str
    has_credential: bool
    is_verified: bool
    requires_credential: bool
    uses_env_var: bool


__all__ = [
    # Core Provider Schemas
    "ProviderKeyNamespace",
    "ProviderType",
    "normalize_provider_key",
    "parse_provider_key",
    "CreateProviderRequest",
    "ProviderResponse",
    # Capability Provider API Schemas
    "CapabilityMappingRequest",
    "CapabilityProviderResponse",
    "CapabilityProviderDetailResponse",
    "SaveApiKeyRequest",
    "VerifyApiKeyResponse",
    "CredentialStatusResponse",
]
