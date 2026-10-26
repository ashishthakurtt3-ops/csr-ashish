"""
modules/admin_panel/utils/ai_crypto.py
======================================
Cryptographic utility for secure storage and handling of AI provider API keys.
Follows defense-in-depth principles:
- Symmetric encryption at rest using AES-128-CBC + HMAC-SHA256 (Fernet).
- Encryption key derived separately from Django SECRET_KEY or dedicated AI_ENCRYPTION_KEY.
- Keys are NEVER stored in plaintext in the database.
- Keys are NEVER exposed in plain text in logs, frontend responses, or DOM attributes.
- Provides consistent masking utilities for secure display across administrative consoles.
"""

import os
import base64
import hashlib
from typing import Optional
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


def get_encryption_key() -> bytes:
    """
    Retrieves or derives a consistent 32-byte URL-safe base64 encryption key.
    Prefers explicit AI_ENCRYPTION_KEY from environment, falling back to a
    PBKDF2-style SHA-256 derivation over settings.SECRET_KEY with a cryptographic domain salt.
    """
    env_key = os.environ.get("AI_ENCRYPTION_KEY", "").strip()
    if env_key:
        try:
            # Validate Fernet key format
            key_bytes = env_key.encode("utf-8")
            Fernet(key_bytes)
            return key_bytes
        except Exception:
            pass

    if settings.configured:
        secret = getattr(settings, "SECRET_KEY", "") or os.environ.get("SECRET_KEY", "default-insecure-django-secret-fallback")
    else:
        secret = os.environ.get("SECRET_KEY", "default-insecure-django-secret-fallback")
    salt = b":CSR_AI_INTELLIGENCE_2026_CRYPTO_SALT_AT_REST"
    digest = hashlib.sha256(secret.encode("utf-8") + salt).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(plaintext: str) -> str:
    """
    Encrypts a plaintext string (e.g. API key) into a URL-safe encrypted token.
    Returns empty string if plaintext is empty or None.
    """
    if not plaintext or not str(plaintext).strip():
        return ""
    
    key = get_encryption_key()
    fernet = Fernet(key)
    encrypted_bytes = fernet.encrypt(str(plaintext).strip().encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """
    Decrypts an encrypted token back into its plaintext string.
    Returns empty string if ciphertext is empty, None, or invalid.
    """
    if not ciphertext or not str(ciphertext).strip():
        return ""

    key = get_encryption_key()
    fernet = Fernet(key)
    try:
        decrypted_bytes = fernet.decrypt(str(ciphertext).strip().encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except (InvalidToken, Exception):
        # Graceful handling if ciphertext was corrupted or key changed
        return ""


def mask_api_key(raw_key: Optional[str], default: str = "") -> str:
    """
    Produces a safe, masked representation of an API key for administrative display.
    Examples:
    - 53-character key: '••••••••••••tjCw (53 chars)'
    - Short key (<=8 chars): '•••••••• (5 chars)'
    - Empty: default
    NEVER leaks full secret value.
    """
    if not raw_key:
        return default

    clean = str(raw_key).strip()
    length = len(clean)
    if length == 0:
        return default
    if length <= 8:
        return f"•••••••• ({length} chars)"

    last_four = clean[-4:]
    return f"••••••••••••{last_four} ({length} chars)"


def is_masked_placeholder(key: Optional[str]) -> bool:
    """
    Returns True if a string looks like a masked API key or placeholder badge,
    preventing it from overwriting the real encrypted key.
    """
    if not key or not str(key).strip():
        return True
    k = str(key).strip()
    return (
        "•" in k
        or "\u2022" in k
        or "\ufffd" in k
        or k.startswith("****")
        or ("chars)" in k and "(" in k)
        or k.startswith("(Not configured)")
    )
