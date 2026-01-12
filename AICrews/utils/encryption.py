"""
Encryption utilities for API keys and sensitive data.

Uses Fernet symmetric encryption (AES-128-CBC with PKCS7 padding).
"""

import os
from cryptography.fernet import Fernet
from typing import Optional

# Environment variable for encryption key (should be set in production)
_ENCRYPTION_KEY_ENV = "ENCRYPTION_KEY"

# Default key for development (MUST be replaced in production)
# This is a FIXED Fernet key for development - ensures consistency across restarts
# WARNING: Do NOT use this in production - set ENCRYPTION_KEY environment variable
_DEFAULT_DEV_KEY = b"mgFWkMvRQshmlvvqGbZAkp0YKGxsuq6iR_1coffEinA="


def get_encryption_key_bytes(encryption_key: Optional[bytes | str] = None) -> bytes:
    """
    Resolve the effective Fernet key bytes.

    Priority:
    1) explicit `encryption_key`
    2) env var ENCRYPTION_KEY
    3) fixed dev fallback key (NOT for production)
    """
    key: bytes | str | None
    if encryption_key is not None:
        key = encryption_key
    else:
        key = os.environ.get(_ENCRYPTION_KEY_ENV)

    if not key:
        env = (os.getenv("ENVIRONMENT", "development") or "development").strip().lower()
        require_key = os.getenv("FAIC_REQUIRE_ENCRYPTION_KEY", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        if require_key or env in {"production", "prod"}:
            raise RuntimeError(
                "ENCRYPTION_KEY is required in production. "
                'Generate one with: python -c "from AICrews.utils.encryption import generate_encryption_key; '
                'print(generate_encryption_key())"'
            )
        return _DEFAULT_DEV_KEY

    if isinstance(key, str):
        return key.encode("utf-8")
    if isinstance(key, (bytes, bytearray)):
        return bytes(key)

    raise TypeError(f"Invalid encryption key type: {type(key)}")


def _get_fernet(encryption_key: Optional[bytes] = None) -> Fernet:
    """
    Get or create the Fernet encryption instance.

    Args:
        encryption_key: Optional explicit key (useful for tests or per-request encryption contexts).

    Uses explicit key when provided; otherwise uses ENCRYPTION_KEY env var if set,
    else falls back to a development key (NOT for production).
    """
    return Fernet(get_encryption_key_bytes(encryption_key))


def encrypt_api_key(api_key: str, encryption_key: Optional[bytes] = None) -> str:
    """
    Encrypt an API key using Fernet symmetric encryption.

    Args:
        api_key: The plaintext API key to encrypt
        encryption_key: Optional explicit encryption key (for tests / deterministic encryption).

    Returns:
        Encrypted API key as a base64-encoded string (Fernet token)

    Raises:
        ValueError: If api_key is empty or not a string
    """
    if not api_key:
        raise ValueError("API key cannot be empty")

    if not isinstance(api_key, str):
        raise ValueError("API key must be a string")

    f = _get_fernet(encryption_key)
    encrypted_bytes = f.encrypt(api_key.encode("utf-8"))

    return encrypted_bytes.decode("utf-8")


def decrypt_api_key(encrypted_api_key: str, encryption_key: Optional[bytes] = None) -> str:
    """
    Decrypt an API key that was encrypted with encrypt_api_key.

    Args:
        encrypted_api_key: The encrypted API key (Fernet token)
        encryption_key: Optional explicit encryption key (for tests / deterministic encryption).

    Returns:
        Decrypted (plaintext) API key

    Raises:
        ValueError: If encrypted_api_key is empty or invalid
        cryptography.exceptions.InvalidToken: If the key cannot be decrypted
    """
    if not encrypted_api_key:
        raise ValueError("Encrypted API key cannot be empty")

    f = _get_fernet(encryption_key)
    decrypted_bytes = f.decrypt(encrypted_api_key.encode("utf-8"))

    return decrypted_bytes.decode("utf-8")


def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be encrypted (Fernet format).

    Fernet tokens start with 'gAAA' in base64 encoding.

    Args:
        value: The value to check

    Returns:
        True if the value appears to be encrypted, False otherwise
    """
    if not isinstance(value, str):
        return False

    return value.startswith("gAAA")


def generate_encryption_key() -> str:
    """
    Generate a new random encryption key.

    Useful for setting up ENCRYPTION_KEY environment variable.

    Returns:
        A new Fernet key as a base64-encoded string
    """
    return Fernet.generate_key().decode("utf-8")
