"""Capability definitions and taxonomy."""
from .taxonomy import (
    ALL_CAPABILITIES,
    CORE_CAPABILITIES,
    EXTENDED_CAPABILITIES,
    COMPUTE_CAPABILITIES,
    EXTERNAL_CAPABILITIES,
    CAPABILITY_METADATA,
    CAPABILITY_DEPENDENCIES,
    is_valid_capability,
    get_capability_group,
    get_capability_dependencies,
    get_capabilities_by_group,
)

__all__ = [
    "ALL_CAPABILITIES",
    "CORE_CAPABILITIES",
    "EXTENDED_CAPABILITIES",
    "COMPUTE_CAPABILITIES",
    "EXTERNAL_CAPABILITIES",
    "CAPABILITY_METADATA",
    "CAPABILITY_DEPENDENCIES",
    "is_valid_capability",
    "get_capability_group",
    "get_capability_dependencies",
    "get_capabilities_by_group",
]
