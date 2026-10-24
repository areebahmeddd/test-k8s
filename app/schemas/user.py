import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import BCRYPT_MAX_BYTES


class UserCreate(BaseModel):
    """Request schema for registering a new user account."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        """Store usernames lowercase so lookups are case-insensitive."""
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        """Reject passwords bcrypt cannot hash without truncation."""
        if len(v.encode()) > BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes")
        return v


class UserRead(BaseModel):
    """Public fields of a user account."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool
    created_at: datetime
