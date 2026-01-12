"""
System LLM Configuration from Environment Variables.

Provides hot-reloadable configuration for system-managed LLM scopes.
This module reads FAIC_LLM_* environment variables and provides a unified
interface for getting LLM configuration.

Environment Variable Schema:
    FAIC_LLM_{SCOPE}_PROVIDER=openai
    FAIC_LLM_{SCOPE}_MODEL=gpt-4o-mini
    FAIC_LLM_{SCOPE}_API_KEY=sk-xxx
    FAIC_LLM_{SCOPE}_BASE_URL=https://api.openai.com/v1  # optional
    FAIC_LLM_{SCOPE}_TEMPERATURE=0.7  # optional
    FAIC_LLM_{SCOPE}_ENABLE_THINKING=false  # optional, for thinking models (GLM-4.6, DeepSeek-R1)

Fallback Chain:
    1. Scope-specific: FAIC_LLM_COPILOT_*
    2. Group fallback: FAIC_LLM_SCAN_* for quick_scan/chart_scan
    3. Provider API key: {PROVIDER}_API_KEY (e.g., OPENAI_API_KEY)
    4. Global default: FAIC_LLM_DEFAULT_*
"""

import os
from AICrews.observability.logging import get_logger
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Any, Union

logger = get_logger(__name__)


# All system scopes that can be configured via environment variables
SYSTEM_SCOPES = [
    "copilot",
    "quick_scan",
    "chart_scan",
    "cockpit_scan",
    "crew_router",
    "crew_summary",
    "agents_fast",
    "agents_balanced",
    "agents_best",
]

# Scope to group mapping for fallback chain
# Scopes in the same group share fallback configuration (e.g., FAIC_LLM_SCAN_*)
SCOPE_GROUPS: Dict[str, str] = {
    "quick_scan": "scan",
    "chart_scan": "scan",
    "cockpit_scan": "scan",
    "crew_router": "crew",
    "crew_summary": "crew",
    # copilot, agents_* have no group fallback
}

# Provider to API key env var mapping
PROVIDER_API_KEY_ENV_VARS: Dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "google": "GOOGLE_API_KEY",
    "azure": "AZURE_OPENAI_API_KEY",
    "volcengine": "VOLCENGINE_API_KEY",
    "zhipu": "ZHIPU_API_KEY",
}


@dataclass
class SystemLLMConfig:
    """Configuration for a system-managed LLM scope."""
    provider: str
    model: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    enable_thinking: bool = False  # For thinking models (GLM-4.6, DeepSeek-R1)

    def to_dict(self, mask_key: bool = True) -> Dict[str, Any]:
        """
        Convert to dictionary, optionally masking the API key.

        Args:
            mask_key: If True, mask the API key (show first 4 and last 4 chars)

        Returns:
            Dictionary representation of the config
        """
        result = asdict(self)
        if mask_key:
            result["api_key"] = self._mask_api_key(self.api_key)
        return result

    @staticmethod
    def _mask_api_key(key: str) -> str:
        """Mask API key, showing first 4 and last 4 characters."""
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"


