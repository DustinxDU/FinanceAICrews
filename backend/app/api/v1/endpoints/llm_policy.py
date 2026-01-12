"""
LLM Policy Router API Endpoints

This module provides REST APIs for managing the LLM Policy Router system:
- BYOK profiles (user BYOK API keys per tier)
- Routing overrides (force routing mode per scope)
- System profiles (admin-managed model mappings)
- Virtual key status (read-only user key info)

All endpoints are thin wrappers around database operations.
Business logic stays in AICrews.llm.policy_router.
"""

import logging
import os
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.security import get_current_user, get_db
from backend.app.api.v1.utils.entitlements_http import require_entitlement
from AICrews.database.models.user import User
from AICrews.database.models.llm_policy import (
    LLMSystemProfile,
    LLMUserByokProfile,
    LLMRoutingOverride,
    LLMVirtualKey,
    RoutingModeEnum,
)
from AICrews.schemas.llm_policy import (
    LLMUserByokProfileResponse,
    LLMUserByokProfileCreate,
    LLMUserByokProfileUpdate,
    LLMRoutingOverrideResponse,
    LLMRoutingOverrideCreate,
    LLMSystemProfileResponse,
    LLMVirtualKeyResponse,
    LLMScope,
    ByokTestCode,
)
from AICrews.utils.encryption import encrypt_api_key, decrypt_api_key
from AICrews.schemas.entitlements import PolicyAction
from AICrews.schemas.llm_policy import (
    ProviderCatalogItem,
    RouterStatusResponse,
    RoutingPreviewResponse,
    SystemConfigReloadResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm-policy", tags=["LLM Policy Router"])


# Valid tier values
VALID_TIERS = {"agents_fast", "agents_balanced", "agents_best"}


def _mask_api_key(decrypted_key: str) -> str:
    """Return masked version of API key for display."""
    if not decrypted_key or len(decrypted_key) < 8:
        return "••••••••"
    return f"{decrypted_key[:4]}••••{decrypted_key[-4:]}"


def _profile_to_response(profile: LLMUserByokProfile) -> dict:
    """Convert DB profile to response dict with key_masked."""
    try:
        decrypted_key = decrypt_api_key(profile.api_key_encrypted) if profile.api_key_encrypted else ""
        key_masked = _mask_api_key(decrypted_key)
    except Exception:
        key_masked = "••••••••"

    return {
        "id": profile.id,
        "tier": profile.scenario,  # Return scenario as tier for backward compatibility
        "scenario": profile.scenario,  # New field
        "provider": profile.provider,
        "model": profile.model,
        "api_base": profile.api_base,
        "api_version": profile.api_version,
        "enabled": profile.enabled,
        "key_masked": key_masked,
        "last_tested_at": profile.last_tested_at,
        "last_test_status": profile.last_test_status,
        "last_test_code": profile.last_test_code,
        "last_test_message": profile.last_test_message,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


# ============================================================================
# Lazy-initialized ConfigStore for providers catalog
# ============================================================================

_config_store_instance: Optional[Any] = None
_config_store_lock = __import__('threading').Lock()


def _get_config_store():
    """Lazy-initialize ConfigStore to avoid import-time I/O."""
    global _config_store_instance
    if _config_store_instance is None:
        with _config_store_lock:
            if _config_store_instance is None:
                from AICrews.llm.core.config_store import ConfigStore
                _config_store_instance = ConfigStore(auto_reload=False)
    return _config_store_instance


# ============================================================================
# Providers Catalog Endpoint (for BYOK UI)
# ============================================================================


@router.get("/providers", response_model=List[ProviderCatalogItem])
async def list_providers_catalog() -> List[ProviderCatalogItem]:
    """
    Get providers catalog for BYOK UI dropdowns.

    Returns minimal provider information needed for configuration:
    - provider_key: Internal identifier (e.g., "openai", "anthropic")
    - display_name: Human-readable name
    - provider_type: crewai_native, openai_compatible, etc.
    - requires_api_key: Whether API key is needed
    - requires_base_url: Whether custom base URL is required
    - default_api_base: Default API endpoint (null if not set)
    """
    config_store = _get_config_store()
    providers_config = config_store.providers

    catalog = []
    for provider_key, provider_config in providers_config.providers.items():
        catalog.append(ProviderCatalogItem(
            provider_key=provider_key,
            display_name=provider_config.display_name,
            provider_type=provider_config.provider_type.value,
            requires_api_key=bool(provider_config.auth.api_key_env),
            requires_base_url=provider_config.endpoints.requires_base_url,
            default_api_base=provider_config.endpoints.api_base or None,
        ))

    return catalog


# ============================================================================
# API Key Validation Endpoint (for BYOK UI - validate before saving)
# ============================================================================


class ValidateApiKeyRequest(BaseModel):
    """Request to validate an API key."""
    provider_key: str
    api_key: str
    base_url: Optional[str] = None
    volcengine_endpoints: Optional[List[str]] = None


class ValidateApiKeyResponse(BaseModel):
    """Response from API key validation."""
    valid: bool
    message: str
    error: Optional[str] = None
    error_details: Optional[dict] = None


@router.post("/validate", response_model=ValidateApiKeyResponse)
async def validate_api_key(
    request: ValidateApiKeyRequest,
) -> ValidateApiKeyResponse:
    """
    Validate an API key without saving it.

    Use this to test an API key before saving. Makes a minimal LLM call
    to verify the credentials work.

    Supports all providers in the catalog.
    """
    import httpx
    import time

    provider_key = request.provider_key
    api_key = request.api_key
    base_url = request.base_url

    # Get provider config for default base URL
    config_store = _get_config_store()
    provider_config = config_store.providers.providers.get(provider_key)

    if not provider_config:
        return ValidateApiKeyResponse(
            valid=False,
            message=f"Unknown provider: {provider_key}",
            error="UNKNOWN_PROVIDER"
        )

    # Determine base URL
    if not base_url:
        base_url = provider_config.endpoints.api_base

    if not base_url:
        return ValidateApiKeyResponse(
            valid=False,
            message=f"Provider {provider_key} requires a base URL",
            error="BASE_URL_REQUIRED"
        )

    try:
        # Prepare test request based on provider type
        if provider_key == "anthropic":
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}],
            }
            url = f"{base_url.rstrip('/')}/v1/messages"
        elif provider_key == "volcengine":
            # Volcano Engine requires endpoint ID
            if not request.volcengine_endpoints:
                return ValidateApiKeyResponse(
                    valid=False,
                    message="Volcano Engine requires at least one endpoint ID",
                    error="ENDPOINT_REQUIRED"
                )
            endpoint = request.volcengine_endpoints[0]
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": endpoint,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"
        elif provider_key == "google_gemini":
            # Gemini uses query param for API key
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": "Hi"}]}],
                "generationConfig": {"maxOutputTokens": 1}
            }
            url = f"{base_url.rstrip('/')}/models/gemini-1.5-flash:generateContent?key={api_key}"
        elif provider_key == "zhipu_ai":
            # 智谱 AI (GLM)
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "glm-4-flash",  # Use cheapest model for testing
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"
        elif provider_key == "kimi_moonshot":
            # Kimi (Moonshot)
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "moonshot-v1-8k",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"
        elif provider_key == "qianwen_dashscope":
            # 通义千问 (DashScope)
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "qwen-turbo",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"
        elif provider_key == "deepseek":
            # DeepSeek
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"
        else:
            # Default: OpenAI-compatible
            headers = {"Authorization": f"Bearer {api_key}"}
            # Use a common model for testing based on provider
            if provider_key == "openai":
                test_model = "gpt-4o-mini"
            elif provider_key == "groq":
                test_model = "llama-3.1-8b-instant"
            elif provider_key == "mistral":
                test_model = "mistral-small-latest"
            else:
                test_model = "gpt-4o-mini"  # Fallback
            payload = {
                "model": test_model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"

        # Make test call
        start_time = time.time()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        latency_ms = int((time.time() - start_time) * 1000)

        if response.status_code == 200:
            return ValidateApiKeyResponse(
                valid=True,
                message=f"API key validated successfully ({latency_ms}ms)"
            )
        elif response.status_code == 401:
            return ValidateApiKeyResponse(
                valid=False,
                message="Invalid API key",
                error="INVALID_KEY",
                error_details={"status_code": 401, "provider": provider_key}
            )
        elif response.status_code == 403:
            return ValidateApiKeyResponse(
                valid=False,
                message="API key does not have required permissions",
                error="FORBIDDEN",
                error_details={"status_code": 403, "provider": provider_key}
            )
        elif response.status_code == 429:
            return ValidateApiKeyResponse(
                valid=False,
                message="Rate limited by provider - try again later",
                error="RATE_LIMITED",
                error_details={"status_code": 429, "provider": provider_key}
            )
        else:
            try:
                error_body = response.json()
                error_msg = error_body.get("error", {}).get("message", response.text[:200])
            except Exception:
                error_msg = response.text[:200]

            return ValidateApiKeyResponse(
                valid=False,
                message=f"Provider error: {error_msg}",
                error="PROVIDER_ERROR",
                error_details={
                    "status_code": response.status_code,
                    "provider": provider_key,
                    "raw_response": error_msg
                }
            )

    except httpx.TimeoutException:
        return ValidateApiKeyResponse(
            valid=False,
            message="Request timed out - provider may be slow or unreachable",
            error="TIMEOUT"
        )
    except httpx.RequestError as e:
        return ValidateApiKeyResponse(
            valid=False,
            message=f"Network error: {str(e)[:100]}",
            error="NETWORK_ERROR"
        )
    except Exception as e:
        logger.exception(f"Unexpected error validating API key for {provider_key}")
        return ValidateApiKeyResponse(
            valid=False,
            message=f"Unexpected error: {str(e)[:100]}",
            error="UNEXPECTED_ERROR"
        )


# ============================================================================
# LLM Config CRUD Endpoints (for API Keys Tab)
# ============================================================================


class SaveLLMConfigRequest(BaseModel):
    """Request to save an LLM provider configuration."""
    provider_key: str
    api_key: str
    base_url: Optional[str] = None
    config_name: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    volcengine_endpoints: Optional[List[str]] = None
    config_id: Optional[int] = None  # For updates


class LLMConfigResponse(BaseModel):
    """Response for LLM config operations."""
    id: int
    provider_key: str
    provider_name: str
    config_name: str
    is_validated: bool
    is_active: bool
    base_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


@router.get("/configs", response_model=List[LLMConfigResponse])
async def list_llm_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[LLMConfigResponse]:
    """
    List all LLM configurations for the current user.

    Returns saved provider configurations with API keys (masked).
    """
    from AICrews.database.models.llm import UserLLMConfig, LLMProvider

    configs = db.query(UserLLMConfig).filter(
        UserLLMConfig.user_id == current_user.id,
        UserLLMConfig.is_active == True
    ).all()

    result = []
    for config in configs:
        provider = db.query(LLMProvider).filter(LLMProvider.id == config.provider_id).first()
        result.append(LLMConfigResponse(
            id=config.id,
            provider_key=provider.provider_key if provider else "unknown",
            provider_name=provider.display_name if provider else "Unknown",
            config_name=config.config_name,
            is_validated=config.is_validated,
            is_active=config.is_active,
            base_url=config.base_url,
            created_at=config.created_at,
            updated_at=config.updated_at,
        ))

    return result


@router.post("/configs", response_model=LLMConfigResponse)
async def save_llm_config(
    request: SaveLLMConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LLMConfigResponse:
    """
    Save or update an LLM provider configuration.

    If config_id is provided, updates existing config.
    Otherwise creates a new config (or updates existing for same provider).

    After saving, dynamically fetches available models from the provider's API
    and creates UserModelConfig records for model selection in Agent Models tab.
    """
    from AICrews.database.models.llm import UserLLMConfig, LLMProvider, LLMModel, UserModelConfig
    from AICrews.services.provider_credential_service import encrypt_api_key
    from AICrews.llm.services.model_service import get_model_service

    # Find provider by key
    provider = db.query(LLMProvider).filter(
        LLMProvider.provider_key == request.provider_key
    ).first()

    if not provider:
        # Create provider if it doesn't exist
        config_store = _get_config_store()
        provider_config = config_store.providers.providers.get(request.provider_key)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {request.provider_key}"
            )

        provider = LLMProvider(
            provider_key=request.provider_key,
            display_name=provider_config.display_name,
            provider_type=provider_config.provider_type.value,
            is_active=True,
        )
        db.add(provider)
        db.flush()

    # Check for existing config
    existing_config = None
    if request.config_id:
        existing_config = db.query(UserLLMConfig).filter(
            UserLLMConfig.id == request.config_id,
            UserLLMConfig.user_id == current_user.id
        ).first()
    else:
        # Check if user already has a config for this provider
        existing_config = db.query(UserLLMConfig).filter(
            UserLLMConfig.user_id == current_user.id,
            UserLLMConfig.provider_id == provider.id
        ).first()

    # Encrypt API key
    try:
        encrypted_key = encrypt_api_key(request.api_key)
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {e}")
        # Store as-is if encryption fails (not recommended for production)
        encrypted_key = request.api_key

    config_name = request.config_name or provider.display_name

    if existing_config:
        # Update existing
        existing_config.api_key = encrypted_key
        existing_config.base_url = request.base_url
        existing_config.config_name = config_name
        existing_config.default_temperature = request.temperature or 0.7
        existing_config.default_max_tokens = request.max_tokens
        existing_config.is_validated = True  # Assume validated since we just tested
        existing_config.last_validated_at = datetime.now()
        config = existing_config
        logger.info(f"Updated LLM config: user_id={current_user.id}, provider={request.provider_key}")
    else:
        # Create new
        config = UserLLMConfig(
            user_id=current_user.id,
            provider_id=provider.id,
            config_name=config_name,
            api_key=encrypted_key,
            base_url=request.base_url,
            default_temperature=request.temperature or 0.7,
            default_max_tokens=request.max_tokens,
            is_active=True,
            is_validated=True,
            last_validated_at=datetime.now(),
        )
        db.add(config)
        logger.info(f"Created LLM config: user_id={current_user.id}, provider={request.provider_key}")

    db.flush()  # Get config.id before creating model configs

    # Dynamically fetch models from provider API and create UserModelConfig records
    models_created = 0
    try:
        logger.info(
            f"Starting model discovery for {request.provider_key}, "
            f"api_key_len={len(request.api_key) if request.api_key else 0}, "
            f"base_url={request.base_url}"
        )
        model_service = get_model_service()
        discovered_models = await model_service.list_models(
            provider_key=request.provider_key,
            api_key=request.api_key,  # Use raw API key for discovery
            base_url=request.base_url,
            use_cache=False,  # Force fresh fetch
        )

        logger.info(
            f"Discovered {len(discovered_models)} models from {request.provider_key} API"
        )

        for model_info in discovered_models:
            # Find or create LLMModel record
            llm_model = db.query(LLMModel).filter(
                LLMModel.provider_id == provider.id,
                LLMModel.model_key == model_info.model_key
            ).first()

            if not llm_model:
                # Create new LLMModel record
                llm_model = LLMModel(
                    provider_id=provider.id,
                    model_key=model_info.model_key,
                    display_name=model_info.display_name,
                    context_length=model_info.context_length,
                    supports_tools=model_info.supports_tools,
                    performance_level=model_info.performance_level,
                    is_thinking=model_info.is_thinking,
                    is_active=True,
                )
                db.add(llm_model)
                db.flush()

            # Check if UserModelConfig already exists
            existing_model_config = db.query(UserModelConfig).filter(
                UserModelConfig.user_id == current_user.id,
                UserModelConfig.llm_config_id == config.id,
                UserModelConfig.model_id == llm_model.id
            ).first()

            if not existing_model_config:
                model_config = UserModelConfig(
                    user_id=current_user.id,
                    llm_config_id=config.id,
                    model_id=llm_model.id,
                    is_active=True,
                    is_available=True,
                )
                db.add(model_config)
                models_created += 1

    except Exception as e:
        # Log error but don't fail the save operation
        # Models can be fetched later via refresh
        logger.warning(
            f"Failed to discover models from {request.provider_key}: {e}. "
            f"User can refresh models later."
        )

    db.commit()
    db.refresh(config)

    logger.info(
        f"Saved LLM config: user_id={current_user.id}, provider={request.provider_key}, "
        f"models_discovered={models_created}"
    )

    return LLMConfigResponse(
        id=config.id,
        provider_key=provider.provider_key,
        provider_name=provider.display_name,
        config_name=config.config_name,
        is_validated=config.is_validated,
        is_active=config.is_active,
        base_url=config.base_url,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete an LLM provider configuration.
    """
    from AICrews.database.models.llm import UserLLMConfig

    config = db.query(UserLLMConfig).filter(
        UserLLMConfig.id == config_id,
        UserLLMConfig.user_id == current_user.id
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    db.delete(config)
    db.commit()
    logger.info(f"Deleted LLM config: user_id={current_user.id}, config_id={config_id}")


# ============================================================================
# Router Status Endpoint
# ============================================================================


@router.get("/status", response_model=RouterStatusResponse)
async def get_router_status() -> RouterStatusResponse:
    """Check if LLM Policy Router is enabled."""
    enabled = os.getenv("LLM_POLICY_ROUTER_ENABLED", "false").lower() == "true"
    message = "Router is active" if enabled else "Router is disabled (using legacy path)"
    return RouterStatusResponse(enabled=enabled, message=message)


@router.get("/routing-preview/{scope}", response_model=RoutingPreviewResponse)
async def get_routing_preview(
    scope: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoutingPreviewResponse:
    """
    Preview routing decision for a scope (without making LLM call).

    Returns what routing would be used:
    - "system": System-managed profile
    - "byok": User BYOK configuration

    This is a read-only preview - doesn't trigger provisioning.
    """
    # Check if router is enabled
    router_enabled = os.getenv("LLM_POLICY_ROUTER_ENABLED", "false").lower() == "true"
    if not router_enabled:
        return RoutingPreviewResponse(
            routing_effective="system",
            scope=scope,
            model_alias="legacy",
        )

    # Check for SYSTEM_ONLY scopes
    system_only_scopes = {"copilot", "cockpit_scan", "crew_router", "crew_summary"}
    if scope in system_only_scopes:
        # Get system profile for model alias
        system_profile = (
            db.query(LLMSystemProfile)
            .filter(LLMSystemProfile.scope == scope, LLMSystemProfile.enabled == True)
            .first()
        )
        return RoutingPreviewResponse(
            routing_effective="system",
            scope=scope,
            model_alias=system_profile.proxy_model_name if system_profile else None,
        )

    # Check for admin override
    override = (
        db.query(LLMRoutingOverride)
        .filter(
            LLMRoutingOverride.user_id == current_user.id,
            LLMRoutingOverride.scope == scope,
        )
        .first()
    )

    if override:
        if override.mode == RoutingModeEnum.SYSTEM_ONLY:
            system_profile = (
                db.query(LLMSystemProfile)
                .filter(LLMSystemProfile.scope == scope, LLMSystemProfile.enabled == True)
                .first()
            )
            return RoutingPreviewResponse(
                routing_effective="system",
                scope=scope,
                model_alias=system_profile.proxy_model_name if system_profile else None,
            )
        elif override.mode == RoutingModeEnum.USER_BYOK_ONLY:
            # Note: Using scenario field - tier fallback removed via migration 8e239749edcd
            byok_profile = (
                db.query(LLMUserByokProfile)
                .filter(
                    LLMUserByokProfile.user_id == current_user.id,
                    LLMUserByokProfile.scenario == scope,
                    LLMUserByokProfile.enabled == True,
                )
                .first()
            )
            if byok_profile:
                return RoutingPreviewResponse(
                    routing_effective="byok",
                    scope=scope,
                    model_alias=scope,
                    provider=byok_profile.provider,
                    user_model=byok_profile.model,
                )
            else:
                # BYOK required but not configured - show as system fallback
                return RoutingPreviewResponse(
                    routing_effective="system",
                    scope=scope,
                    model_alias=None,
                )

    # AUTO mode: Check if user has BYOK configured for this scenario
    agent_scenarios = {"agents_fast", "agents_balanced", "agents_best"}
    if scope in agent_scenarios:
        # Check subscription eligibility (simplified - always check BYOK profile)
        # Note: Using scenario field - tier fallback removed via migration 8e239749edcd
        byok_profile = (
            db.query(LLMUserByokProfile)
            .filter(
                LLMUserByokProfile.user_id == current_user.id,
                LLMUserByokProfile.scenario == scope,
                LLMUserByokProfile.enabled == True,
            )
            .first()
        )

        if byok_profile:
            return RoutingPreviewResponse(
                routing_effective="byok",
                scope=scope,
                model_alias=scope,
                provider=byok_profile.provider,
                user_model=byok_profile.model,
            )

    # Fallback to system
    system_profile = (
        db.query(LLMSystemProfile)
        .filter(LLMSystemProfile.scope == scope, LLMSystemProfile.enabled == True)
        .first()
    )
    return RoutingPreviewResponse(
        routing_effective="system",
        scope=scope,
        model_alias=system_profile.proxy_model_name if system_profile else None,
    )


# ============================================================================
# BYOK Profile Management (User Endpoints)
# ============================================================================


@router.get("/byok-profiles", response_model=List[LLMUserByokProfileResponse])
async def list_byok_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[dict]:
    """List user's BYOK profiles with masked keys."""
    profiles = (
        db.query(LLMUserByokProfile)
        .filter(LLMUserByokProfile.user_id == current_user.id)
        .all()
    )
    return [_profile_to_response(p) for p in profiles]


@router.post(
    "/byok-profiles",
    response_model=LLMUserByokProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_byok_profile(
    profile_data: LLMUserByokProfileCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Create or update BYOK profile for a tier.

    If profile already exists for this tier, updates it (upsert behavior).
    API key is encrypted before storage.
    """
    require_entitlement(
        action=PolicyAction.SET_BYOK_KEY,
        request=request,
        db=db,
        current_user=current_user,
    )
    # Check for existing profile (using scenario field)
    existing = (
        db.query(LLMUserByokProfile)
        .filter(
            LLMUserByokProfile.user_id == current_user.id,
            LLMUserByokProfile.scenario == profile_data.tier.value,
        )
        .first()
    )

    if existing:
        # Update existing
        existing.provider = profile_data.provider
        existing.model = profile_data.model
        existing.api_key_encrypted = encrypt_api_key(profile_data.api_key)
        existing.api_base = profile_data.api_base
        existing.api_version = profile_data.api_version
        existing.enabled = profile_data.enabled
        db.commit()
        db.refresh(existing)
        logger.info(
            f"Updated BYOK profile: user_id={current_user.id}, scenario={profile_data.tier}"
        )
        return _profile_to_response(existing)
    else:
        # Create new
        profile = LLMUserByokProfile(
            user_id=current_user.id,
            scenario=profile_data.tier.value,
            provider=profile_data.provider,
            model=profile_data.model,
            api_key_encrypted=encrypt_api_key(profile_data.api_key),
            api_base=profile_data.api_base,
            api_version=profile_data.api_version,
            enabled=profile_data.enabled,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info(
            f"Created BYOK profile: user_id={current_user.id}, scenario={profile_data.tier}"
        )
        return _profile_to_response(profile)


@router.put(
    "/byok-profiles/{tier}",
    response_model=LLMUserByokProfileResponse,
)
async def upsert_byok_profile_by_tier(
    tier: str,
    profile_data: LLMUserByokProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Create or update BYOK profile for a tier (tier-based endpoint).

    api_key handling:
    - omitted: keep existing
    - null: treat as omitted (keep existing)
    - "": return 400 Bad Request
    - valid string: encrypt and store
    """
    # Validate tier
    if tier not in VALID_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}. Must be one of: {', '.join(VALID_TIERS)}",
        )

    require_entitlement(
        action=PolicyAction.SET_BYOK_KEY,
        request=request,
        db=db,
        current_user=current_user,
    )

    # Validate api_key if provided
    if profile_data.api_key == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key cannot be empty string. Omit the field to keep existing key.",
        )

    # Check for existing profile (using scenario field)
    existing = (
        db.query(LLMUserByokProfile)
        .filter(
            LLMUserByokProfile.user_id == current_user.id,
            LLMUserByokProfile.scenario == tier,
        )
        .first()
    )

    if existing:
        # Update existing
        existing.provider = profile_data.provider
        existing.model = profile_data.model
        existing.enabled = profile_data.enabled
        # Only update key if provided and not null
        if profile_data.api_key is not None:
            existing.api_key_encrypted = encrypt_api_key(profile_data.api_key)
        db.commit()
        db.refresh(existing)
        logger.info(f"Updated BYOK profile: user_id={current_user.id}, scenario={tier}")
        return _profile_to_response(existing)
    else:
        # Create new - require api_key for new profiles
        if profile_data.api_key is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="api_key is required when creating a new BYOK profile",
            )

        profile = LLMUserByokProfile(
            user_id=current_user.id,
            scenario=tier,
            provider=profile_data.provider,
            model=profile_data.model,
            api_key_encrypted=encrypt_api_key(profile_data.api_key),
            enabled=profile_data.enabled,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info(f"Created BYOK profile: user_id={current_user.id}, scenario={tier}")
        return _profile_to_response(profile)


@router.post(
    "/byok-profiles/{tier}/test",
    response_model=LLMUserByokProfileResponse,
)
async def test_byok_profile(
    tier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Test BYOK profile credentials ("credentials only" - ignores enabled flag).

    Makes minimal LLM call (1 token), persists result to DB.
    Returns updated profile with test results.
    """
    # Validate tier
    if tier not in VALID_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}. Must be one of: {', '.join(VALID_TIERS)}",
        )

    # Get profile (using scenario field)
    profile = (
        db.query(LLMUserByokProfile)
        .filter(
            LLMUserByokProfile.user_id == current_user.id,
            LLMUserByokProfile.scenario == tier,
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BYOK profile not found for scenario: {tier}",
        )

    # Decrypt API key
    try:
        api_key = decrypt_api_key(profile.api_key_encrypted)
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        profile.last_tested_at = datetime.now()
        profile.last_test_status = "fail"
        profile.last_test_code = ByokTestCode.INVALID_KEY.value
        profile.last_test_message = "Failed to decrypt stored API key"
        db.commit()
        db.refresh(profile)
        return _profile_to_response(profile)

    # Test the key with a minimal call
    test_code = ByokTestCode.OK
    test_message = "Test passed"
    test_status = "pass"

    try:
        # Import here to avoid circular imports
        import httpx

        # Prepare test request based on provider
        if profile.provider == "openai":
            base_url = profile.api_base or "https://api.openai.com/v1"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": profile.model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"
        elif profile.provider == "anthropic":
            base_url = profile.api_base or "https://api.anthropic.com"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": profile.api_version or "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": profile.model,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}],
            }
            url = f"{base_url.rstrip('/')}/v1/messages"
        elif profile.provider == "deepseek":
            base_url = profile.api_base or "https://api.deepseek.com/v1"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": profile.model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"
        else:
            # Generic OpenAI-compatible endpoint
            base_url = profile.api_base or "https://api.openai.com/v1"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": profile.model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"

        # Make test call
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            test_code = ByokTestCode.OK
            test_message = "API key validated successfully"
            test_status = "pass"
        elif response.status_code == 401:
            test_code = ByokTestCode.INVALID_KEY
            test_message = "Invalid API key"
            test_status = "fail"
        elif response.status_code == 429:
            test_code = ByokTestCode.RATE_LIMITED
            test_message = "Rate limited by provider"
            test_status = "fail"
        elif response.status_code == 404:
            test_code = ByokTestCode.MODEL_NOT_FOUND
            test_message = f"Model not found: {profile.model}"
            test_status = "fail"
        else:
            test_code = ByokTestCode.PROVIDER_ERROR
            try:
                error_detail = response.json().get("error", {}).get("message", response.text[:100])
            except Exception:
                error_detail = response.text[:100]
            test_message = f"Provider error ({response.status_code}): {error_detail}"
            test_status = "fail"

    except httpx.TimeoutException:
        test_code = ByokTestCode.NETWORK_ERROR
        test_message = "Request timed out"
        test_status = "fail"
    except httpx.RequestError as e:
        test_code = ByokTestCode.NETWORK_ERROR
        test_message = f"Network error: {str(e)[:100]}"
        test_status = "fail"
    except Exception as e:
        test_code = ByokTestCode.PROVIDER_ERROR
        test_message = f"Unexpected error: {str(e)[:100]}"
        test_status = "fail"

    # Update profile with test results
    profile.last_tested_at = datetime.now()
    profile.last_test_status = test_status
    profile.last_test_code = test_code.value
    profile.last_test_message = test_message
    db.commit()
    db.refresh(profile)

    logger.info(
        f"Tested BYOK profile: user_id={current_user.id}, tier={tier}, "
        f"status={test_status}, code={test_code.value}"
    )

    return _profile_to_response(profile)


@router.delete("/byok-profiles/{tier}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_byok_profile_by_tier(
    tier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete BYOK profile by tier (scenario)."""
    # Validate tier
    if tier not in VALID_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}. Must be one of: {', '.join(VALID_TIERS)}",
        )

    # Query using scenario field
    profile = (
        db.query(LLMUserByokProfile)
        .filter(
            LLMUserByokProfile.user_id == current_user.id,
            LLMUserByokProfile.scenario == tier,
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BYOK profile not found for scenario: {tier}",
        )

    db.delete(profile)
    db.commit()
    logger.info(f"Deleted BYOK profile: scenario={tier}, user_id={current_user.id}")


@router.delete("/byok-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_byok_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete BYOK profile by ID (legacy endpoint)."""
    profile = (
        db.query(LLMUserByokProfile)
        .filter(
            LLMUserByokProfile.id == profile_id,
            LLMUserByokProfile.user_id == current_user.id,
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="BYOK profile not found"
        )

    db.delete(profile)
    db.commit()
    logger.info(f"Deleted BYOK profile: id={profile_id}, user_id={current_user.id}")


# ============================================================================
# Routing Override Management (User Endpoints)
# ============================================================================


@router.get(
    "/routing-overrides", response_model=List[LLMRoutingOverrideResponse]
)
async def list_routing_overrides(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[LLMRoutingOverride]:
    """List user's routing overrides."""
    overrides = (
        db.query(LLMRoutingOverride)
        .filter(LLMRoutingOverride.user_id == current_user.id)
        .all()
    )
    return overrides


@router.post(
    "/routing-overrides",
    response_model=LLMRoutingOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_routing_override(
    override_data: LLMRoutingOverrideCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LLMRoutingOverride:
    """
    Create or update routing override for a scope.

    If override already exists for this scope, updates it (upsert behavior).
    """
    # Check for existing override
    existing = (
        db.query(LLMRoutingOverride)
        .filter(
            LLMRoutingOverride.user_id == current_user.id,
            LLMRoutingOverride.scope == override_data.scope.value,
        )
        .first()
    )

    if existing:
        # Update existing
        existing.mode = RoutingModeEnum[override_data.mode.name]
        existing.updated_by = current_user.email or str(current_user.id)
        db.commit()
        db.refresh(existing)
        logger.info(
            f"Updated routing override: user_id={current_user.id}, "
            f"scope={override_data.scope}, mode={override_data.mode}"
        )
        return existing
    else:
        # Create new
        override = LLMRoutingOverride(
            user_id=current_user.id,
            scope=override_data.scope.value,
            mode=RoutingModeEnum[override_data.mode.name],
            updated_by=current_user.email or str(current_user.id),
        )
        db.add(override)
        db.commit()
        db.refresh(override)
        logger.info(
            f"Created routing override: user_id={current_user.id}, "
            f"scope={override_data.scope}, mode={override_data.mode}"
        )
        return override


@router.delete(
    "/routing-overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_routing_override(
    override_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete routing override."""
    override = (
        db.query(LLMRoutingOverride)
        .filter(
            LLMRoutingOverride.id == override_id,
            LLMRoutingOverride.user_id == current_user.id,
        )
        .first()
    )

    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Routing override not found",
        )

    db.delete(override)
    db.commit()
    logger.info(
        f"Deleted routing override: id={override_id}, user_id={current_user.id}"
    )


# ============================================================================
# Virtual Key Status (User Endpoints - Read-Only)
# ============================================================================


@router.get("/virtual-keys", response_model=List[LLMVirtualKeyResponse])
async def list_virtual_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[LLMVirtualKey]:
    """
    List user's virtual key status (read-only).

    Actual keys NEVER returned - only status, type, and allowed models.
    """
    keys = (
        db.query(LLMVirtualKey)
        .filter(LLMVirtualKey.user_id == current_user.id)
        .all()
    )
    return keys


# ============================================================================
# System Profile Management (Admin Endpoints)
# TODO: Add admin role check via dependency
# ============================================================================


class SystemLLMConfigResponse(BaseModel):
    """Response for system LLM configuration."""
    scope: str
    provider: str
    model: str
    base_url: Optional[str] = None
    temperature: float
    max_tokens: Optional[int] = None
    api_key_masked: str


class SystemConfigReloadResponse(BaseModel):
    """Response for system config reload."""
    status: str
    loaded_scopes: List[str]
    errors: List[dict]
    configs: dict


@router.get("/system-config", response_model=dict)
async def get_system_config(
    current_user: User = Depends(get_current_user),
    # TODO: Add admin role check
) -> dict:
    """
    Get current system LLM configuration (admin only).

    Returns all configured system scopes with masked API keys.
    """
    from AICrews.llm.system_config import get_system_llm_config_store, SYSTEM_SCOPES

    store = get_system_llm_config_store()
    configs = store.get_all_configs(mask_keys=True)

    # Add unconfigured scopes
    all_scopes = {}
    for scope in SYSTEM_SCOPES:
        if scope in configs:
            all_scopes[scope] = {
                "configured": True,
                **configs[scope],
            }
        else:
            all_scopes[scope] = {
                "configured": False,
                "provider": None,
                "model": None,
            }

    return {
        "scopes": all_scopes,
        "configured_count": len(configs),
        "total_scopes": len(SYSTEM_SCOPES),
    }


@router.get("/system-profiles", response_model=List[LLMSystemProfileResponse])
async def list_system_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[LLMSystemProfile]:
    """
    List all system profiles (admin only).

    TODO: Add admin role check.
    """
    profiles = db.query(LLMSystemProfile).all()
    return profiles


@router.put(
    "/system-profiles/{scope}",
    response_model=LLMSystemProfileResponse,
)
async def update_system_profile(
    scope: str,
    proxy_model_name: str,
    enabled: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LLMSystemProfile:
    """
    Update system profile for a scope (admin only).

    Creates profile if it doesn't exist (upsert behavior).
    TODO: Add admin role check.
    """
    # Validate scope
    try:
        LLMScope(scope)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {scope}",
        )

    # Check for existing profile
    profile = db.query(LLMSystemProfile).filter_by(scope=scope).first()

    if profile:
        # Update existing
        profile.proxy_model_name = proxy_model_name
        profile.enabled = enabled
        profile.updated_by = current_user.email or str(current_user.id)
        db.commit()
        db.refresh(profile)
        logger.info(
            f"Updated system profile: scope={scope}, model={proxy_model_name}"
        )
        return profile
    else:
        # Create new
        profile = LLMSystemProfile(
            scope=scope,
            proxy_model_name=proxy_model_name,
            enabled=enabled,
            updated_by=current_user.email or str(current_user.id),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info(
            f"Created system profile: scope={scope}, model={proxy_model_name}"
        )
        return profile


# ============================================================================
# System LLM Config Hot Reload (Environment Variables)
# ============================================================================


@router.post("/system-config/reload", response_model=SystemConfigReloadResponse)
async def reload_system_llm_config() -> SystemConfigReloadResponse:
    """
    Hot reload system LLM configuration from environment variables.

    This endpoint:
    1. Reloads .env file into the process environment
    2. Clears the SystemLLMConfigStore cache
    3. Returns list of available scopes after reload

    Use this after updating FAIC_LLM_* variables in .env file.
    """
    from dotenv import load_dotenv
    from AICrews.llm.system_config import get_system_llm_config_store

    # Reload .env file (override=True to update existing vars)
    load_dotenv(override=True)
    logger.info("Reloaded .env file into process environment")

    # Clear the config store cache and reload
    store = get_system_llm_config_store()
    result = store.reload()

    # Get all configs with masked keys for response
    configs = store.get_all_configs()

    logger.info(
        f"System LLM config reloaded: "
        f"{len(result['loaded_scopes'])} scopes loaded, {len(result['errors'])} errors"
    )

    return SystemConfigReloadResponse(
        status=result["status"],
        loaded_scopes=result["loaded_scopes"],
        errors=result["errors"],
        configs=configs,
    )
