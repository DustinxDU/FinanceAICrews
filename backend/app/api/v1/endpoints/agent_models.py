"""
Agent Models API Endpoints

This module provides REST APIs for managing agent model configurations.
Users can configure which LLM provider and model to use for each agent scenario:
- agents_fast: Quick tasks, lower cost
- agents_balanced: Balance between speed and quality
- agents_best: Premium quality analysis

Key features:
- References existing UserLLMConfig (no duplicate API key storage)
- Supports Volcano Engine endpoint selection
- Provides test functionality for each scenario
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.security import get_current_user, get_db
from AICrews.database.models.user import User
from AICrews.database.models.llm import UserLLMConfig, UserModelConfig, LLMProvider
from AICrews.database.models.llm_policy import LLMUserByokProfile
from AICrews.utils.encryption import decrypt_api_key
from AICrews.llm.core.config_store import get_config_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent-models", tags=["Agent Models"])


# Valid scenarios
VALID_SCENARIOS = {"agents_fast", "agents_balanced", "agents_best"}

# Scenario display info
SCENARIO_INFO = {
    "agents_fast": {
        "name": "Agents - Fast",
        "description": "Quick tasks with lower cost",
        "icon": "⚡"
    },
    "agents_balanced": {
        "name": "Agents - Balanced",
        "description": "Balance between speed and quality",
        "icon": "⚖️"
    },
    "agents_best": {
        "name": "Agents - Best",
        "description": "Premium quality analysis",
        "icon": "🏆"
    }
}


# ============================================================================
# Request/Response Models (imported from AICrews.schemas.llm_policy)
# These schemas are defined in AICrews/schemas/llm_policy.py
from AICrews.schemas.llm_policy import (
    ProviderSummary,
    ModelSummary,
    AgentModelConfig,
    AgentModelsResponse,
    UpdateAgentModelRequest,
    TestResultResponse,
    ToggleByokRequest,
    ToggleByokResponse,
)


# ============================================================================
# Helper Functions
# ============================================================================

def _get_provider_summary(config: UserLLMConfig, db: Session) -> ProviderSummary:
    """Convert UserLLMConfig to ProviderSummary."""
    provider = db.query(LLMProvider).filter(LLMProvider.id == config.provider_id).first()
    provider_name = provider.display_name if provider else "Unknown"
    provider_key = provider.provider_key if provider else ""

    # Count available models (not just active ones)
    model_count = db.query(UserModelConfig).filter(
        UserModelConfig.llm_config_id == config.id,
        UserModelConfig.is_available == True
    ).count()

    # Get endpoints for Volcano Engine
    endpoints = None
    if provider_key == "volcengine":
        endpoint_configs = db.query(UserModelConfig).filter(
            UserModelConfig.llm_config_id == config.id,
            UserModelConfig.volcengine_endpoint_id.isnot(None)
        ).all()
        endpoints = list(set(ec.volcengine_endpoint_id for ec in endpoint_configs if ec.volcengine_endpoint_id))

    return ProviderSummary(
        config_id=config.id,
        provider_key=provider_key,
        provider_name=provider_name,
        is_validated=config.is_validated,
        model_count=model_count,
        endpoints=endpoints
    )


def _get_scenario_config(
    scenario: str,
    user_id: int,
    db: Session
) -> AgentModelConfig:
    """Get configuration for a specific scenario."""
    info = SCENARIO_INFO.get(scenario, {})

    # Find existing profile by scenario field
    # Note: tier fallback removed - all profiles have scenario set via migration 8e239749edcd
    profile = db.query(LLMUserByokProfile).filter(
        LLMUserByokProfile.user_id == user_id,
        LLMUserByokProfile.scenario == scenario
    ).first()

    config = AgentModelConfig(
        scenario=scenario,
        scenario_name=info.get("name", scenario),
        scenario_description=info.get("description", ""),
        scenario_icon=info.get("icon", "🤖"),
        enabled=False
    )

    if profile:
        config.enabled = profile.enabled
        config.last_tested_at = profile.last_tested_at
        config.last_test_status = profile.last_test_status
        config.last_test_message = profile.last_test_message
        config.volcengine_endpoint = profile.volcengine_endpoint

        # Get provider info from new fields
        if profile.provider_config_id:
            config.provider_config_id = profile.provider_config_id
            provider_config = db.query(UserLLMConfig).filter(
                UserLLMConfig.id == profile.provider_config_id
            ).first()
            if provider_config:
                provider = db.query(LLMProvider).filter(
                    LLMProvider.id == provider_config.provider_id
                ).first()
                config.provider_name = provider.display_name if provider else None

        if profile.model_config_id:
            config.model_config_id = profile.model_config_id
            model_config = db.query(UserModelConfig).filter(
                UserModelConfig.id == profile.model_config_id
            ).first()
            if model_config and model_config.model:
                config.model_name = model_config.model.display_name

        # Fallback to legacy fields if new fields not set
        if not config.provider_name and profile.provider:
            config.provider_name = profile.provider
        if not config.model_name and profile.model:
            config.model_name = profile.model

    return config


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=AgentModelsResponse)
async def list_agent_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentModelsResponse:
    """
    List all agent model configurations for the current user.

    Returns:
    - use_own_llm_keys: Global BYOK toggle status
    - scenarios: Configuration for each agent scenario (fast, balanced, best)
    - available_providers: List of validated providers for dropdown selection
    """
    # Get all scenarios
    scenarios = [
        _get_scenario_config(scenario, current_user.id, db)
        for scenario in VALID_SCENARIOS
    ]

    # Get validated providers
    provider_configs = db.query(UserLLMConfig).filter(
        UserLLMConfig.user_id == current_user.id,
        UserLLMConfig.is_active == True,
        UserLLMConfig.is_validated == True
    ).all()

    available_providers = [
        _get_provider_summary(config, db)
        for config in provider_configs
    ]

    return AgentModelsResponse(
        use_own_llm_keys=current_user.use_own_llm_keys,
        scenarios=scenarios,
        available_providers=available_providers
    )


@router.put("/toggle-byok", response_model=ToggleByokResponse)
async def toggle_byok_mode(
    request: ToggleByokRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToggleByokResponse:
    """
    Toggle the global BYOK (Bring Your Own Key) mode for the current user.
    
    When enabled, the user's configured API keys will be used for agent LLM calls.
    When disabled, the system's official models will be used instead.
    
    This is the master switch - individual scenario configurations still need
    to be set up for BYOK to work when enabled.
    """
    # Update user's BYOK preference
    current_user.use_own_llm_keys = request.enabled
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"User {current_user.id} toggled BYOK mode to {request.enabled}")
    
    return ToggleByokResponse(
        success=True,
        use_own_llm_keys=current_user.use_own_llm_keys,
        message="BYOK mode enabled - your API keys will be used for agent calls" 
                if request.enabled 
                else "BYOK mode disabled - using official system models"
    )


@router.get("/providers/{config_id}/models", response_model=List[ModelSummary])
async def list_provider_models(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ModelSummary]:
    """
    List available models for a specific provider config.

    Used to populate the model dropdown when user selects a provider.
    """
    # Verify ownership
    provider_config = db.query(UserLLMConfig).filter(
        UserLLMConfig.id == config_id,
        UserLLMConfig.user_id == current_user.id
    ).first()

    if not provider_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    # Get available models (is_available=True, regardless of is_active)
    # Users can select any available model for agent scenarios
    model_configs = db.query(UserModelConfig).filter(
        UserModelConfig.llm_config_id == config_id,
        UserModelConfig.is_available == True
    ).all()

    return [
        ModelSummary(
            model_config_id=mc.id,
            model_key=mc.model.model_key if mc.model else "",
            model_name=mc.model.display_name if mc.model else "",
            context_length=mc.model.context_length if mc.model else None,
            volcengine_endpoint_id=mc.volcengine_endpoint_id
        )
        for mc in model_configs
    ]


@router.put("/{scenario}", response_model=AgentModelConfig)
async def update_agent_model(
    scenario: str,
    request: UpdateAgentModelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentModelConfig:
    """
    Update agent model configuration for a specific scenario.

    Creates a new profile if one doesn't exist, or updates the existing one.
    """
    # Validate scenario
    if scenario not in VALID_SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario: {scenario}. Must be one of: {', '.join(VALID_SCENARIOS)}"
        )

    # Verify provider config ownership
    provider_config = db.query(UserLLMConfig).filter(
        UserLLMConfig.id == request.provider_config_id,
        UserLLMConfig.user_id == current_user.id
    ).first()

    if not provider_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    # Verify model config ownership
    model_config = db.query(UserModelConfig).filter(
        UserModelConfig.id == request.model_config_id,
        UserModelConfig.user_id == current_user.id
    ).first()

    if not model_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model configuration not found"
        )

    # Get provider info for legacy fields
    provider = db.query(LLMProvider).filter(
        LLMProvider.id == provider_config.provider_id
    ).first()
    provider_key = provider.provider_key if provider else "unknown"
    model_key = model_config.model.model_key if model_config.model else "unknown"

    # Find or create profile by scenario field
    # Note: tier fallback removed - all profiles have scenario set via migration 8e239749edcd
    profile = db.query(LLMUserByokProfile).filter(
        LLMUserByokProfile.user_id == current_user.id,
        LLMUserByokProfile.scenario == scenario
    ).first()

    if profile:
        # Update existing
        profile.scenario = scenario
        profile.provider_config_id = request.provider_config_id
        profile.model_config_id = request.model_config_id
        profile.volcengine_endpoint = request.volcengine_endpoint
        profile.enabled = request.enabled
        # Clear old test status when configuration changes
        profile.last_test_status = None
        profile.last_test_message = None
        profile.last_tested_at = None
        # Note: Legacy provider/model fields no longer written (Phase 4.5)
        # New records use provider_config_id and model_config_id only
        logger.info(f"Updated agent model: user_id={current_user.id}, scenario={scenario}")
    else:
        # Create new
        profile = LLMUserByokProfile(
            user_id=current_user.id,
            scenario=scenario,
            tier=scenario,  # Legacy field kept for backward compatibility
            provider_config_id=request.provider_config_id,
            model_config_id=request.model_config_id,
            volcengine_endpoint=request.volcengine_endpoint,
            enabled=request.enabled,
            # Note: Legacy provider/model fields no longer set (Phase 4.5)
        )
        db.add(profile)
        logger.info(f"Created agent model: user_id={current_user.id}, scenario={scenario}")

    db.commit()
    db.refresh(profile)

    return _get_scenario_config(scenario, current_user.id, db)


@router.post("/{scenario}/test", response_model=TestResultResponse)
async def test_agent_model(
    scenario: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestResultResponse:
    """
    Test the agent model configuration for a specific scenario.

    Makes a minimal LLM call to verify the configuration works.
    """
    import time
    import httpx

    # Validate scenario
    if scenario not in VALID_SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario: {scenario}. Must be one of: {', '.join(VALID_SCENARIOS)}"
        )

    # Find profile by scenario field
    # Note: tier fallback removed - all profiles have scenario set via migration 8e239749edcd
    profile = db.query(LLMUserByokProfile).filter(
        LLMUserByokProfile.user_id == current_user.id,
        LLMUserByokProfile.scenario == scenario
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No configuration found for scenario: {scenario}"
        )

    # Get provider config for API key
    if not profile.provider_config_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile not configured with provider reference"
        )

    provider_config = db.query(UserLLMConfig).filter(
        UserLLMConfig.id == profile.provider_config_id
    ).first()

    if not provider_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    # Get provider info
    provider = db.query(LLMProvider).filter(
        LLMProvider.id == provider_config.provider_id
    ).first()
    provider_key = provider.provider_key if provider else "openai"

    # Get model info
    model_key = profile.model
    if profile.model_config_id:
        model_config = db.query(UserModelConfig).filter(
            UserModelConfig.id == profile.model_config_id
        ).first()
        if model_config and model_config.model:
            model_key = model_config.model.model_key

    # Perform test
    start_time = time.time()
    test_status = "pass"
    test_message = "Test passed"

    try:
        # Decrypt the API key (stored encrypted in database)
        try:
            api_key = decrypt_api_key(provider_config.api_key)
        except Exception as decrypt_err:
            logger.error(f"Failed to decrypt API key for provider config {provider_config.id}: {type(decrypt_err).__name__}: {decrypt_err}")
            test_status = "fail"
            test_message = "Failed to decrypt API key. The encryption key may have changed since the key was saved. Please re-save your API key in the API Keys tab."
            # Skip the rest of the test
            profile.last_tested_at = datetime.now()
            profile.last_test_status = test_status
            profile.last_test_message = test_message
            db.commit()
            return TestResultResponse(
                scenario=scenario,
                success=False,
                message=test_message,
                latency_ms=int((time.time() - start_time) * 1000)
            )

        # Get default base URL from providers.yaml config
        config_store = get_config_store()
        yaml_provider_config = config_store.get_provider(provider_key)
        default_base_url = yaml_provider_config.endpoints.api_base if yaml_provider_config else None

        # Use user's configured base_url, or fall back to providers.yaml default
        base_url = provider_config.base_url or default_base_url

        # Prepare test request based on provider
        if provider_key == "anthropic":
            # Anthropic uses a different API format
            if not base_url:
                base_url = "https://api.anthropic.com"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_key,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}],
            }
            url = f"{base_url.rstrip('/')}/v1/messages"
        elif provider_key == "volcengine":
            # Volcano Engine uses endpoint-based routing
            endpoint = profile.volcengine_endpoint
            if not endpoint:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Volcano Engine requires an endpoint"
                )
            if not base_url:
                base_url = "https://ark.cn-beijing.volces.com/api/v3"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": endpoint,  # Volcano Engine uses endpoint as model
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"
        else:
            # OpenAI and OpenAI-compatible providers (including Chinese providers)
            if not base_url:
                test_status = "fail"
                test_message = f"Provider '{provider_key}' requires a base URL. Please configure it in providers.yaml or set a custom base URL."
                profile.last_tested_at = datetime.now()
                profile.last_test_status = test_status
                profile.last_test_message = test_message
                db.commit()
                return TestResultResponse(
                    scenario=scenario,
                    success=False,
                    message=test_message,
                    latency_ms=int((time.time() - start_time) * 1000)
                )
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": model_key,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"

        # Make test call
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            test_status = "pass"
            test_message = "Configuration validated successfully"
        elif response.status_code == 401:
            test_status = "fail"
            test_message = "Invalid API key"
        elif response.status_code == 429:
            test_status = "fail"
            test_message = "Rate limited by provider"
        elif response.status_code == 404:
            test_status = "fail"
            test_message = f"Model not found: {model_key}"
        else:
            test_status = "fail"
            try:
                error_detail = response.json().get("error", {}).get("message", response.text[:100])
            except Exception:
                error_detail = response.text[:100]
            test_message = f"Provider error ({response.status_code}): {error_detail}"

    except httpx.TimeoutException:
        test_status = "fail"
        test_message = "Request timed out"
    except httpx.RequestError as e:
        test_status = "fail"
        test_message = f"Network error: {str(e)[:100]}"
    except Exception as e:
        test_status = "fail"
        test_message = f"Unexpected error: {str(e)[:100]}"

    latency_ms = int((time.time() - start_time) * 1000)

    # Update profile with test results
    profile.last_tested_at = datetime.now()
    profile.last_test_status = test_status
    profile.last_test_message = test_message
    db.commit()

    logger.info(
        f"Tested agent model: user_id={current_user.id}, scenario={scenario}, "
        f"status={test_status}, latency={latency_ms}ms"
    )

    return TestResultResponse(
        scenario=scenario,
        success=test_status == "pass",
        message=test_message,
        latency_ms=latency_ms
    )


@router.delete("/{scenario}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_model(
    scenario: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete agent model configuration for a specific scenario.
    """
    # Validate scenario
    if scenario not in VALID_SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario: {scenario}. Must be one of: {', '.join(VALID_SCENARIOS)}"
        )

    # Find profile by scenario field
    # Note: tier fallback removed - all profiles have scenario set via migration 8e239749edcd
    profile = db.query(LLMUserByokProfile).filter(
        LLMUserByokProfile.user_id == current_user.id,
        LLMUserByokProfile.scenario == scenario
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No configuration found for scenario: {scenario}"
        )

    db.delete(profile)
    db.commit()
    logger.info(f"Deleted agent model: user_id={current_user.id}, scenario={scenario}")
