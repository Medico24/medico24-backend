"""Clinic schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator

# ============================================================================
# Clinic Base Schemas
# ============================================================================


class ClinicBase(BaseModel):
    """Base schema for clinic."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=255, description="URL-friendly identifier")
    description: str | None = None
    logo_url: str | None = None
    contacts: dict | None = Field(
        None,
        description="Contact information: email, phone_primary, phone_secondary, website",
    )
    address: str = Field(..., min_length=1, description="Full address")
    latitude: Decimal | None = Field(None, ge=-90, le=90)
    longitude: Decimal | None = Field(None, ge=-180, le=180)
    opening_hours: dict | None = Field(
        None, description="Opening hours by day: {day: {open: time, close: time}}"
    )


class ClinicCreate(ClinicBase):
    """Schema for creating a clinic."""

    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v: str | None, info) -> str:
        """Generate slug from name if not provided."""
        if v is None and "name" in info.data:
            name = info.data["name"]
            return name.lower().replace(" ", "-").replace("_", "-")
        return v or ""


class ClinicUpdate(BaseModel):
    """Schema for updating a clinic."""

    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=255)
    description: str | None = None
    logo_url: str | None = None
    contacts: dict | None = None
    address: str | None = None
    latitude: Decimal | None = Field(None, ge=-90, le=90)
    longitude: Decimal | None = Field(None, ge=-180, le=180)
    opening_hours: dict | None = None
    status: str | None = Field(
        None, pattern="^(active|inactive|temporarily_closed|permanently_closed)$"
    )


class ClinicResponse(ClinicBase):
    """Clinic response schema."""

    id: UUID
    rating: Decimal | None = None
    rating_count: int = 0
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_serializer("latitude", "longitude", "rating", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Serialize Decimal to float for JSON."""
        return float(value) if value is not None else None


class ClinicListResponse(BaseModel):
    """Clinic schema for list responses."""

    id: UUID
    name: str
    slug: str | None
    description: str | None
    logo_url: str | None
    address: str
    latitude: Decimal | None
    longitude: Decimal | None
    rating: Decimal | None
    rating_count: int
    status: str
    is_active: bool
    distance_km: float | None = Field(
        None, description="Distance in kilometers (if location search)"
    )

    model_config = {"from_attributes": True}

    @field_serializer("latitude", "longitude", "rating", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Serialize Decimal to float for JSON."""
        return float(value) if value is not None else None


class ClinicItemResponse(BaseModel):
    """Individual clinic item (deprecated - use ClinicListResponse)."""

    id: UUID
    name: str
    slug: str | None
    description: str | None
    logo_url: str | None
    address: str
    latitude: Decimal | None
    longitude: Decimal | None
    rating: Decimal | None
    rating_count: int
    status: str
    is_active: bool
    distance_km: float | None = Field(
        None, description="Distance in kilometers (if location search)"
    )

    model_config = {"from_attributes": True}

    @field_serializer("latitude", "longitude", "rating", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Serialize Decimal to float for JSON."""
        return float(value) if value is not None else None


# ============================================================================
# Clinic Search/Filter Schemas
# ============================================================================


class ClinicSearchParams(BaseModel):
    """Clinic search parameters."""

    name: str | None = Field(None, description="Search by clinic name")
    city: str | None = Field(None, description="Filter by city (from address)")
    status: str | None = Field(
        None, pattern="^(active|inactive|temporarily_closed|permanently_closed)$"
    )
    is_active: bool = True
    min_rating: Decimal | None = Field(None, ge=0, le=5)


class ClinicNearbySearch(BaseModel):
    """Schema for nearby clinic search."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(10.0, gt=0, le=100, description="Search radius in kilometers")
    is_active: bool = True
    min_rating: Decimal | None = Field(None, ge=0, le=5)
