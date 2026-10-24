import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbDep
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_tokens(db: AsyncSession, user_id: uuid.UUID) -> Token:
    """Persist a new hashed refresh token and return it with a fresh access token.

    The user's revoked and expired tokens are deleted here, so the table stays bounded.
    """
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            or_(RefreshToken.revoked, RefreshToken.expires_at <= datetime.now(UTC)),
        )
    )
    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            token_hash=hash_refresh_token(raw_refresh),
            user_id=user_id,
            expires_at=refresh_token_expiry(),
        )
    )
    await db.commit()
    return Token(access_token=create_access_token(user_id), refresh_token=raw_refresh)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: DbDep) -> User:
    """Register a new user, rejecting a duplicate email or username."""
    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=await asyncio.to_thread(hash_password, payload.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email or username already taken"
        ) from None

    await db.refresh(user)
    logger.info("user registered", extra={"user_id": str(user.id)})
    return user


@router.post("/login", response_model=Token)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbDep) -> Token:
    """Authenticate with username and password and return a new token pair."""
    result = await db.execute(select(User).where(User.username == form.username.lower()))
    user = result.scalar_one_or_none()
    # bcrypt is deliberately slow; run it off the event loop so other requests keep flowing.
    password_ok = await asyncio.to_thread(
        verify_password, form.password, user.hashed_password if user else None
    )

    if user is None or not password_ok:
        logger.warning("login failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return await _issue_tokens(db, user.id)


@router.post("/refresh", response_model=Token)
async def refresh_tokens(payload: RefreshTokenRequest, db: DbDep) -> Token:
    """Rotate a refresh token: revoke it atomically and issue a new token pair."""
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_refresh_token(payload.refresh_token),
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        .values(revoked=True)
        .returning(RefreshToken.user_id)
    )
    user_id = result.scalar_one_or_none()
    user = await db.get(User, user_id) if user_id else None

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )
    return await _issue_tokens(db, user.id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshTokenRequest, current_user: CurrentUser, db: DbDep) -> None:
    """Revoke the caller's refresh token. Unknown or already-revoked tokens are a no-op."""
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_refresh_token(payload.refresh_token),
            RefreshToken.user_id == current_user.id,
        )
        .values(revoked=True)
    )
    await db.commit()


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: CurrentUser) -> User:
    """Return the profile of the currently authenticated user."""
    return current_user
