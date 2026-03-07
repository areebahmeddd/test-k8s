from pydantic import BaseModel


class Token(BaseModel):
    """Response schema carrying an access/refresh token pair returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Request body schema for the token-refresh endpoint."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Request body schema for the logout endpoint."""

    refresh_token: str
