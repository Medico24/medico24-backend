"""Clinic service for business logic."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import CacheManager
from app.models.clinics import clinics
from app.models.doctor_clinics import doctor_clinics
from app.models.doctors import doctors
from app.models.users import users
from app.schemas.clinics import ClinicCreate, ClinicUpdate
from app.schemas.doctor_clinics import DoctorClinicCreate, DoctorClinicUpdate


class ClinicService:
    """Service for clinic operations."""

    # Cache TTL in seconds
    CLINIC_CACHE_TTL = 900  # 15 minutes for individual clinics
    CLINIC_LIST_CACHE_TTL = 300  # 5 minutes for lists

    def __init__(self, cache_manager: CacheManager | None = None):
        """Initialize service with optional cache manager."""
        self.cache = cache_manager

    @staticmethod
    def _get_clinic_cache_key(clinic_id: UUID) -> str:
        """Generate cache key for clinic."""
        return f"clinic:{clinic_id}"

    @staticmethod
    def _get_clinic_list_cache_key(
        skip: int, limit: int, is_active: bool, status: str | None
    ) -> str:
        """Generate cache key for clinic list."""
        return f"clinic:list:{skip}:{limit}:{is_active}:{status}"

    async def create_clinic(self, db: AsyncSession, clinic_data: ClinicCreate) -> dict:
        """Create a new clinic."""
        clinic_query = (
            clinics.insert()
            .values(
                name=clinic_data.name,
                slug=clinic_data.slug,
                description=clinic_data.description,
                logo_url=clinic_data.logo_url,
                contacts=clinic_data.contacts,
                address=clinic_data.address,
                latitude=clinic_data.latitude,
                longitude=clinic_data.longitude,
                opening_hours=clinic_data.opening_hours,
            )
            .returning(clinics)
        )

        result = await db.execute(clinic_query)
        clinic = result.mappings().first()

        if not clinic:
            raise ValueError("Failed to create clinic")

        await db.commit()

        # Invalidate cache
        if self.cache:
            self.cache.delete_pattern("clinic:list:*")

        return dict(clinic)

    async def get_clinic_by_id(self, db: AsyncSession, clinic_id: UUID) -> dict | None:
        """Get clinic by ID with caching."""
        # Try cache first
        if self.cache:
            cache_key = self._get_clinic_cache_key(clinic_id)
            cached = self.cache.get_json(cache_key)
            if cached:
                return cached

        # Query database
        query = select(clinics).where(clinics.c.id == clinic_id, clinics.c.deleted_at.is_(None))

        result = await db.execute(query)
        clinic = result.mappings().first()

        if not clinic:
            return None

        clinic_dict = dict(clinic)

        # Cache result
        if self.cache:
            cache_key = self._get_clinic_cache_key(clinic_id)
            self.cache.set_json(cache_key, clinic_dict, ttl=self.CLINIC_CACHE_TTL)

        return clinic_dict

    async def get_clinic_by_slug(self, db: AsyncSession, slug: str) -> dict | None:
        """Get clinic by slug."""
        query = select(clinics).where(clinics.c.slug == slug, clinics.c.deleted_at.is_(None))

        result = await db.execute(query)
        clinic = result.mappings().first()

        return dict(clinic) if clinic else None

    async def get_clinics(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        is_active: bool = True,
        status: str | None = None,
        name_search: str | None = None,
        min_rating: float | None = None,
    ) -> list[dict]:
        """Get list of clinics with filtering."""
        # Build query
        conditions: list = [clinics.c.deleted_at.is_(None)]

        if is_active is not None:
            conditions.append(clinics.c.is_active == is_active)

        if status:
            conditions.append(clinics.c.status == status)

        if name_search:
            conditions.append(clinics.c.name.ilike(f"%{name_search}%"))

        if min_rating is not None:
            conditions.append(clinics.c.rating >= min_rating)

        query = (
            select(clinics)
            .where(and_(*conditions))
            .order_by(clinics.c.name)
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        clinic_list = result.mappings().all()

        return [dict(c) for c in clinic_list]

    async def search_clinics_nearby(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
        skip: int = 0,
        limit: int = 20,
        is_active: bool = True,
        min_rating: float | None = None,
    ) -> list[dict]:
        """Search clinics near a location (simplified without PostGIS)."""
        # Note: This is a simplified version using Haversine formula
        # For production, use PostGIS ST_DWithin for better performance

        conditions: list = [
            clinics.c.deleted_at.is_(None),
            clinics.c.latitude.isnot(None),
            clinics.c.longitude.isnot(None),
        ]

        if is_active is not None:
            conditions.append(clinics.c.is_active == is_active)

        if min_rating is not None:
            conditions.append(clinics.c.rating >= min_rating)

        # Haversine formula for distance calculation
        distance_formula = (
            func.acos(
                func.cos(func.radians(latitude))
                * func.cos(func.radians(clinics.c.latitude))
                * func.cos(func.radians(clinics.c.longitude) - func.radians(longitude))
                + func.sin(func.radians(latitude)) * func.sin(func.radians(clinics.c.latitude))
            )
            * 6371
        )  # Earth's radius in km

        query = (
            select(clinics, distance_formula.label("distance_km"))
            .where(and_(*conditions))
            .having(distance_formula <= radius_km)
            .order_by(distance_formula)
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        rows = result.mappings().all()

        return [dict(row) for row in rows]

    async def update_clinic(  # noqa: C901, PLR0912
        self, db: AsyncSession, clinic_id: UUID, clinic_data: ClinicUpdate
    ) -> dict | None:
        """Update clinic information."""
        # Check if clinic exists
        existing = await self.get_clinic_by_id(db, clinic_id)
        if not existing:
            return None

        # Build update values
        update_values: dict[str, Any] = {}
        if clinic_data.name is not None:
            update_values["name"] = clinic_data.name
        if clinic_data.slug is not None:
            update_values["slug"] = clinic_data.slug
        if clinic_data.description is not None:
            update_values["description"] = clinic_data.description
        if clinic_data.logo_url is not None:
            update_values["logo_url"] = clinic_data.logo_url
        if clinic_data.contacts is not None:
            update_values["contacts"] = clinic_data.contacts
        if clinic_data.address is not None:
            update_values["address"] = clinic_data.address
        if clinic_data.latitude is not None:
            update_values["latitude"] = clinic_data.latitude
        if clinic_data.longitude is not None:
            update_values["longitude"] = clinic_data.longitude
        if clinic_data.opening_hours is not None:
            update_values["opening_hours"] = clinic_data.opening_hours
        if clinic_data.status is not None:
            update_values["status"] = clinic_data.status

        if not update_values:
            return existing

        # Update clinic
        query = (
            update(clinics)
            .where(clinics.c.id == clinic_id)
            .values(**update_values)
            .returning(clinics)
        )

        result = await db.execute(query)
        updated_clinic = result.mappings().first()

        await db.commit()

        # Invalidate cache
        if self.cache:
            cache_key = self._get_clinic_cache_key(clinic_id)
            self.cache.delete(cache_key)
            self.cache.delete_pattern("clinic:list:*")

        return dict(updated_clinic) if updated_clinic else None

    async def soft_delete_clinic(self, db: AsyncSession, clinic_id: UUID) -> bool:
        """Soft delete a clinic."""
        query = (
            update(clinics)
            .where(clinics.c.id == clinic_id, clinics.c.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )

        await db.execute(query)
        await db.commit()

        # Invalidate cache
        if self.cache:
            cache_key = self._get_clinic_cache_key(clinic_id)
            self.cache.delete(cache_key)
            self.cache.delete_pattern("clinic:list:*")

        return True

    # ============================================================================
    # Doctor-Clinic Association Methods
    # ============================================================================

    async def add_doctor_to_clinic(
        self, db: AsyncSession, association_data: DoctorClinicCreate
    ) -> dict:
        """Add a doctor to a clinic."""
        query = (
            doctor_clinics.insert()
            .values(
                doctor_id=association_data.doctor_id,
                clinic_id=association_data.clinic_id,
                is_primary=association_data.is_primary,
                consultation_fee=association_data.consultation_fee,
                consultation_duration_minutes=association_data.consultation_duration_minutes,
                department=association_data.department,
                designation=association_data.designation,
                available_days=association_data.available_days,
                available_time_slots=association_data.available_time_slots,
                appointment_booking_enabled=association_data.appointment_booking_enabled,
            )
            .returning(doctor_clinics)
        )

        result = await db.execute(query)
        association = result.mappings().first()

        if not association:
            raise ValueError("Failed to create doctor-clinic association")

        await db.commit()

        # Invalidate cache
        if self.cache:
            self.cache.delete_pattern(f"clinic:{association_data.clinic_id}:doctors:*")
            self.cache.delete_pattern(f"doctor:{association_data.doctor_id}:clinics:*")

        return dict(association)

    async def get_clinic_doctors(
        self, db: AsyncSession, clinic_id: UUID, active_only: bool = True
    ) -> list[dict]:
        """Get all doctors at a clinic."""
        conditions: list = [doctor_clinics.c.clinic_id == clinic_id]

        if active_only:
            conditions.append(doctor_clinics.c.status == "active")
            conditions.append(doctor_clinics.c.end_date.is_(None))

        query = (
            select(
                doctor_clinics,
                doctors.c.license_number,
                doctors.c.specialization,
                doctors.c.experience_years,
                users.c.full_name.label("doctor_name"),
            )
            .join(doctors, doctor_clinics.c.doctor_id == doctors.c.id)
            .join(users, doctors.c.user_id == users.c.id)
            .where(and_(*conditions))
            .order_by(doctor_clinics.c.is_primary.desc(), users.c.full_name)
        )

        result = await db.execute(query)
        rows = result.mappings().all()

        return [dict(row) for row in rows]

    async def get_doctor_clinics(
        self, db: AsyncSession, doctor_id: UUID, active_only: bool = True
    ) -> list[dict]:
        """Get all clinics where a doctor works."""
        conditions: list = [doctor_clinics.c.doctor_id == doctor_id]

        if active_only:
            conditions.append(doctor_clinics.c.status == "active")
            conditions.append(doctor_clinics.c.end_date.is_(None))

        query = (
            select(
                doctor_clinics,
                clinics.c.name.label("clinic_name"),
                clinics.c.address.label("clinic_address"),
                clinics.c.latitude.label("clinic_latitude"),
                clinics.c.longitude.label("clinic_longitude"),
            )
            .join(clinics, doctor_clinics.c.clinic_id == clinics.c.id)
            .where(and_(*conditions))
            .order_by(doctor_clinics.c.is_primary.desc(), clinics.c.name)
        )

        result = await db.execute(query)
        rows = result.mappings().all()

        return [dict(row) for row in rows]

    async def update_doctor_clinic_association(  # noqa: C901
        self, db: AsyncSession, association_id: UUID, update_data: DoctorClinicUpdate
    ) -> dict | None:
        """Update doctor-clinic association."""
        # Build update values
        update_values: dict[str, Any] = {}
        if update_data.is_primary is not None:
            update_values["is_primary"] = update_data.is_primary
        if update_data.consultation_fee is not None:
            update_values["consultation_fee"] = update_data.consultation_fee
        if update_data.consultation_duration_minutes is not None:
            update_values["consultation_duration_minutes"] = (
                update_data.consultation_duration_minutes
            )
        if update_data.department is not None:
            update_values["department"] = update_data.department
        if update_data.designation is not None:
            update_values["designation"] = update_data.designation
        if update_data.available_days is not None:
            update_values["available_days"] = update_data.available_days
        if update_data.available_time_slots is not None:
            update_values["available_time_slots"] = update_data.available_time_slots
        if update_data.appointment_booking_enabled is not None:
            update_values["appointment_booking_enabled"] = update_data.appointment_booking_enabled
        if update_data.status is not None:
            update_values["status"] = update_data.status

        if not update_values:
            return None

        query = (
            update(doctor_clinics)
            .where(doctor_clinics.c.id == association_id)
            .values(**update_values)
            .returning(doctor_clinics)
        )

        result = await db.execute(query)
        updated = result.mappings().first()

        await db.commit()

        # Invalidate cache
        if self.cache and updated:
            self.cache.delete_pattern(f"clinic:{updated['clinic_id']}:doctors:*")
            self.cache.delete_pattern(f"doctor:{updated['doctor_id']}:clinics:*")

        return dict(updated) if updated else None

    async def end_doctor_clinic_association(
        self, db: AsyncSession, association_id: UUID, end_date: datetime | None = None
    ) -> dict | None:
        """End a doctor-clinic association."""
        if end_date is None:
            end_date = datetime.now(UTC)

        query = (
            update(doctor_clinics)
            .where(doctor_clinics.c.id == association_id)
            .values(end_date=end_date, status="inactive")
            .returning(doctor_clinics)
        )

        result = await db.execute(query)
        updated = result.mappings().first()

        await db.commit()

        # Invalidate cache
        if self.cache and updated:
            self.cache.delete_pattern(f"clinic:{updated['clinic_id']}:doctors:*")
            self.cache.delete_pattern(f"doctor:{updated['doctor_id']}:clinics:*")

        return dict(updated) if updated else None

    async def remove_doctor_from_clinic(
        self, db: AsyncSession, doctor_id: UUID, clinic_id: UUID
    ) -> bool:
        """Remove a doctor from a clinic (end active association)."""
        query = (
            update(doctor_clinics)
            .where(
                doctor_clinics.c.doctor_id == doctor_id,
                doctor_clinics.c.clinic_id == clinic_id,
                doctor_clinics.c.end_date.is_(None),
            )
            .values(end_date=datetime.now(UTC), status="inactive")
        )

        await db.execute(query)
        await db.commit()

        # Invalidate cache
        if self.cache:
            self.cache.delete_pattern(f"clinic:{clinic_id}:doctors:*")
            self.cache.delete_pattern(f"doctor:{doctor_id}:clinics:*")

        return True
