"""Security primitives: password hashing, JWT, and AES (Fernet) encryption.

Secrets such as API keys and access tokens are encrypted at rest using Fernet
(AES-128-CBC + HMAC). Passwords use bcrypt.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import AuthenticationException

# --- Password hashing ---------------------------------------------------------


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT ----------------------------------------------------------------------


def _create_token(subject: str, expires_delta: timedelta, token_type: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    return _create_token(
        subject, timedelta(minutes=settings.access_token_expire_minutes), "access", extra
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, timedelta(days=settings.refresh_token_expire_days), "refresh")


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationException("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationException("Invalid token") from exc
    if expected_type and payload.get("type") != expected_type:
        raise AuthenticationException("Invalid token type")
    return payload


# --- Encryption (Fernet / AES) ------------------------------------------------


def _derive_fernet_key() -> bytes:
    """Use the configured key if valid, else derive a stable key from jwt_secret.

    Deriving from ``jwt_secret`` keeps development working without extra config
    while still allowing an explicit ``ENCRYPTION_KEY`` in production.
    """
    key = settings.encryption_key.strip()
    if key:
        try:
            Fernet(key.encode())
            return key.encode()
        except (ValueError, TypeError):
            pass
    digest = hashlib.sha256(settings.jwt_secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_fernet_key())


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mask_secret(value: str, visible: int = 4) -> str:
    """Mask a secret for safe display/logging."""
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return value[:visible] + "*" * (len(value) - visible)
