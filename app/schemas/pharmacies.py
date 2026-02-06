"""Pharmacy schemas for request/response validation."""

from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator

# ============================================================================
# Pharmacy Hours Schemas
# ============================================================================


class PharmacyHoursBase(BaseModel):
    """Base schema for pharmacy hours."""

    day_of_week: int = Field(..., ge=1, le=7, description="Day of week: 1=Monday, 7=Sunday")
    open_time: time
    close_time: time
    is_closed: bool = False

    @field_validator("day_of_week")
    @classmethod
    def validate_day_of_week(cls, v: int) -> int:
        """Validate day_of_week is between 1 and 7."""
        if not 1 <= v <= 7:
            raise ValueError("day_of_week must be between 1 (Monday) and 7 (Sunday)")
        return v


class PharmacyHoursCreate(PharmacyHoursBase):
    """Schema for creating pharmacy hours."""


class PharmacyHoursUpdate(BaseModel):
    """Schema for updating pharmacy hours."""

    open_time: time | None = None
    close_time: time | None = None
    is_closed: bool | None = None


class PharmacyHoursInDB(PharmacyHoursBase):
    """Pharmacy hours schema as stored in database."""

    id: UUID
    pharmacy_id: UUID

    model_config = {"from_attributes": True}


# ============================================================================
# Pharmacy Location Schemas
# ============================================================================


class PharmacyLocationBase(BaseModel):
    """Base schema for pharmacy location."""

    address_line: str
    city: str
    state: str | None = None
    country: str = "India"
    pincode: str | None = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class PharmacyLocationCreate(PharmacyLocationBase):
    """Schema for creating a pharmacy location."""


class PharmacyLocationUpdate(BaseModel):
    """Schema for updating a pharmacy location."""

    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    pincode: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


class PharmacyLocationInDB(PharmacyLocationBase):
    """Pharmacy location schema as stored in database."""

    id: UUID
    pharmacy_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Pharmacy Schemas
# ============================================================================


class PharmacyBase(BaseModel):
    """Base schema for pharmacy."""

    name: str
    description: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    supports_delivery: bool = False
    supports_pickup: bool = True


class PharmacyCreate(PharmacyBase):
    """Schema for creating a pharmacy."""

    location: PharmacyLocationCreate
    hours: list[PharmacyHoursCreate] | None = None


class PharmacyUpdate(BaseModel):
    """Schema for updating a pharmacy."""

    name: str | None = None
    description: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    supports_delivery: bool | None = None
    supports_pickup: bool | None = None
    is_active: bool | None = None


class PharmacyInDB(PharmacyBase):
    """Pharmacy schema as stored in database."""

    id: UUID
    is_verified: bool
    is_active: bool
    rating: Decimal
    rating_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("rating", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Serialize Decimal to float for JSON."""
        return float(value) if value is not None else None


class PharmacyResponse(PharmacyInDB):
    """Pharmacy schema for API responses with location and hours."""

    location: PharmacyLocationInDB | None = None
    hours: list[PharmacyHoursInDB] = []


class PharmacyListResponse(PharmacyInDB):
    """Pharmacy schema for list responses with basic location info."""

    location: PharmacyLocationInDB | None = None
    distance_km: float | None = None  # Distance from search point


# ============================================================================
# Search Schemas
# ============================================================================


class PharmacySearchParams(BaseModel):
    """Schema for searching pharmacies."""

    latitude: float | None = Field(None, ge=-90, le=90, description="Search latitude")
    longitude: float | None = Field(None, ge=-180, le=180, description="Search longitude")
    radius_km: float = Field(10.0, gt=0, le=100, description="Search radius in kilometers")
    is_active: bool = True
    is_verified: bool | None = None
    supports_delivery: bool | None = None
    supports_pickup: bool | None = None
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)
