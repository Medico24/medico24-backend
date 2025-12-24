"""User schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    full_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    photo_url: str | None = None
    phone: str | None = Field(None, max_length=20)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    firebase_uid: str = Field(..., description="Firebase user ID")
    email_verified: bool = False
    auth_provider: str = "google"


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    full_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    photo_url: str | None = None
    phone: str | None = Field(None, max_length=20)


class UserInDB(UserBase):
    """User schema as stored in database."""

    id: UUID
    firebase_uid: str
    email_verified: bool
    auth_provider: str
    role: str
    is_active: bool
    is_onboarded: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class UserResponse(UserInDB):
    """User schema for API responses."""


class UserProfile(BaseModel):
    """Public user profile schema."""

    id: UUID
    full_name: str | None = None
    photo_url: str | None = None
    role: str
    is_onboarded: bool

    class Config:
        """Pydantic config."""

        from_attributes = True
