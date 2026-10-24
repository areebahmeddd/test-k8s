import functools
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt only considers the first 72 bytes and bcrypt>=5 rejects longer input.
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@functools.cache
def _dummy_password_hash() -> str:
    return hash_password(secrets.token_urlsafe())


def verify_password(plain: str, hashed: str | None) -> bool:
    """Return True if the plain-text password matches the bcrypt hash.

    Without a hash (unknown user), or for input bcrypt cannot check (stored passwords are
    at most 72 bytes, so it can never match), it still runs bcrypt against a dummy hash and
    returns False. Response times therefore do not reveal whether a username exists.
    """
    password = plain.encode()
    if hashed is None or len(password) > BCRYPT_MAX_BYTES:
        bcrypt.checkpw(password[:BCRYPT_MAX_BYTES], _dummy_password_hash().encode())
        return False
    return bcrypt.checkpw(password, hashed.encode())


def create_access_token(subject: uuid.UUID) -> str:
    """Create a signed JWT access token for the given user id."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token, raising InvalidTokenError on failure."""
    return jwt.decode(
        token, settings.secret_key.get_secret_value(), algorithms=[settings.algorithm]
    )


def generate_refresh_token() -> str:
    """Generate an opaque, URL-safe refresh token with 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 hex digest of a refresh token for storage and lookup."""
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expiry() -> datetime:
    """Return the expiry timestamp for a refresh token issued now."""
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
