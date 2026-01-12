"""
LiteLLM Proxy Provider - Thin Adapter for ResolvedLLMCall

This module provides a thin adapter that translates ResolvedLLMCall contracts
into LiteLLM Proxy-compatible LLM instances. It handles:
- Correct header mapping (x-litellm-enable-message-redaction, x-litellm-timeout)
- Tags mapping (top-level comma-separated + metadata.tags list)
- BYOK extra_body.user_config deep merge
- Trace field derivation (trace_id, trace_user_id, generation_name)

Key Design Principles:
- Thin adapter: No routing logic, no DB access, no policy decisions
- Security: Never log API keys in plaintext
- LiteLLM Proxy semantics: Follow official docs for headers/body structure
"""

import os
from AICrews.observability.logging import get_logger
from typing import Dict, Any, List, Optional
from copy import deepcopy

from litellm import completion

from AICrews.schemas.llm_policy import ResolvedLLMCall

logger = get_logger(__name__)


class LiteLLMProxyLLM:
    """
    Custom LLM implementation for LiteLLM Proxy calls.

    This is a thin wrapper that translates ResolvedLLMCall into a LiteLLM Proxy
    compatible request. It does NOT inherit from crewai.LLM because we need
    full control over headers and request body structure.

    Security:
    - API keys are SecretStr in ResolvedLLMCall (never logged)
    - BYOK keys in user_config are only in request body (ephemeral)
    - Repr/str methods sanitize secrets
    """

    def __init__(self, resolved_call: ResolvedLLMCall, timeout: int = 30):
        """
        Initialize LiteLLM Proxy LLM.

        Args:
            resolved_call: The resolved call contract from LLMPolicyRouter
            timeout: Request timeout in seconds (default 30s)
        """
        self.resolved_call = resolved_call
        self.timeout = timeout

        # Extract core fields
        self.base_url = str(resolved_call.base_url)
        self.model = resolved_call.model
        self.api_key = resolved_call.api_key.get_secret_value()

        # Build headers
        self.headers = self._build_headers()

        # Build base request body (without messages)
        self.base_request_body = self._build_base_request_body()

    def _build_headers(self) -> Dict[str, str]:
        """
        Build HTTP headers for LiteLLM Proxy request.

        Returns:
            Dict with Authorization, redaction, and timeout headers
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Add extra headers from resolved_call (e.g., message redaction)
        if self.resolved_call.extra_headers:
            headers.update(self.resolved_call.extra_headers)

        # Add timeout header
        headers["x-litellm-timeout"] = str(self.timeout)

        return headers

    def _build_base_request_body(self) -> Dict[str, Any]:
        """
        Build base request body (without messages).

        Follows LiteLLM Proxy semantics:
        - Top-level `tags`: comma-separated string (for spend tracking/routing)
        - Top-level `metadata`: includes tags list + run_id + trace fields
        - Optional `user_config`: BYOK credentials (deep merged)

        Returns:
            Dict with tags, metadata, and optional user_config
        """
        body: Dict[str, Any] = {}

        # 1. Top-level tags (comma-separated string)
        #    LiteLLM uses this for spend tracking, tag routing, etc.
        if self.resolved_call.metadata and "tags" in self.resolved_call.metadata:
            tags_list = self.resolved_call.metadata["tags"]
            body["tags"] = ",".join(tags_list)

        # 2. Metadata (tags list + run_id + trace fields)
        #    LiteLLM also supports metadata for custom logging/tracing
        metadata = deepcopy(self.resolved_call.metadata)

        # Derive trace fields for better observability
        if metadata:
            run_id = metadata.get("run_id")
            tags_list = metadata.get("tags", [])

            # Extract user_id and scope from tags
            user_id = None
            scope = None
            for tag in tags_list:
                if tag.startswith("user:"):
                    user_id = tag.split(":", 1)[1]
                elif tag.startswith("scope:"):
                    scope = tag.split(":", 1)[1]

            # Add trace fields (LiteLLM observability)
            if run_id:
                metadata["trace_id"] = run_id
            if user_id:
                metadata["trace_user_id"] = user_id
            if scope:
                metadata["generation_name"] = scope

        body["metadata"] = metadata

        # 3. Deep merge extra_body (BYOK user_config, etc.)
        if self.resolved_call.extra_body:
            # Deep merge to preserve both metadata and user_config
            for key, value in self.resolved_call.extra_body.items():
                if key in body:
                    # Merge nested dicts
                    if isinstance(body[key], dict) and isinstance(value, dict):
                        body[key] = {**body[key], **value}
                    else:
                        body[key] = value
                else:
                    body[key] = value

        return body

    def get_request_body(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Get complete request body with messages.

        Args:
            messages: Chat messages (OpenAI format)

        Returns:
            Complete request body for LiteLLM Proxy
        """
        body = deepcopy(self.base_request_body)
        body["model"] = self.model
        body["messages"] = messages
        return body

    def call(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Make a synchronous LLM call via LiteLLM Proxy.

        Args:
            messages: Chat messages
            **kwargs: Additional parameters for litellm.completion()

        Returns:
            Response text content
        """
        request_body = self.get_request_body(messages)

        # Merge kwargs (allow override of temperature, max_tokens, etc.)
        request_body.update(kwargs)

        # Log call (sanitized)
        logger.info(
            f"Calling LiteLLM Proxy: model={self.model}, "
            f"run_id={self.resolved_call.metadata.get('run_id')}"
        )

        # Make the call using litellm SDK
        response = completion(
            **request_body,
            api_base=self.base_url,
            api_key=self.api_key,
            custom_llm_provider="openai",  # LiteLLM Proxy is OpenAI-compatible
            timeout=self.timeout,
        )

        return response.choices[0].message.content

    async def acall(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Make an asynchronous LLM call via LiteLLM Proxy.

        Args:
            messages: Chat messages
            **kwargs: Additional parameters

        Returns:
            Response text content
        """
        from litellm import acompletion

        request_body = self.get_request_body(messages)
        request_body.update(kwargs)

        logger.info(
            f"Async calling LiteLLM Proxy: model={self.model}, "
            f"run_id={self.resolved_call.metadata.get('run_id')}"
        )

        response = await acompletion(
            **request_body,
            api_base=self.base_url,
            api_key=self.api_key,
            custom_llm_provider="openai",
            timeout=self.timeout,
        )

        return response.choices[0].message.content

    def __repr__(self) -> str:
        """Repr with sanitized API key."""
        return (
            f"LiteLLMProxyLLM(model={self.model}, "
            f"base_url={self.base_url}, "
            f"api_key=**********)"
        )

    def __str__(self) -> str:
        """String representation with sanitized secrets."""
        return self.__repr__()


class ProxyProvider:
    """
    Factory for creating LiteLLMProxyLLM instances from ResolvedLLMCall contracts.

    This is the ONLY entry point for business code to get LLM instances.
    It translates the stable ResolvedLLMCall contract into LiteLLM Proxy requests.

    Design:
    - Thin adapter: No routing, no DB, no policy logic
    - Security: Never logs API keys
    - Configuration: Reads timeout from env or uses default
    """

    def __init__(self, timeout: Optional[int] = None):
        """
        Initialize ProxyProvider.

        Args:
            timeout: Request timeout in seconds. If not provided, reads from
                    LITELLM_PROXY_TIMEOUT_S env var or defaults to 30s.
        """
        if timeout is not None:
            self.timeout = timeout
        else:
            # Read from env or use default
            self.timeout = int(os.getenv("LITELLM_PROXY_TIMEOUT_S", "30"))

    def create_llm(self, resolved_call: ResolvedLLMCall) -> LiteLLMProxyLLM:
        """
        Create an LLM instance from a ResolvedLLMCall contract.

        Args:
            resolved_call: The routing decision from LLMPolicyRouter

        Returns:
            LiteLLMProxyLLM instance ready to make LLM calls

        Example:
            ```python
            # Get routing decision
            resolved = router.resolve(scope="copilot", user_context=ctx, db=db)

            # Create LLM instance
            provider = ProxyProvider()
            llm = provider.create_llm(resolved)

            # Make LLM call
            response = llm.call([{"role": "user", "content": "Hello"}])
            ```
        """
        return LiteLLMProxyLLM(resolved_call=resolved_call, timeout=self.timeout)
