import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LogoutRequest, RefreshRequest, Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token string for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DbDep) -> User:
    """Register a new user, rejecting duplicate email or username."""
    result = await db.execute(
        select(User).where(
            (User.email == payload.email) | (User.username == payload.username)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already taken",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDep,
) -> Token:
    """Authenticate a user and return a new access/refresh token pair."""
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            token_hash=_hash_token(raw_refresh),
            user_id=user.id,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()

    return Token(access_token=create_access_token(user.id), refresh_token=raw_refresh)


@router.post("/refresh", response_model=Token)
async def refresh_tokens(payload: RefreshRequest, db: DbDep) -> Token:
    """Rotate a refresh token and issue a new access/refresh token pair."""
    token_hash = _hash_token(payload.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()

    if not stored or stored.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    stored.revoked = True
    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            token_hash=_hash_token(raw_refresh),
            user_id=stored.user_id,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()

    return Token(
        access_token=create_access_token(stored.user_id), refresh_token=raw_refresh
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, current_user: CurrentUser, db: DbDep) -> None:
    """Revoke the provided refresh token, preventing further use for token rotation."""
    token_hash = _hash_token(payload.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == current_user.id,
        )
    )
    stored = result.scalar_one_or_none()

    if stored and not stored.revoked:
        stored.revoked = True
        await db.commit()


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> User:
    """Return the profile of the currently authenticated user."""
    return current_user
