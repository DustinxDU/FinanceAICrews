"""
Skills API - Unified skill catalog and management.

Endpoints:
- GET /skills/catalog - List all skills with status
- GET /skills/capabilities - List capability taxonomy
- POST /skills - Create a new skill (preset/strategy/skillset)
- POST /skills/{skill_key}/toggle - Toggle skill enabled/disabled
- GET /skills/{skill_key} - Get skill detail with card
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from AICrews.capabilities.taxonomy import (
    CORE_CAPABILITIES,
    EXTENDED_CAPABILITIES,
    COMPUTE_CAPABILITIES,
    EXTERNAL_CAPABILITIES,
    CAPABILITY_METADATA,
    CAPABILITY_DEPENDENCIES,
    get_capability_dependencies,
)
from AICrews.database.models.skill import SkillCatalog, SkillKind, UserSkillPreference
from AICrews.database.models.provider import CapabilityProvider, ProviderCapabilityMapping
from AICrews.schemas.skill import (
    SkillToggleRequest,
    SkillToggleResponse,
    CreateSkillRequest,
    CapabilityInfo,
    SkillInfo,
    SkillCatalogResponse,
    CapabilityTaxonomyResponse,
)
from backend.app.security import get_current_user, get_current_user_optional, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["Skills"])


# =============================================================================
# Helper Functions for Dependency Checking
# =============================================================================

def _get_provider_status(provider: CapabilityProvider) -> Dict[str, bool]:
    """Get the status of a capability provider."""
    return {
        'enabled': provider.enabled,
        'healthy': provider.healthy,
    }


def _check_capability_available(db: Session, capability_id: str) -> tuple[bool, Optional[str]]:
    """
    Check if a capability is available from an enabled, healthy provider.

    Returns:
        tuple: (is_available, blocked_reason)
    """
    # Find providers that implement this capability
    result = db.execute(
        select(CapabilityProvider)
        .join(ProviderCapabilityMapping)
        .filter(
            ProviderCapabilityMapping.capability_id == capability_id,
            CapabilityProvider.enabled == True,
            CapabilityProvider.healthy == True,
        )
    )
    providers = result.scalars().all()

    if providers:
        return True, None

    # No enabled+healthy provider found
    # Check if any provider exists (but disabled or unhealthy)
    # Note: Multiple providers may implement the same capability, so use first()
    any_provider = db.execute(
        select(CapabilityProvider)
        .join(ProviderCapabilityMapping)
        .filter(ProviderCapabilityMapping.capability_id == capability_id)
    ).scalars().first()

    if any_provider:
        if not any_provider.enabled:
            return False, f"Provider '{any_provider.provider_key}' is disabled"
        else:
            return False, f"Provider '{any_provider.provider_key}' is unhealthy"
    else:
        return False, f"No provider available for capability '{capability_id}'"


def _check_skill_ready(skill: SkillCatalog, db: Session) -> Dict[str, Any]:
    """
    Check if a skill is ready based on its dependencies.

    Dependency resolution:
    1. For capability skills: Check if capability has enabled+healthy provider
    2. For preset/strategy skills: Check capability + its dependencies (e.g., indicator_calc needs equity_history)
    3. For skillsets without capability_id: Always ready

    Returns:
        Dict with 'is_ready' (bool) and 'blocked_reason' (Optional[str])
    """
    # Skills without capability_id are always ready (e.g., composite skillsets)
    if not skill.capability_id:
        return {'is_ready': True, 'blocked_reason': None}

    capability_id = skill.capability_id

    # Check if the primary capability is available
    is_available, reason = _check_capability_available(db, capability_id)

    if not is_available:
        return {'is_ready': False, 'blocked_reason': reason}

    # Check capability dependencies (e.g., indicator_calc depends on equity_history)
    dependencies = get_capability_dependencies(capability_id)

    for dep_capability in dependencies:
        dep_available, dep_reason = _check_capability_available(db, dep_capability)
        if not dep_available:
            return {
                'is_ready': False,
                'blocked_reason': f"Dependency '{dep_capability}' not available: {dep_reason}"
            }

    return {'is_ready': True, 'blocked_reason': None}


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/catalog", response_model=SkillCatalogResponse, summary="Get skill catalog")
async def get_skill_catalog(
    kind: Optional[str] = Query(None, description="Filter by kind: capability, preset, strategy, skillset"),
    enabled_only: bool = Query(False, description="Only return enabled skills"),
    current_user: Optional[Any] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> SkillCatalogResponse:
    """
    Get the full skill catalog with user preferences applied.

    Returns skills grouped by kind (capabilities, presets, strategies, skillsets).
    Each skill includes ready/blocked status based on capability dependencies.
    """
    user_id = current_user.id if current_user else None

    # Query skills from catalog
    query = select(SkillCatalog).where(SkillCatalog.is_active == True)

    if kind:
        try:
            skill_kind = SkillKind(kind)
            query = query.filter(SkillCatalog.kind == skill_kind)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid kind: {kind}")

    query = query.order_by(SkillCatalog.sort_order, SkillCatalog.title)
    skills = db.execute(query).scalars().all()

    # Get user preferences if authenticated
    user_prefs: Dict[str, bool] = {}
    if user_id:
        prefs = db.execute(
            select(UserSkillPreference).where(UserSkillPreference.user_id == user_id)
        ).scalars().all()
        user_prefs = {p.skill_key: p.is_enabled for p in prefs}

    # Build response grouped by kind
    result = SkillCatalogResponse()

    for skill in skills:
        # Determine enabled status
        is_enabled = user_prefs.get(skill.skill_key, True)  # Default enabled

        if enabled_only and not is_enabled:
            continue

        # Check if skill is ready (dependencies available)
        ready_status = _check_skill_ready(skill, db)
        is_ready = ready_status['is_ready']
        blocked_reason = ready_status['blocked_reason']

        info = SkillInfo(
            skill_key=skill.skill_key,
            kind=skill.kind.value,
            capability_id=skill.capability_id,
            title=skill.title,
            description=skill.description,
            icon=skill.icon,
            tags=skill.tags or [],
            is_system=skill.is_system,
            is_enabled=is_enabled,
            is_ready=is_ready,
            blocked_reason=blocked_reason,
            args_schema=skill.args_schema,
            examples=skill.examples or [],
            invocation=skill.invocation,
        )

        if skill.kind == SkillKind.capability:
            result.capabilities.append(info)
        elif skill.kind == SkillKind.preset:
            result.presets.append(info)
        elif skill.kind == SkillKind.strategy:
            result.strategies.append(info)
        elif skill.kind == SkillKind.skillset:
            result.skillsets.append(info)

    return result


@router.get("/capabilities", response_model=CapabilityTaxonomyResponse, summary="Get capability taxonomy")
async def get_capability_taxonomy() -> CapabilityTaxonomyResponse:
    """
    Get the standard capability taxonomy.

    Returns capabilities grouped by category (core, extended, compute, external).
    """
    def make_capability_info(cap_id: str) -> CapabilityInfo:
        meta = CAPABILITY_METADATA.get(cap_id, {})
        return CapabilityInfo(
            capability_id=cap_id,
            display_name=meta.get("display_name", cap_id),
            description=meta.get("description", ""),
            group=meta.get("group", "unknown"),
            icon=meta.get("icon"),
            dependencies=CAPABILITY_DEPENDENCIES.get(cap_id, []),
            available=False,  # TODO: Check provider availability
        )

    return CapabilityTaxonomyResponse(
        core=[make_capability_info(c) for c in CORE_CAPABILITIES],
        extended=[make_capability_info(c) for c in EXTENDED_CAPABILITIES],
        compute=[make_capability_info(c) for c in COMPUTE_CAPABILITIES],
        external=[make_capability_info(c) for c in EXTERNAL_CAPABILITIES],
    )


@router.post("", response_model=SkillInfo, summary="Create skill")
async def create_skill(
    request: CreateSkillRequest,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SkillInfo:
    """
    Create a new user skill (preset, strategy, or skillset).
    """
    # Validate kind
    try:
        kind = SkillKind(request.kind)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid kind: {request.kind}")

    # Check if skill_key already exists
    existing = db.execute(
        select(SkillCatalog).where(SkillCatalog.skill_key == request.skill_key)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail=f"Skill already exists: {request.skill_key}")

    # Create skill
    skill = SkillCatalog(
        skill_key=request.skill_key,
        kind=kind,
        capability_id=request.capability_id,
        title=request.title,
        description=request.description,
        invocation=request.invocation,
        args_schema=request.args_schema,
        tags=request.tags or [],
        is_system=False,  # User-created skills are not system
        is_active=True,
    )

    db.add(skill)
    db.commit()
    db.refresh(skill)

    return SkillInfo(
        skill_key=skill.skill_key,
        kind=skill.kind.value,
        capability_id=skill.capability_id,
        title=skill.title,
        description=skill.description,
        icon=skill.icon,
        tags=skill.tags or [],
        is_system=skill.is_system,
        is_enabled=True,
        is_ready=True,
        blocked_reason=None,
        args_schema=skill.args_schema,
        examples=skill.examples or [],
        invocation=skill.invocation,
    )


@router.post("/{skill_key:path}/toggle", response_model=SkillToggleResponse, summary="Toggle skill")
async def toggle_skill(
    skill_key: str,
    request: SkillToggleRequest,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SkillToggleResponse:
    """
    Toggle a skill's enabled status for the current user.
    """
    user_id = current_user.id

    # Check if preference exists
    pref = db.execute(
        select(UserSkillPreference).where(
            UserSkillPreference.user_id == user_id,
            UserSkillPreference.skill_key == skill_key,
        )
    ).scalar_one_or_none()

    if pref:
        pref.is_enabled = request.enabled
    else:
        pref = UserSkillPreference(
            user_id=user_id,
            skill_key=skill_key,
            is_enabled=request.enabled,
        )
        db.add(pref)

    db.commit()

    return SkillToggleResponse(skill_key=skill_key, is_enabled=request.enabled)


@router.get("/{skill_key:path}", summary="Get skill detail")
async def get_skill_detail(
    skill_key: str,
    current_user: Optional[Any] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> SkillInfo:
    """
    Get detailed information about a skill including its card.
    """
    skill = db.execute(
        select(SkillCatalog).where(SkillCatalog.skill_key == skill_key)
    ).scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_key}")

    # Get user preference
    is_enabled = True
    if current_user:
        pref = db.execute(
            select(UserSkillPreference).where(
                UserSkillPreference.user_id == current_user.id,
                UserSkillPreference.skill_key == skill_key,
            )
        ).scalar_one_or_none()
        if pref:
            is_enabled = pref.is_enabled

    # Check if skill is ready (dependencies available)
    ready_status = _check_skill_ready(skill, db)

    return SkillInfo(
        skill_key=skill.skill_key,
        kind=skill.kind.value,
        capability_id=skill.capability_id,
        title=skill.title,
        description=skill.description,
        icon=skill.icon,
        tags=skill.tags or [],
        is_system=skill.is_system,
        is_enabled=is_enabled,
        is_ready=ready_status['is_ready'],
        blocked_reason=ready_status['blocked_reason'],
        args_schema=skill.args_schema,
        examples=skill.examples or [],
        invocation=skill.invocation,
    )