class SystemLLMConfigStore:
    """
    Singleton store for system LLM configurations.
    Reads from environment variables with caching and hot-reload support.
    """

    # Scope string to env var prefix mapping (for fallback groups)
    SCOPE_FALLBACK_MAP: Dict[str, List[str]] = {
        "quick_scan": ["QUICK_SCAN", "SCAN"],
        "chart_scan": ["CHART_SCAN", "SCAN"],
        "copilot": ["COPILOT"],
        "cockpit_scan": ["COCKPIT_SCAN", "SCAN"],
        "crew_router": ["CREW_ROUTER", "CREW"],
        "crew_summary": ["CREW_SUMMARY", "CREW"],
        "agents_fast": ["AGENTS_FAST", "AGENTS"],
        "agents_balanced": ["AGENTS_BALANCED", "AGENTS"],
        "agents_best": ["AGENTS_BEST", "AGENTS"],
    }

    def __init__(self):
        self._cache: Dict[str, SystemLLMConfig] = {}

    def get_config(self, scope: str) -> SystemLLMConfig:
        """
        Get config for scope, with fallback chain.

        Args:
            scope: Scope name as string (e.g., "copilot", "quick_scan")

        Fallback order:
        1. Scope-specific env vars (e.g., FAIC_LLM_COPILOT_*)
        2. Group fallback (e.g., FAIC_LLM_SCAN_* for quick_scan/chart_scan)
        3. Global default (FAIC_LLM_DEFAULT_*)

        Raises:
            ValueError: If no configuration found for scope
        """
        # Normalize scope to string
        scope_str = scope.value if hasattr(scope, 'value') else str(scope)

        # Check cache first
        if scope_str in self._cache:
            return self._cache[scope_str]

        # Get fallback prefixes for this scope
        prefixes = list(self.SCOPE_FALLBACK_MAP.get(scope_str, [scope_str.upper()]))
        prefixes.append("DEFAULT")  # Always add DEFAULT as last fallback

        config = None
        for prefix in prefixes:
            config = self._try_load_from_env(prefix)
            if config:
                logger.debug(f"Loaded config for {scope_str} from FAIC_LLM_{prefix}_*")
                break

        if not config:
            raise ValueError(
                f"No LLM configuration found for scope '{scope_str}'. "
                f"Set FAIC_LLM_{scope_str.upper()}_PROVIDER and related env vars."
            )

        # Cache the config
        self._cache[scope_str] = config
        return config

    def get_config_or_none(self, scope: str) -> Optional[SystemLLMConfig]:
        """
        Get config for scope, returning None if not configured.

        Args:
            scope: Scope name as string

        Returns:
            SystemLLMConfig or None if not configured
        """
        try:
            return self.get_config(scope)
        except ValueError:
            return None

    def _try_load_from_env(self, prefix: str) -> Optional[SystemLLMConfig]:
        """Try to load config from environment variables with given prefix."""
        provider = os.getenv(f"FAIC_LLM_{prefix}_PROVIDER")
        model = os.getenv(f"FAIC_LLM_{prefix}_MODEL")
        api_key = os.getenv(f"FAIC_LLM_{prefix}_API_KEY")

        if not provider or not model:
            return None

        # If no API key specified, try provider-specific fallback
        if not api_key and provider:
            provider_lower = provider.lower()
            env_var_name = PROVIDER_API_KEY_ENV_VARS.get(provider_lower)
            if env_var_name:
                api_key = os.getenv(env_var_name)

        if not api_key:
            return None

        base_url = os.getenv(f"FAIC_LLM_{prefix}_BASE_URL")
        temperature_str = os.getenv(f"FAIC_LLM_{prefix}_TEMPERATURE")
        max_tokens_str = os.getenv(f"FAIC_LLM_{prefix}_MAX_TOKENS")
        enable_thinking_str = os.getenv(f"FAIC_LLM_{prefix}_ENABLE_THINKING")

        # Parse temperature with error handling
        temperature = 0.7
        if temperature_str:
            try:
                temperature = float(temperature_str)
            except ValueError:
                logger.warning(f"Invalid temperature value '{temperature_str}', using default 0.7")
                temperature = 0.7

        max_tokens = int(max_tokens_str) if max_tokens_str else None
        enable_thinking = enable_thinking_str.lower() in ("true", "1", "yes") if enable_thinking_str else False

        return SystemLLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
        )

    def reload(self, skip_dotenv: bool = False) -> Dict[str, Any]:
        """
        Force reload from environment (hot update).

        This method:
        1. Reloads .env file to update os.environ (unless skip_dotenv=True)
        2. Clears the config cache
        3. Attempts to load all scopes

        Args:
            skip_dotenv: If True, skip reloading .env file (useful for testing)

        Returns:
            Dict with status, loaded_scopes, and errors
        """
        # Reload .env file to update environment variables
        if not skip_dotenv:
            try:
                from dotenv import load_dotenv
                from pathlib import Path

                # Find .env file - check multiple possible locations
                possible_paths = [
                    Path(__file__).parent.parent.parent / ".env",  # Project root
                    Path.cwd() / ".env",  # Current working directory
                ]

                env_loaded = False
                for env_path in possible_paths:
                    if env_path.exists():
                        load_dotenv(env_path, override=True)
                        logger.info(f"Reloaded .env file from: {env_path}")
                        env_loaded = True
                        break

                if not env_loaded:
                    logger.warning(f".env file not found in: {possible_paths}")

            except ImportError:
                logger.warning("python-dotenv not installed, cannot reload .env file")

        self._cache.clear()
        logger.info("SystemLLMConfigStore cache cleared - will reload on next access")

        # Try loading all scopes and track results
        loaded_scopes = []
        errors = []

        for scope in SYSTEM_SCOPES:
            try:
                self.get_config(scope)
                loaded_scopes.append(scope)
            except ValueError as e:
                # Scope not configured, which is OK
                pass
            except Exception as e:
                errors.append({"scope": scope, "error": str(e)})

        return {
            "status": "reloaded",
            "loaded_scopes": loaded_scopes,
            "errors": errors,
        }

    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all configured scopes (for admin UI).

        Returns:
            Dict mapping scope names to their config dictionaries (with masked keys)
        """
        configs = {}
        for scope in SYSTEM_SCOPES:
            try:
                config = self.get_config(scope)
                configs[scope] = config.to_dict(mask_key=True)
            except ValueError:
                # Scope not configured
                pass
        return configs

    def is_configured(self, scope: str) -> bool:
        """
        Check if a scope has environment-based configuration.

        Args:
            scope: Scope name as string

        Returns:
            True if configured, False otherwise
        """
        return self.get_config_or_none(scope) is not None


# Singleton instance
_store: Optional[SystemLLMConfigStore] = None


def get_system_llm_config_store() -> SystemLLMConfigStore:
    """Get the singleton SystemLLMConfigStore instance."""
    global _store
    if _store is None:
        _store = SystemLLMConfigStore()
    return _store


def reset_system_llm_config_store() -> None:
    """Reset the singleton store (for testing)."""
    global _store
    _store = None
