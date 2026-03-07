import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import bcrypt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plain-text password matches the bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: Any) -> str:
    """Create a signed JWT access token for the given subject (user id)."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token, raising InvalidTokenError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def generate_refresh_token() -> str:
    """Generate a cryptographically random refresh token as a UUID4 string."""
    return str(uuid.uuid4())
