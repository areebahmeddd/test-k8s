import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_valid_hash():
    """Assert that hash_password returns a non-empty string distinct from the input."""
    hashed = hash_password("mysecret")
    assert hashed != "mysecret"
    assert len(hashed) > 0


def test_verify_password_correct():
    """Assert that verify_password returns True when the plain-text matches the stored hash."""
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed) is True


def test_verify_password_wrong():
    """Assert that verify_password returns False for a mismatched plain-text/hash pair."""
    hashed = hash_password("mysecret")
    assert verify_password("wrongpassword", hashed) is False


def test_create_and_decode_access_token():
    """Assert that a freshly created access token round-trips correctly through decode."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert "exp" in payload


def test_expired_token_raises():
    """Assert that decoding a token with a past expiry raises InvalidTokenError."""
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(UTC) - timedelta(seconds=1),
        "type": "access",
    }
    token = jwt.encode(
        expired_payload, settings.secret_key, algorithm=settings.algorithm
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_generate_refresh_token_is_unique():
    """Assert that successive calls to generate_refresh_token produce distinct UUID4 strings."""
    t1 = generate_refresh_token()
    t2 = generate_refresh_token()
    assert isinstance(t1, str)
    assert t1 != t2
