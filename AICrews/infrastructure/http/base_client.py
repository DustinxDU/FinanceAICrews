"""
Base HTTP client with retry, timeout, and error handling.

Provides a standardized way to make HTTP requests across the application.
"""
from typing import Any, Dict, Optional
import asyncio
from abc import ABC, abstractmethod

import httpx

from AICrews.observability.logging import get_logger

logger = get_logger(__name__)


class BaseHTTPClient(ABC):
    """
    Abstract base class for HTTP clients.

    Provides:
    - Configurable timeout and retry logic
    - Consistent error handling and logging
    - Both sync and async support

    Subclasses should implement `_get_base_url()` and optionally
    override `_get_default_headers()`.

    Example:
        class MyAPIClient(BaseHTTPClient):
            def _get_base_url(self) -> str:
                return "https://api.example.com"

            def _get_default_headers(self) -> Dict[str, str]:
                return {"Authorization": f"Bearer {self.api_key}"}
    """

    DEFAULT_TIMEOUT = 30.0
    DEFAULT_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ):
        """
        Initialize the HTTP client.

        Args:
            timeout: Request timeout in seconds.
            retries: Number of retry attempts for failed requests.
            retry_delay: Delay between retries in seconds.
        """
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    @abstractmethod
    def _get_base_url(self) -> str:
        """Return the base URL for this client."""
        pass

    def _get_default_headers(self) -> Dict[str, str]:
        """Return default headers for requests. Override in subclasses."""
        return {"Content-Type": "application/json"}

    def _get_client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self._get_base_url(),
                timeout=self.timeout,
                headers=self._get_default_headers(),
            )
        return self._client

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self._get_base_url(),
                timeout=self.timeout,
                headers=self._get_default_headers(),
            )
        return self._async_client

    def request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Make a synchronous HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (appended to base URL)
            **kwargs: Additional arguments passed to httpx

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPError: If all retries fail
        """
        client = self._get_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.retries):
            try:
                response = client.request(method, path, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    f"HTTP request failed (attempt {attempt + 1}/{self.retries}): "
                    f"{method} {path} - {e}"
                )
                if attempt < self.retries - 1:
                    import time
                    time.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"All {self.retries} attempts failed for {method} {path}")
        raise last_error

    async def arequest(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Make an asynchronous HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (appended to base URL)
            **kwargs: Additional arguments passed to httpx

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPError: If all retries fail
        """
        client = self._get_async_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.retries):
            try:
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    f"Async HTTP request failed (attempt {attempt + 1}/{self.retries}): "
                    f"{method} {path} - {e}"
                )
                if attempt < self.retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"All {self.retries} async attempts failed for {method} {path}")
        raise last_error

    def get(self, path: str, **kwargs) -> httpx.Response:
        """Convenience method for GET requests."""
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        """Convenience method for POST requests."""
        return self.request("POST", path, **kwargs)

    async def aget(self, path: str, **kwargs) -> httpx.Response:
        """Convenience method for async GET requests."""
        return await self.arequest("GET", path, **kwargs)

    async def apost(self, path: str, **kwargs) -> httpx.Response:
        """Convenience method for async POST requests."""
        return await self.arequest("POST", path, **kwargs)

    def close(self) -> None:
        """Close sync client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    async def aclose(self) -> None:
        """Close async client."""
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()


__all__ = ["BaseHTTPClient"]
