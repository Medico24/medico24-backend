"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """JWT token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request schema."""

    refresh_token: str


class GoogleAuthRequest(BaseModel):
    """Firebase ID token authentication request."""

    id_token: str = Field(..., description="Firebase ID token from Flutter app")


class GoogleUserInfo(BaseModel):
    """Google user information."""

    id: str
    email: EmailStr
    name: str
    picture: str | None = None
    verified_email: bool = False


class UserResponse(BaseModel):
    """User response schema."""

    id: str
    email: EmailStr
    name: str
    picture: str | None = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Login response with tokens and user info."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
