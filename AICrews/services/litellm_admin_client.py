"""
LiteLLM Admin Client - HTTP Wrapper for Admin API

This module provides a thin HTTP client wrapper for LiteLLM Proxy Admin API.
It handles:
- Key generation (POST /key/generate) with idempotency via key_alias
- Key info retrieval (GET /key/info)
- Key deletion (POST /key/delete)
- Key update (POST /key/update)

Key Design Principles:
- Pure HTTP transport: No business logic, no DB access
- Idempotency: key_alias based (LiteLLM native support)
- Error handling: Wraps HTTP errors in LiteLLMAdminError
- Security: Master key only in memory, never logged

LiteLLM Admin API Reference:
- https://docs.litellm.ai/docs/proxy/virtual_keys
- https://docs.litellm.ai/docs/proxy/management_cli
"""

import os
from AICrews.observability.logging import get_logger
from typing import Dict, Any, List, Optional

import httpx

logger = get_logger(__name__)


class LiteLLMAdminError(Exception):
    """Raised when LiteLLM Admin API calls fail."""

    pass


class LiteLLMAdminClient:
    """
    HTTP client for LiteLLM Proxy Admin API.

    This client wraps the LiteLLM Admin API endpoints for managing virtual keys.
    It requires a master key for authentication.

    Security Note:
    - Master key should ONLY be available to Provisioner (not app containers)
    - Master key is passed via Authorization header, never logged
    - Virtual keys returned are encrypted before storage

    Example:
        ```python
        client = LiteLLMAdminClient(
            admin_base_url="http://litellm:4000",
            master_key=os.getenv("LITELLM_PROXY_MASTER_KEY")
        )

        # Generate virtual key
        result = await client.generate_key(
            key_alias="vk:user:123",
            models=["agents_fast", "agents_balanced"],
            metadata={"user_id": "123", "key_type": "vk_user"}
        )

        virtual_key = result["key"]  # sk-vk-...
        ```
    """

    def __init__(
        self,
        admin_base_url: Optional[str] = None,
        master_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize LiteLLM Admin Client.

        Args:
            admin_base_url: LiteLLM proxy admin base URL (e.g., http://litellm:4000).
                           If not provided, reads from LITELLM_PROXY_ADMIN_BASE_URL env.
            master_key: LiteLLM proxy master key (sk-...).
                       If not provided, reads from LITELLM_PROXY_MASTER_KEY env.
            timeout: Request timeout in seconds (default 30s)

        Raises:
            ValueError: If master_key is not provided
        """
        self.admin_base_url = admin_base_url or os.getenv(
            "LITELLM_PROXY_ADMIN_BASE_URL", "http://litellm:4000"
        )
        self.master_key = master_key or os.getenv("LITELLM_PROXY_MASTER_KEY")
        self.timeout = timeout

        if not self.master_key:
            raise ValueError(
                "LITELLM_PROXY_MASTER_KEY is required for admin operations. "
                "Set it via environment variable or pass explicitly."
            )

        # Create httpx client with auth headers
        self.client = httpx.AsyncClient(
            base_url=self.admin_base_url,
            headers={
                "Authorization": f"Bearer {self.master_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )

        logger.info(
            f"Initialized LiteLLM Admin Client: base_url={self.admin_base_url}"
        )

    async def generate_key(
        self,
        key_alias: str,
        models: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        max_budget: Optional[float] = None,
        duration: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a new virtual key (or return existing if alias exists).

        This is idempotent: if key_alias already exists, LiteLLM returns the
        existing key instead of creating a duplicate.

        Args:
            key_alias: Unique identifier for the key (e.g., "vk:user:123").
                      Used for idempotency.
            models: List of model aliases this key can access
                   (e.g., ["agents_fast", "agents_balanced"])
            metadata: Optional metadata to attach to the key
                     (e.g., {"user_id": "123", "key_type": "vk_user"})
            user_id: Optional user ID for tracking (string format)
            max_budget: Optional maximum spend limit for this key
            duration: Optional key expiration duration (e.g., "30d")

        Returns:
            Dict with key info:
            {
                "key": "sk-vk-abc123...",
                "key_alias": "vk:user:123",
                "user_id": "123",
                "models": ["agents_fast", "agents_balanced"],
                "metadata": {...}
            }

        Raises:
            LiteLLMAdminError: If key generation fails
        """
        payload: Dict[str, Any] = {
            "key_alias": key_alias,
            "models": models,
        }

        if metadata:
            payload["metadata"] = metadata
        if user_id:
            payload["user_id"] = user_id
        if max_budget:
            payload["max_budget"] = max_budget
        if duration:
            payload["duration"] = duration

        try:
            response = await self.client.post("/key/generate", json=payload)
            response.raise_for_status()

            result = response.json()

            logger.info(
                f"Generated virtual key: alias={key_alias}, "
                f"models={models}, user_id={user_id}"
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to generate key: alias={key_alias}, "
                f"status={e.response.status_code}, error={e.response.text}"
            )
            raise LiteLLMAdminError(
                f"Failed to generate key '{key_alias}': {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Network error generating key: {e}")
            raise LiteLLMAdminError(f"Network error: {e}") from e

    async def get_key_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a virtual key.

        Args:
            key: The virtual key to query (e.g., "sk-vk-abc123...")

        Returns:
            Dict with key info if found, None if key doesn't exist:
            {
                "key": "sk-vk-abc123...",
                "key_alias": "vk:user:123",
                "user_id": "123",
                "models": ["agents_fast"],
                "spend": 0.0,
                "max_budget": None,
                "metadata": {...}
            }

        Raises:
            LiteLLMAdminError: If query fails (except 404)
        """
        try:
            response = await self.client.get("/key/info", params={"key": key})
            response.raise_for_status()

            result = response.json()

            logger.debug(f"Retrieved key info: alias={result.get('key_alias')}")

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Key doesn't exist - return None (not an error)
                logger.debug(f"Key not found: {key}")
                return None

            logger.error(
                f"Failed to get key info: key={key}, "
                f"status={e.response.status_code}, error={e.response.text}"
            )
            raise LiteLLMAdminError(
                f"Failed to get key info: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Network error getting key info: {e}")
            raise LiteLLMAdminError(f"Network error: {e}") from e

    async def delete_key(self, key: str) -> bool:
        """
        Delete a virtual key.

        This is idempotent: deleting a non-existent key returns False
        (not an error).

        Args:
            key: The virtual key to delete (e.g., "sk-vk-abc123...")

        Returns:
            True if key was deleted, False if key didn't exist

        Raises:
            LiteLLMAdminError: If deletion fails (except 404)
        """
        payload = {"key": key}

        try:
            response = await self.client.post("/key/delete", json=payload)
            response.raise_for_status()

            logger.info(f"Deleted virtual key: {key}")

            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Key already deleted - idempotent
                logger.debug(f"Key already deleted: {key}")
                return False

            logger.error(
                f"Failed to delete key: key={key}, "
                f"status={e.response.status_code}, error={e.response.text}"
            )
            raise LiteLLMAdminError(
                f"Failed to delete key: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Network error deleting key: {e}")
            raise LiteLLMAdminError(f"Network error: {e}") from e

    async def update_key(
        self,
        key: str,
        models: Optional[List[str]] = None,
        max_budget: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing virtual key.

        Args:
            key: The virtual key to update (e.g., "sk-vk-abc123...")
            models: Optional new list of allowed models
            max_budget: Optional new budget limit
            metadata: Optional new metadata

        Returns:
            Dict with updated key info

        Raises:
            LiteLLMAdminError: If update fails
        """
        payload: Dict[str, Any] = {"key": key}

        if models is not None:
            payload["models"] = models
        if max_budget is not None:
            payload["max_budget"] = max_budget
        if metadata is not None:
            payload["metadata"] = metadata

        try:
            response = await self.client.post("/key/update", json=payload)
            response.raise_for_status()

            result = response.json()

            logger.info(f"Updated virtual key: {key}")

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to update key: key={key}, "
                f"status={e.response.status_code}, error={e.response.text}"
            )
            raise LiteLLMAdminError(
                f"Failed to update key: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Network error updating key: {e}")
            raise LiteLLMAdminError(f"Network error: {e}") from e

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
