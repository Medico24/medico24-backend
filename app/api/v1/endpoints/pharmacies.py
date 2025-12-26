"""Pharmacy endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.pharmacies import (
    PharmacyCreate,
    PharmacyHoursCreate,
    PharmacyHoursInDB,
    PharmacyListResponse,
    PharmacyLocationUpdate,
    PharmacyResponse,
    PharmacyUpdate,
)
from app.services.pharmacy_service import PharmacyService

router = APIRouter(prefix="/pharmacies", tags=["pharmacies"])


@router.post("", response_model=PharmacyResponse, status_code=status.HTTP_201_CREATED)
async def create_pharmacy(
    pharmacy_data: PharmacyCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new pharmacy with location and hours."""
    try:
        pharmacy = await PharmacyService.create_pharmacy(db, pharmacy_data)
        return PharmacyResponse.model_validate(pharmacy)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create pharmacy: {e!s}",
        )


@router.get("", response_model=list[PharmacyListResponse])
async def list_pharmacies(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    is_active: bool = Query(True, description="Filter by active status"),
    is_verified: bool | None = Query(None, description="Filter by verified status"),
    supports_delivery: bool | None = Query(None, description="Filter by delivery support"),
    supports_pickup: bool | None = Query(None, description="Filter by pickup support"),
    db: AsyncSession = Depends(get_db),
):
    """Get list of pharmacies with optional filtering."""
    pharmacies_list = await PharmacyService.get_pharmacies(
        db=db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        is_verified=is_verified,
        supports_delivery=supports_delivery,
        supports_pickup=supports_pickup,
    )

    return [PharmacyListResponse.model_validate(p) for p in pharmacies_list]


@router.get("/search/nearby", response_model=list[PharmacyListResponse])
async def search_pharmacies_nearby(
    latitude: float = Query(..., ge=-90, le=90, description="Search latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Search longitude"),
    radius_km: float = Query(10.0, gt=0, le=100, description="Search radius in kilometers"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    is_active: bool = Query(True, description="Filter by active status"),
    is_verified: bool | None = Query(None, description="Filter by verified status"),
    supports_delivery: bool | None = Query(None, description="Filter by delivery support"),
    supports_pickup: bool | None = Query(None, description="Filter by pickup support"),
    db: AsyncSession = Depends(get_db),
):
    """Search pharmacies within a radius using geographic location."""
    pharmacies_list = await PharmacyService.search_pharmacies_nearby(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        skip=skip,
        limit=limit,
        is_active=is_active,
        is_verified=is_verified,
        supports_delivery=supports_delivery,
        supports_pickup=supports_pickup,
    )

    return [PharmacyListResponse.model_validate(p) for p in pharmacies_list]


@router.get("/{pharmacy_id}", response_model=PharmacyResponse)
async def get_pharmacy(
    pharmacy_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific pharmacy."""
    pharmacy = await PharmacyService.get_pharmacy_by_id(db, pharmacy_id)

    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found",
        )

    return PharmacyResponse.model_validate(pharmacy)


@router.patch("/{pharmacy_id}", response_model=PharmacyResponse)
async def update_pharmacy(
    pharmacy_id: UUID,
    pharmacy_data: PharmacyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update pharmacy information."""
    pharmacy = await PharmacyService.update_pharmacy(db, pharmacy_id, pharmacy_data)

    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found",
        )

    return PharmacyResponse.model_validate(pharmacy)


@router.delete("/{pharmacy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pharmacy(
    pharmacy_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a pharmacy."""
    success = await PharmacyService.delete_pharmacy(db, pharmacy_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found",
        )


@router.patch("/{pharmacy_id}/location", response_model=PharmacyResponse)
async def update_pharmacy_location(
    pharmacy_id: UUID,
    location_data: PharmacyLocationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update pharmacy location."""
    pharmacy = await PharmacyService.update_pharmacy_location(db, pharmacy_id, location_data)

    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found",
        )

    return PharmacyResponse.model_validate(pharmacy)


@router.post(
    "/{pharmacy_id}/hours", response_model=PharmacyHoursInDB, status_code=status.HTTP_201_CREATED
)
async def add_pharmacy_hours(
    pharmacy_id: UUID,
    hours_data: PharmacyHoursCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add or update pharmacy hours for a specific day."""
    # First check if pharmacy exists
    pharmacy = await PharmacyService.get_pharmacy_by_id(db, pharmacy_id)
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found",
        )

    hours = await PharmacyService.add_pharmacy_hours(db, pharmacy_id, hours_data)

    if not hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add pharmacy hours",
        )

    return PharmacyHoursInDB.model_validate(hours)


@router.get("/{pharmacy_id}/hours", response_model=list[PharmacyHoursInDB])
async def get_pharmacy_hours(
    pharmacy_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all hours for a pharmacy."""
    # First check if pharmacy exists
    pharmacy = await PharmacyService.get_pharmacy_by_id(db, pharmacy_id)
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found",
        )

    hours = await PharmacyService.get_pharmacy_hours(db, pharmacy_id)
    return [PharmacyHoursInDB.model_validate(h) for h in hours]


@router.delete("/{pharmacy_id}/hours/{day_of_week}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pharmacy_hours(
    pharmacy_id: UUID,
    day_of_week: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete pharmacy hours for a specific day (1=Monday, 7=Sunday)."""
    if not 1 <= day_of_week <= 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="day_of_week must be between 1 (Monday) and 7 (Sunday)",
        )

    success = await PharmacyService.delete_pharmacy_hours(db, pharmacy_id, day_of_week)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy hours not found",
        )
