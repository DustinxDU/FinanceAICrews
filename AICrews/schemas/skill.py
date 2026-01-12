"""
Skill Schemas - Skill management related models.

Contains schemas for skill catalog, capability taxonomy, and skill management.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SkillToggleRequest(BaseModel):
    """Request to toggle skill enabled status."""
    enabled: bool


class SkillToggleResponse(BaseModel):
    """Response after toggling skill."""
    skill_key: str
    is_enabled: bool


class CreateSkillRequest(BaseModel):
    """Request to create a new skill."""
    skill_key: str
    kind: str  # preset, strategy, skillset
    title: str
    description: Optional[str] = None
    capability_id: Optional[str] = None
    invocation: Optional[Dict[str, Any]] = None
    args_schema: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class CapabilityInfo(BaseModel):
    """Capability information for taxonomy display."""
    capability_id: str
    display_name: str
    description: str
    group: str
    icon: Optional[str] = None
    dependencies: List[str] = []
    available: bool = False


class SkillInfo(BaseModel):
    """
    Skill information for catalog display.

    Contains all metadata needed to display and invoke a skill,
    including readiness status based on capability dependencies.
    """
    skill_key: str
    kind: str
    capability_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    tags: List[str] = []
    is_system: bool = False
    is_enabled: bool = True
    is_ready: bool = True  # Based on dependency check
    blocked_reason: Optional[str] = None
    args_schema: Optional[Dict[str, Any]] = None
    examples: List[Dict[str, Any]] = []
    invocation: Optional[Dict[str, Any]] = None  # Contains required_capabilities for preset/strategy/skillset


class SkillCatalogResponse(BaseModel):
    """Full skill catalog response grouped by kind."""
    capabilities: List[SkillInfo] = []
    presets: List[SkillInfo] = []
    strategies: List[SkillInfo] = []
    skillsets: List[SkillInfo] = []


class CapabilityTaxonomyResponse(BaseModel):
    """Capability taxonomy response grouped by category."""
    core: List[CapabilityInfo]
    extended: List[CapabilityInfo]
    compute: List[CapabilityInfo]
    external: List[CapabilityInfo]


__all__ = [
    "SkillToggleRequest",
    "SkillToggleResponse",
    "CreateSkillRequest",
    "CapabilityInfo",
    "SkillInfo",
    "SkillCatalogResponse",
    "CapabilityTaxonomyResponse",
]
