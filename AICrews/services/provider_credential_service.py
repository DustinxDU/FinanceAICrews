"""
Provider Credential Service - User-based API key management.

Stores and retrieves API keys for providers (builtin and MCP) in the
user_credentials table with Fernet encryption.

Design Principles:
1. API keys are user-private data - stored in user_credentials, not provider config
2. Keys are encrypted at rest using Fernet symmetric encryption
3. Healthcheck validates API key before marking provider as healthy
4. Providers with required env vars take precedence over user credentials
5. Credential requirements defined in connection_schema.credentials[]
6. Multi-credential support: one provider can have multiple credential types
"""

import os
from AICrews.observability.logging import get_logger
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from AICrews.database.models.user import UserCredential
from AICrews.database.models.provider import CapabilityProvider
from AICrews.utils.encryption import encrypt_api_key, decrypt_api_key


def func_now():
    """Get current timestamp for database inserts."""
    return datetime.now()

logger = get_logger(__name__)


# Provider validation configuration
# Maps provider_key to validation endpoint and method
# Only providers that require API keys need validation config
PROVIDER_VALIDATION_CONFIG: Dict[str, Dict] = {
    "builtin:serper_dev_tool": {
        "validation_endpoint": "https://google.serper.dev/search",
        "validation_method": "POST",
        "display_name": "Serper API Key",
        "get_key_url": "https://serper.dev/api-key",
    },
    "builtin:firecrawl_tool": {
        "validation_endpoint": "https://api.firecrawl.dev/v1/scrape",
        "validation_method": "POST",
        "display_name": "Firecrawl API Key",
        "get_key_url": "https://firecrawl.dev/app/api-keys",
    },
}


