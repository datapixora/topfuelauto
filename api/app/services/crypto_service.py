"""
Encryption service for sensitive data (proxy credentials, API keys, etc.)
Uses Fernet symmetric encryption from cryptography library.
"""
import os
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Get encryption key from environment variable.
    If not set, generates a warning and uses a default (NOT FOR PRODUCTION).
    """
    key_str = os.getenv("ENCRYPTION_KEY")
    if not key_str:
        logger.warning(
            "ENCRYPTION_KEY not set. Using default key (INSECURE - for development only). "
            "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
        # Default key for development (NOT SECURE)
        return b"ZO8yT5QX9QqJ8YqJ8QqJ8YqJ8QqJ8YqJ8QqJ8YqJ8Qo="

    return key_str.encode()


def encrypt_string(plaintext: Optional[str]) -> Optional[str]:
    """
    Encrypt a string using Fernet encryption.
    Returns base64-encoded encrypted string, or None if input is None/empty.
    """
    if not plaintext:
        return None

    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_bytes = f.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise ValueError("Failed to encrypt data")


def decrypt_string(encrypted: Optional[str]) -> Optional[str]:
    """
    Decrypt a Fernet-encrypted string.
    Returns plaintext string, or None if input is None/empty.
    Raises ValueError if decryption fails (wrong key, corrupted data, etc.).
    """
    if not encrypted:
        return None

    try:
        key = get_encryption_key()
        f = Fernet(key)
        decrypted_bytes = f.decrypt(encrypted.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        logger.error("Decryption failed: invalid token (wrong key or corrupted data)")
        raise ValueError("Failed to decrypt data (invalid key or corrupted data)")
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Failed to decrypt data")


def encrypt_dict(data: dict, fields: list[str]) -> dict:
    """
    Encrypt specified fields in a dictionary.
    Returns a new dict with encrypted fields.
    """
    result = data.copy()
    for field in fields:
        if field in result and result[field]:
            result[field] = encrypt_string(result[field])
    return result


def decrypt_dict(data: dict, fields: list[str]) -> dict:
    """
    Decrypt specified fields in a dictionary.
    Returns a new dict with decrypted fields.
    """
    result = data.copy()
    for field in fields:
        if field in result and result[field]:
            try:
                result[field] = decrypt_string(result[field])
            except ValueError:
                # If decryption fails, keep the original value
                logger.warning(f"Failed to decrypt field '{field}', keeping encrypted value")
    return result
