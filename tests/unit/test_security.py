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
    hash_refresh_token,
    verify_password,
)


def test_password_hash_verifies_only_the_original_password():
    """Assert that a bcrypt hash matches its own password and nothing else."""
    hashed = hash_password("mysecret")
    assert hashed != "mysecret"
    assert verify_password("mysecret", hashed)
    assert not verify_password("wrongpassword", hashed)


@pytest.mark.parametrize("hashed", [None, hash_password("x" * 72)], ids=["no-hash", "too-long"])
def test_verify_password_fails_safely(hashed: str | None):
    """Assert that a missing hash or over-long input is a mismatch rather than an error."""
    assert not verify_password("x" * 100, hashed)


def test_access_token_round_trips():
    """Assert that a created access token decodes to the same subject and type."""
    user_id = uuid.uuid4()
    payload = decode_access_token(create_access_token(user_id))
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert payload["exp"] > datetime.now(UTC).timestamp()


@pytest.mark.parametrize(
    ("key", "expires_in"),
    [
        (None, timedelta(seconds=-1)),
        ("another-key-that-is-at-least-32-bytes", timedelta(minutes=5)),
    ],
    ids=["expired", "wrong-signing-key"],
)
def test_decode_rejects_untrusted_tokens(key: str | None, expires_in: timedelta):
    """Assert that expired tokens and tokens signed with another key are rejected."""
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "exp": datetime.now(UTC) + expires_in},
        key or settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_refresh_tokens_are_unique_and_high_entropy():
    """Assert that refresh tokens never repeat and carry 256 bits (43 URL-safe chars)."""
    first, second = generate_refresh_token(), generate_refresh_token()
    assert first != second
    assert len(first) >= 43


def test_refresh_token_hash_is_stable_sha256():
    """Assert that hashing is deterministic, input-sensitive and yields 64 hex chars."""
    digest = hash_refresh_token("token")
    assert digest == hash_refresh_token("token")
    assert digest != hash_refresh_token("other")
    assert len(digest) == 64