class ProviderCredentialService:
    """
    Service for managing user API keys for providers (builtin and MCP).

    Features:
    - Save/retrieve encrypted API keys for users
    - Multi-credential support: one provider can have multiple credential types
    - Validate API keys against provider endpoints
    - Check if provider requires user credentials based on connection_schema
    """

    def __init__(self, db: Session):
        self.db = db

    def get_provider(self, provider_key: str) -> Optional[CapabilityProvider]:
        """Get provider by key."""
        result = self.db.execute(
            select(CapabilityProvider).where(
                CapabilityProvider.provider_key == provider_key
            )
        )
        return result.scalar_one_or_none()

    def get_provider_by_id(self, provider_id: int) -> Optional[CapabilityProvider]:
        """Get provider by ID."""
        result = self.db.execute(
            select(CapabilityProvider).where(
                CapabilityProvider.id == provider_id
            )
        )
        return result.scalar_one_or_none()

    def get_credential_requirements(self, provider: CapabilityProvider) -> List[Dict]:
        """
        Get credential requirements from provider's connection_schema.

        Returns list of credential definitions:
        [
            {
                "key": "polygon_api_key",
                "display_name": "Polygon.io API Key",
                "description": "...",
                "required": False,
                "env_var": "OPENBB_POLYGON_API_KEY",
                "get_key_url": "https://..."
            },
            ...
        ]
        """
        schema = provider.connection_schema or {}
        return schema.get("credentials", [])

    def get_required_env_vars(self, provider: CapabilityProvider) -> List[str]:
        """
        Get required environment variables from provider's connection_schema.

        Returns empty list if provider doesn't require any env vars.
        """
        schema = provider.connection_schema or {}
        return schema.get("requires_env", [])

    def get_validation_config(self, provider_key: str) -> Optional[Dict]:
        """Get validation configuration for a provider."""
        return PROVIDER_VALIDATION_CONFIG.get(provider_key)

    def get_user_credential(
        self, user_id: int, provider_key: str, credential_type: str = "api_key"
    ) -> Optional[UserCredential]:
        """Get user's stored credential for a provider and credential type."""
        result = self.db.execute(
            select(UserCredential).where(
                UserCredential.user_id == user_id,
                UserCredential.provider_id == provider_key,
                UserCredential.credential_type == credential_type,
            )
        )
        return result.scalar_one_or_none()

    def get_all_user_credentials(
        self, user_id: int, provider_key: str
    ) -> Dict[str, UserCredential]:
        """
        Get all credentials for a user/provider, keyed by credential_type.

        Returns:
            Dict mapping credential_type to UserCredential object
        """
        result = self.db.execute(
            select(UserCredential).where(
                UserCredential.user_id == user_id,
                UserCredential.provider_id == provider_key,
            )
        )
        credentials = result.scalars().all()
        return {cred.credential_type: cred for cred in credentials}

    def get_all_credential_statuses(
        self, user_id: int, provider: CapabilityProvider
    ) -> List[Dict[str, Any]]:
        """
        Get status of all credentials for a provider.

        Returns list of credential statuses based on connection_schema.credentials:
        [
            {
                "key": "polygon_api_key",
                "display_name": "Polygon.io API Key",
                "description": "...",
                "required": False,
                "get_key_url": "https://...",
                "has_credential": True,
                "is_verified": True,
                "uses_env_var": False
            },
            ...
        ]
        """
        requirements = self.get_credential_requirements(provider)
        if not requirements:
            return []

        # Get all user credentials for this provider
        user_credentials = self.get_all_user_credentials(user_id, provider.provider_key)

        statuses = []
        for req in requirements:
            key = req.get("key", "")
            env_var = req.get("env_var", "")

            # Check if env var is set
            uses_env_var = bool(env_var and os.getenv(env_var))

            # Get user credential
            credential = user_credentials.get(key)

            statuses.append({
                "key": key,
                "display_name": req.get("display_name", key),
                "description": req.get("description", ""),
                "required": req.get("required", False),
                "get_key_url": req.get("get_key_url", ""),
                "has_credential": credential is not None,
                "is_verified": credential.is_verified if credential else False,
                "uses_env_var": uses_env_var,
            })

        return statuses

    def get_user_api_key(self, user_id: int, provider_key: str) -> Optional[str]:
        """
        Get decrypted API key for user/provider.

        Returns None if:
        - Provider uses environment variable (takes precedence)
        - No credential stored
        - Credential exists but is_verified=False
        """
        provider = self.get_provider(provider_key)
        if not provider:
            return None

        # Check if env vars are set (takes precedence)
        required_env_vars = self.get_required_env_vars(provider)
        if required_env_vars and all(os.getenv(var) for var in required_env_vars):
            logger.debug(
                "Provider %s uses environment variables, skipping user credential",
                provider_key,
            )
            return None  # Signal to use env var

        # Get user credential
        credential = self.get_user_credential(user_id, provider_key)
        if not credential:
            return None

        if not credential.is_verified:
            logger.debug(
                "Credential for %s exists but not verified", provider_key
            )
            return None

        try:
            return decrypt_api_key(credential.encrypted_value)
        except Exception as e:
            logger.error("Failed to decrypt API key for %s: %s", provider_key, e)
            return None

    def save_api_key(
        self,
        user_id: int,
        provider_key: str,
        api_key: str,
        credential_type: str = "api_key",
    ) -> UserCredential:
        """
        Save encrypted API key for user/provider.

        Args:
            user_id: User ID
            provider_key: Provider key (e.g., "builtin:serper_dev_tool" or "mcp:openbb")
            api_key: Plaintext API key to encrypt and store
            credential_type: Type of credential (e.g., "api_key", "polygon_api_key")

        Returns:
            Created or updated UserCredential
        """
        # Encrypt the API key
        encrypted_value = encrypt_api_key(api_key)

        # Create display mask (first 4 chars + asterisks)
        display_mask = f"{api_key[:4]}****" if len(api_key) > 4 else "****"

        # Check for existing credential with same type
        existing = self.get_user_credential(user_id, provider_key, credential_type)

        if existing:
            # Update existing
            existing.encrypted_value = encrypted_value
            existing.display_mask = display_mask
            existing.is_verified = False  # Requires re-validation
            existing.updated_at = func_now()
            credential = existing
            logger.info("Updated API key for user %d, provider %s", user_id, provider_key)
        else:
            # Create new
            credential = UserCredential(
                user_id=user_id,
                provider_id=provider_key,
                credential_type=credential_type,
                encrypted_value=encrypted_value,
                display_mask=display_mask,
                is_verified=False,
            )
            self.db.add(credential)
            logger.info("Created API key for user %d, provider %s", user_id, provider_key)

        self.db.commit()
        self.db.refresh(credential)
        return credential

    def delete_credential(
        self, user_id: int, provider_key: str, credential_type: str = "api_key"
    ) -> bool:
        """Delete user's credential for a provider and credential type."""
        credential = self.get_user_credential(user_id, provider_key, credential_type)
        if credential:
            self.db.delete(credential)
            self.db.commit()
            logger.info(
                "Deleted credential %s for user %d, provider %s",
                credential_type, user_id, provider_key
            )
            return True
        return False

    def mark_verified(
        self, user_id: int, provider_key: str, credential_type: str = "api_key"
    ) -> bool:
        """Mark credential as verified after successful validation."""
        credential = self.get_user_credential(user_id, provider_key, credential_type)
        if credential:
            credential.is_verified = True
            credential.updated_at = func_now()
            self.db.commit()
            return True
        return False

    def validate_api_key(
        self, user_id: int, provider_key: str, api_key: str
    ) -> Dict[str, Any]:
        """
        Validate an API key by making a test request to the provider.

        Args:
            user_id: User ID (for logging)
            provider_key: Provider key
            api_key: API key to validate

        Returns:
            Dict with:
                - valid: bool
                - message: str (error if invalid)
                - latency_ms: int (request latency)
        """
        import time
        import httpx

        config = self.get_validation_config(provider_key)
        if not config:
            return {
                "valid": False,
                "message": "Provider does not support credential validation",
                "latency_ms": 0,
            }

        endpoint = config.get("validation_endpoint")
        if not endpoint:
            return {
                "valid": False,
                "message": "No validation endpoint configured",
                "latency_ms": 0,
            }

        start_time = time.time()
        try:
            if provider_key == "builtin:serper_dev_tool":
                # Test search request
                response = httpx.post(
                    endpoint,
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": "test query", "num": 1},
                    timeout=10,
                )
                if response.status_code == 200:
                    return {
                        "valid": True,
                        "message": "API key is valid",
                        "latency_ms": int((time.time() - start_time) * 1000),
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"API key rejected: status {response.status_code}",
                        "latency_ms": int((time.time() - start_time) * 1000),
                    }

            elif provider_key == "builtin:firecrawl_tool":
                # Test scrape request
                response = httpx.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"url": "https://example.com", "onlyMainContent": True},
                    timeout=10,
                )
                if response.status_code in (200, 201):
                    return {
                        "valid": True,
                        "message": "API key is valid",
                        "latency_ms": int((time.time() - start_time) * 1000),
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"API key rejected: status {response.status_code}",
                        "latency_ms": int((time.time() - start_time) * 1000),
                    }

            else:
                return {
                    "valid": False,
                    "message": f"Unknown provider: {provider_key}",
                    "latency_ms": 0,
                }

        except httpx.TimeoutException:
            return {
                "valid": False,
                "message": "Validation request timed out",
                "latency_ms": int((time.time() - start_time) * 1000),
            }
        except Exception as e:
            logger.error("API key validation error for %s: %s", provider_key, e)
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}",
                "latency_ms": int((time.time() - start_time) * 1000),
            }

    def requires_credential_for_provider(self, provider: CapabilityProvider) -> bool:
        """
        Check if a provider requires user credentials based on connection_schema.

        A provider requires credentials if:
        1. It has requires_env in connection_schema
        2. AND those env vars are NOT set in the environment

        Args:
            provider: CapabilityProvider object

        Returns:
            True if user needs to configure API key, False otherwise
        """
        required_env_vars = self.get_required_env_vars(provider)

        # No env vars required = no credentials needed
        if not required_env_vars:
            return False

        # Check if all required env vars are set
        if all(os.getenv(var) for var in required_env_vars):
            return False  # Env vars are set, no user credential needed

        return True  # User needs to configure API key

    def get_credential_status_for_provider(
        self, user_id: int, provider: CapabilityProvider
    ) -> Dict[str, Any]:
        """
        Get credential status for a user/provider.

        Args:
            user_id: User ID
            provider: CapabilityProvider object

        Returns:
            Dict with:
                - has_credential: bool
                - is_verified: bool
                - requires_credential: bool
                - uses_env_var: bool
        """
        required_env_vars = self.get_required_env_vars(provider)

        # Check if env vars are set
        uses_env_var = bool(required_env_vars and all(os.getenv(var) for var in required_env_vars))

        # Get user credential if not using env var
        credential = None
        if not uses_env_var and required_env_vars:
            credential = self.get_user_credential(user_id, provider.provider_key)

        return {
            "has_credential": credential is not None,
            "is_verified": credential.is_verified if credential else False,
            "requires_credential": self.requires_credential_for_provider(provider),
            "uses_env_var": uses_env_var,
        }


def get_provider_credential_service(db: Session) -> ProviderCredentialService:
    """Factory function to get ProviderCredentialService instance."""
    return ProviderCredentialService(db)
