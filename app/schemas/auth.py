from pydantic import BaseModel


class Token(BaseModel):
    """Access/refresh token pair returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Request body carrying a refresh token, used by the refresh and logout endpoints."""

    refresh_token: str
