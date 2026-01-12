"""
System LLM Helper Functions

Provides convenient functions for services to get LLM instances
using the new environment-based configuration system.
"""

from AICrews.observability.logging import get_logger
from typing import Any, Optional

from AICrews.schemas.llm_policy import LLMScope

logger = get_logger(__name__)


def get_system_llm(
    scope: LLMScope,
    custom_tags: Optional[list] = None,
) -> Any:
    """
    Get an LLM instance for a system-managed scope.

    This is the recommended way for services to get LLM instances for
    system scopes (copilot, scans, crew, agent tiers).

    Priority:
    1. Environment-based config (FAIC_LLM_{SCOPE}_*) - supports hot updates
    2. Falls back to error if not configured

    Args:
        scope: The LLM scope (e.g., LLMScope.COPILOT, LLMScope.QUICK_SCAN)
        custom_tags: Optional custom tags for logging/tracing

    Returns:
        CrewAI LLM instance ready for use

    Raises:
        ValueError: If no configuration found for scope

    Example:
        from AICrews.llm.helpers import get_system_llm
        from AICrews.schemas.llm_policy import LLMScope

        llm = get_system_llm(LLMScope.COPILOT)
        response = await llm.ainvoke("Hello!")
    """
    from AICrews.llm.policy_router import LLMPolicyRouter
    from AICrews.llm.unified_manager import get_unified_llm_manager

    # Check if env-based config exists
    if not LLMPolicyRouter.is_env_configured(scope):
        raise ValueError(
            f"No environment configuration found for scope '{scope.value}'. "
            f"Please set FAIC_LLM_{scope.value.upper()}_PROVIDER and related env vars."
        )

    # Create router (we only need it for resolve_system_direct)
    router = LLMPolicyRouter(
        proxy_base_url="",  # Not used for direct resolution
        encryption_key=b"",  # Not used for direct resolution
    )

    # Resolve to DirectLLMCall
    direct_call = router.resolve_system_direct(
        scope=scope,
        custom_tags=custom_tags,
    )

    logger.debug(
        "Creating system LLM: scope=%s, provider=%s, model=%s",
        scope.value,
        direct_call.provider,
        direct_call.model,
    )

    # Create LLM instance
    manager = get_unified_llm_manager()
    return manager.create_default_llm(**direct_call.to_llm_params())


def get_system_llm_or_none(
    scope: LLMScope,
    custom_tags: Optional[list] = None,
) -> Optional[Any]:
    """
    Get an LLM instance for a system-managed scope, or None if not configured.

    Same as get_system_llm but returns None instead of raising an error.
    Useful for optional LLM features.

    Args:
        scope: The LLM scope
        custom_tags: Optional custom tags

    Returns:
        CrewAI LLM instance or None if not configured
    """
    try:
        return get_system_llm(scope, custom_tags)
    except ValueError:
        return None


def is_system_llm_configured(scope: LLMScope) -> bool:
    """
    Check if a system scope has environment-based configuration.

    Args:
        scope: The LLM scope to check

    Returns:
        True if configured, False otherwise
    """
    from AICrews.llm.policy_router import LLMPolicyRouter
    return LLMPolicyRouter.is_env_configured(scope)


def get_system_llm_config(scope: LLMScope) -> Optional[dict]:
    """
    Get the configuration for a system scope (without creating LLM).

    Useful for debugging or displaying configuration in admin UI.

    Args:
        scope: The LLM scope

    Returns:
        Config dict with masked API key, or None if not configured
    """
    from AICrews.llm.system_config import get_system_llm_config_store

    store = get_system_llm_config_store()
    config = store.get_config_or_none(scope.value)

    if config:
        return config.to_dict(mask_key=True)
    return None
