import hashlib
from AICrews.observability.logging import get_logger
import os
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse

from AICrews.database.models import UserModelConfig
from AICrews.llm.factories.llm_factory import get_llm_factory
from AICrews.llm.pool import LLMInstancePool
from AICrews.utils.encryption import decrypt_api_key, is_encrypted

logger = get_logger(__name__)

def _fingerprint_api_key(api_key: str) -> str:
    """Create a non-reversible fingerprint for observability."""
    sha = hashlib.sha1(api_key.encode("utf-8")).hexdigest()
    return f"{sha[:8]}...{sha[-4:]}"


@dataclass
class ResolvedLLMConfig:
    """Resolved, runtime-ready LLM configuration (no secrets logged)."""

    user_model_config_id: int
    provider_key: str
    provider_type: str
    model_key: str
    custom_model_name: Optional[str]
    endpoint_id: Optional[str]
    base_url: Optional[str]
    base_host: Optional[str]
    api_key_fingerprint: str


class LLMRuntime:
    """Runtime resolver + factory wrapper.

    Single place to transform DB UserModelConfig into:
    - Resolved, auditable config (base_host + key fingerprint)
    - CrewAI LLM instance
    """

    def __init__(self):
        self._factory = get_llm_factory()
        # Enable LLM pooling by default to avoid redundant instance creation
        self._pool_enabled = os.getenv("FAIC_LLM_POOL_ENABLED", "true").lower() == "true"
        maxsize = int(os.getenv("FAIC_LLM_POOL_MAXSIZE", "128"))
        self._pool = LLMInstancePool(create_fn=lambda _cfg: None, maxsize=maxsize)

    def resolve(self, user_model_config: UserModelConfig) -> ResolvedLLMConfig:
        provider = user_model_config.llm_config.provider
        model = user_model_config.model
        provider_key = provider.provider_key
        provider_type = provider.provider_type
        model_key = model.model_key

        raw_api_key = user_model_config.llm_config.api_key
        api_key = decrypt_api_key(raw_api_key) if is_encrypted(raw_api_key) else raw_api_key
        base_url = user_model_config.llm_config.base_url

        if not api_key:
            raise ValueError(
                f"User model config {user_model_config.id} missing api_key; cannot resolve runtime config."
            )
        if "*" in api_key:
            raise ValueError(
                f"User model config {user_model_config.id} contains masked api_key; please re-enter credential."
            )

        parsed = urlparse(base_url) if base_url else None
        base_host = (parsed.netloc or parsed.path) if parsed else None

        return ResolvedLLMConfig(
            user_model_config_id=user_model_config.id,
            provider_key=provider_key,
            provider_type=provider_type,
            model_key=model_key,
            custom_model_name=user_model_config.custom_model_name,
            endpoint_id=getattr(user_model_config, "volcengine_endpoint_id", None),
            base_url=base_url,
            base_host=base_host,
            api_key_fingerprint=_fingerprint_api_key(api_key),
        )

    def create_llm(
        self, user_model_config: UserModelConfig, **kwargs
    ) -> Tuple[object, ResolvedLLMConfig]:
        """Create CrewAI LLM + return resolved config for observability."""
        resolved = self.resolve(user_model_config)

        if self._pool_enabled:
            key_config = {
                "user_model_config_id": resolved.user_model_config_id,
                "provider_key": resolved.provider_key,
                "provider_type": resolved.provider_type,
                "model_key": resolved.model_key,
                "custom_model_name": resolved.custom_model_name,
                "endpoint_id": resolved.endpoint_id,
                "base_url": resolved.base_url,
                "kwargs": kwargs,
            }
            llm = self._pool.acquire_with_key(
                key_config,
                create=lambda: self._factory.create_from_user_model_config(
                    user_model_config, **kwargs
                ),
            )
        else:
            llm = self._factory.create_from_user_model_config(user_model_config, **kwargs)
        logger.info(
            "LLM created (runtime): provider=%s, model=%s, base_host=%s, user_model_config_id=%s, key_fp=%s",
            resolved.provider_key,
            resolved.model_key,
            resolved.base_host,
            resolved.user_model_config_id,
            resolved.api_key_fingerprint,
        )
        return llm, resolved


_llm_runtime: Optional[LLMRuntime] = None


def get_llm_runtime() -> LLMRuntime:
    global _llm_runtime
    if _llm_runtime is None:
        _llm_runtime = LLMRuntime()
    return _llm_runtime


def resolve_llm_config(user_model_config: UserModelConfig) -> ResolvedLLMConfig:
    return get_llm_runtime().resolve(user_model_config)


def create_llm_from_user_model_config(user_model_config: UserModelConfig, **kwargs):
    return get_llm_runtime().create_llm(user_model_config, **kwargs)
