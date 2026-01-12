"""
LLM Provider Compatibility Service

Checks if LLM providers support critical features like function calling,
to prevent runtime failures and agent hallucination issues.
"""

from AICrews.observability.logging import get_logger
from typing import Dict, Set, Tuple
from enum import Enum

logger = get_logger(__name__)


class FunctionCallingSupport(str, Enum):
    """Function calling support levels."""
    FULL = "full"           # Fully tested and supported
    PARTIAL = "partial"     # Supported but may have limitations
    UNCERTAIN = "uncertain" # Unknown/untested
    NONE = "none"          # Does not support function calling


class ProviderCompatibilityService:
    """Service for checking LLM provider compatibility with required features."""

    # Providers with confirmed full function calling support
    FULL_SUPPORT_PROVIDERS: Set[str] = {
        'openai',
        'anthropic',
        'google',
        'azure',
        'groq',
        'deepseek',
        'together',
        'volcengine',      # Doubao - confirmed to support function calling
        'zhipu_ai',        # Zhipu AI/GLM-4.5+ - 90.6% tool-calling success rate (2025)
    }

    # Providers with partial/uncertain support
    UNCERTAIN_PROVIDERS: Set[str] = {
        'qianwen',         # Qianwen/Tongyi - needs verification
        'kimi_moonshot',   # Kimi - may require special config
    }

    # Providers known to NOT support function calling
    NO_SUPPORT_PROVIDERS: Set[str] = {
        'local',           # Local models generally don't support tools
        'ollama',          # Ollama models vary widely
    }

    def check_function_calling_support(
        self,
        provider_key: str,
        model_key: str = None
    ) -> Tuple[FunctionCallingSupport, str]:
        """
        Check if a provider/model supports function calling.

        Args:
            provider_key: Provider identifier (e.g., 'openai', 'volcengine')
            model_key: Optional model identifier for model-specific checks

        Returns:
            Tuple of (support_level, warning_message)
        """
        provider_lower = provider_key.lower()

        if provider_lower in self.FULL_SUPPORT_PROVIDERS:
            return (
                FunctionCallingSupport.FULL,
                f"Provider '{provider_key}' has full function calling support."
            )

        if provider_lower in self.UNCERTAIN_PROVIDERS:
            warning = (
                f"🚨 CRITICAL: Provider '{provider_key}' has UNCERTAIN function calling support. "
                f"Tools may NOT work correctly - the LLM might ignore tool schemas entirely. "
                f"If your agent outputs data without calling tools, it is HALLUCINATING from training data. "
                f"STRONGLY RECOMMENDED: Switch to OpenAI, Anthropic, or Google for reliable tool usage."
            )
            # Log at ERROR level to ensure visibility
            logger.error(f"⚠️ {warning}")
            return (FunctionCallingSupport.UNCERTAIN, warning)

        if provider_lower in self.NO_SUPPORT_PROVIDERS:
            error = (
                f"Provider '{provider_key}' does NOT support function calling. "
                f"Tools will NOT work. You MUST switch to a supported provider "
                f"(OpenAI, Anthropic, Google, Groq, or DeepSeek)."
            )
            logger.error(error)
            return (FunctionCallingSupport.NONE, error)

        # Unknown provider - assume uncertain
        warning = (
            f"Provider '{provider_key}' is not in our compatibility list. "
            f"Function calling support is UNKNOWN. Proceed with caution. "
            f"If tools don't work, switch to OpenAI, Anthropic, or Google."
        )
        logger.warning(warning)
        return (FunctionCallingSupport.UNCERTAIN, warning)

    def validate_agent_llm_compatibility(
        self,
        agent_name: str,
        provider_key: str,
        model_key: str,
        has_tools: bool,
        strict_mode: bool = False
    ) -> Dict[str, any]:
        """
        Validate that an agent's LLM is compatible with its tool requirements.

        Args:
            agent_name: Agent name for error messages
            provider_key: LLM provider
            model_key: LLM model
            has_tools: Whether agent has tools configured
            strict_mode: If True, raise error for uncertain/no support

        Returns:
            Dict with 'can_proceed' (bool), 'warnings' (list), 'errors' (list)
        """
        result = {
            'can_proceed': True,
            'warnings': [],
            'errors': []
        }

        # If agent has no tools, no compatibility check needed
        if not has_tools:
            return result

        # Check function calling support
        support_level, message = self.check_function_calling_support(provider_key, model_key)

        if support_level == FunctionCallingSupport.FULL:
            # All good
            pass

        elif support_level == FunctionCallingSupport.UNCERTAIN:
            result['warnings'].append(
                f"Agent '{agent_name}' uses provider '{provider_key}' with uncertain tool support. {message}"
            )
            if strict_mode:
                result['can_proceed'] = False
                result['errors'].append(
                    f"Strict mode: Agent '{agent_name}' cannot use provider '{provider_key}' with tools. "
                    f"Switch to OpenAI/Anthropic/Google."
                )

        elif support_level == FunctionCallingSupport.NONE:
            result['can_proceed'] = False
            result['errors'].append(
                f"Agent '{agent_name}' has tools but provider '{provider_key}' does NOT support function calling. "
                f"Tools will not work. You MUST switch to a supported provider."
            )

        return result

    def get_recommended_providers(self) -> Dict[str, str]:
        """Get list of recommended providers with descriptions."""
        return {
            'openai': 'OpenAI (GPT-4, GPT-3.5) - Full support, most tested',
            'anthropic': 'Anthropic (Claude 3+) - Full support, reliable',
            'google': 'Google (Gemini 1.5+) - Full support',
            'groq': 'Groq (Fast inference) - Full support',
            'deepseek': 'DeepSeek (OpenAI-compatible) - Full support',
        }


# Singleton instance
_compatibility_service = None


def get_compatibility_service() -> ProviderCompatibilityService:
    """Get singleton ProviderCompatibilityService instance."""
    global _compatibility_service
    if _compatibility_service is None:
        _compatibility_service = ProviderCompatibilityService()
    return _compatibility_service
