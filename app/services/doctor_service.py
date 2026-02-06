"""Doctor service for business logic."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import CacheManager
from app.models.clinics import clinics
from app.models.doctor_clinics import doctor_clinics
from app.models.doctors import doctors
from app.models.users import users
from app.schemas.doctors import DoctorCreate, DoctorUpdate


class DoctorService:
    """Service for doctor operations."""

    # Cache TTL in seconds
    DOCTOR_CACHE_TTL = 900  # 15 minutes for individual doctors
    DOCTOR_LIST_CACHE_TTL = 300  # 5 minutes for lists

    def __init__(self, cache_manager: CacheManager | None = None):
        """Initialize service with optional cache manager."""
        self.cache = cache_manager

    @staticmethod
    def _get_doctor_cache_key(doctor_id: UUID) -> str:
        """Generate cache key for doctor."""
        return f"doctor:{doctor_id}"

    async def create_doctor(self, db: AsyncSession, doctor_data: DoctorCreate) -> dict:
        """Create a new doctor profile."""
        query = (
            doctors.insert()
            .values(
                user_id=doctor_data.user_id,
                license_number=doctor_data.license_number,
                specialization=doctor_data.specialization,
                sub_specialization=doctor_data.sub_specialization,
                qualification=doctor_data.qualification,
                experience_years=doctor_data.experience_years,
                consultation_fee=doctor_data.consultation_fee,
                consultation_duration_minutes=doctor_data.consultation_duration_minutes,
                bio=doctor_data.bio,
                languages_spoken=doctor_data.languages_spoken,
                medical_council_registration=doctor_data.medical_council_registration,
            )
            .returning(doctors)
        )

        result = await db.execute(query)
        doctor = result.mappings().first()

        if not doctor:
            raise ValueError("Failed to create doctor")

        await db.commit()

        # Invalidate cache
        if self.cache:
            self.cache.delete_pattern("doctor:list:*")

        return dict(doctor)

    async def get_doctor_by_id(self, db: AsyncSession, doctor_id: UUID) -> dict | None:
        """Get doctor by ID with caching."""
        # Try cache first
        if self.cache:
            cache_key = self._get_doctor_cache_key(doctor_id)
            cached = self.cache.get_json(cache_key)
            if cached:
                return cached

        # Query database
        query = select(doctors).where(doctors.c.id == doctor_id)
        result = await db.execute(query)
        doctor = result.mappings().first()

        if not doctor:
            return None

        doctor_dict = dict(doctor)

        # Cache result
        if self.cache:
            cache_key = self._get_doctor_cache_key(doctor_id)
            self.cache.set_json(cache_key, doctor_dict, ttl=self.DOCTOR_CACHE_TTL)

        return doctor_dict

    async def get_doctor_with_details(self, db: AsyncSession, doctor_id: UUID) -> dict | None:
        """Get doctor with user details and clinic associations."""
        # Get doctor
        doctor = await self.get_doctor_by_id(db, doctor_id)
        if not doctor:
            return None

        # Get user details
        user_query = select(users).where(users.c.id == doctor["user_id"])
        user_result = await db.execute(user_query)
        user = user_result.mappings().first()

        if user:
            doctor["full_name"] = user["full_name"]
            doctor["email"] = user["email"]
            doctor["phone_number"] = user["phone_number"]
            doctor["profile_picture_url"] = user["profile_picture_url"]

        # Get clinic associations
        clinics_query = (
            select(
                doctor_clinics,
                clinics.c.name.label("clinic_name"),
                clinics.c.address.label("clinic_address"),
                clinics.c.latitude,
                clinics.c.longitude,
            )
            .join(clinics, doctor_clinics.c.clinic_id == clinics.c.id)
            .where(
                doctor_clinics.c.doctor_id == doctor_id,
                doctor_clinics.c.status == "active",
                doctor_clinics.c.end_date.is_(None),
            )
            .order_by(doctor_clinics.c.is_primary.desc())
        )

        clinics_result = await db.execute(clinics_query)
        doctor["clinics"] = [dict(row) for row in clinics_result.mappings().all()]

        return doctor

    async def get_doctor_by_user_id(self, db: AsyncSession, user_id: UUID) -> dict | None:
        """Get doctor by user ID."""
        query = select(doctors).where(doctors.c.user_id == user_id)
        result = await db.execute(query)
        doctor = result.mappings().first()

        return dict(doctor) if doctor else None

    async def get_doctors(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        specialization: str | None = None,
        sub_specialization: str | None = None,
        min_experience: int | None = None,
        max_experience: int | None = None,
        is_verified: bool | None = None,
        min_rating: float | None = None,
        languages: list[str] | None = None,
    ) -> list[dict]:
        """Get list of doctors with filtering."""
        # Build query with user join for name
        conditions: list = []

        if specialization:
            conditions.append(doctors.c.specialization.ilike(f"%{specialization}%"))

        if sub_specialization:
            conditions.append(doctors.c.sub_specialization.ilike(f"%{sub_specialization}%"))

        if min_experience is not None:
            conditions.append(doctors.c.experience_years >= min_experience)

        if max_experience is not None:
            conditions.append(doctors.c.experience_years <= max_experience)

        if is_verified is not None:
            conditions.append(doctors.c.is_verified == is_verified)

        if min_rating is not None:
            conditions.append(doctors.c.rating >= min_rating)

        if languages:
            # Check if any of the specified languages are in the languages_spoken array
            for lang in languages:
                conditions.append(doctors.c.languages_spoken.contains([lang]))

        # Join with users to get full name
        query = (
            select(
                doctors,
                users.c.full_name,
                users.c.profile_picture_url,
            )
            .join(users, doctors.c.user_id == users.c.id)
            .where(and_(*conditions) if conditions else True)
            .order_by(doctors.c.rating.desc().nullslast(), doctors.c.experience_years.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        doctor_list = result.mappings().all()

        return [dict(d) for d in doctor_list]

    async def search_doctors_nearby(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
        specialization: str | None = None,
        skip: int = 0,
        limit: int = 20,
        is_verified: bool = True,
        min_rating: float | None = None,
    ) -> list[dict]:
        """Search doctors near a location (through their clinic associations)."""
        conditions: list = [
            clinics.c.deleted_at.is_(None),
            clinics.c.latitude.isnot(None),
            clinics.c.longitude.isnot(None),
            doctor_clinics.c.status == "active",
            doctor_clinics.c.end_date.is_(None),
            doctor_clinics.c.appointment_booking_enabled == True,  # noqa: E712
        ]

        if is_verified:
            conditions.append(doctors.c.is_verified == True)  # noqa: E712

        if specialization:
            conditions.append(doctors.c.specialization.ilike(f"%{specialization}%"))

        if min_rating is not None:
            conditions.append(doctors.c.rating >= min_rating)

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
            select(
                doctors,
                users.c.full_name,
                users.c.profile_picture_url,
                clinics.c.name.label("clinic_name"),
                clinics.c.address.label("clinic_address"),
                doctor_clinics.c.consultation_fee.label("clinic_consultation_fee"),
                distance_formula.label("distance_km"),
            )
            .join(doctor_clinics, doctors.c.id == doctor_clinics.c.doctor_id)
            .join(clinics, doctor_clinics.c.clinic_id == clinics.c.id)
            .join(users, doctors.c.user_id == users.c.id)
            .where(and_(*conditions))
            .having(distance_formula <= radius_km)
            .order_by(distance_formula, doctors.c.rating.desc().nullslast())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        rows = result.mappings().all()

        return [dict(row) for row in rows]

    async def update_doctor(  # noqa: C901
        self, db: AsyncSession, doctor_id: UUID, doctor_data: DoctorUpdate
    ) -> dict | None:
        """Update doctor information."""
        # Check if doctor exists
        existing = await self.get_doctor_by_id(db, doctor_id)
        if not existing:
            return None

        # Build update values
        update_values = {}
        if doctor_data.specialization is not None:
            update_values["specialization"] = doctor_data.specialization
        if doctor_data.sub_specialization is not None:
            update_values["sub_specialization"] = doctor_data.sub_specialization
        if doctor_data.qualification is not None:
            update_values["qualification"] = doctor_data.qualification
        if doctor_data.experience_years is not None:
            update_values["experience_years"] = doctor_data.experience_years
        if doctor_data.consultation_fee is not None:
            update_values["consultation_fee"] = doctor_data.consultation_fee
        if doctor_data.consultation_duration_minutes is not None:
            update_values["consultation_duration_minutes"] = (
                doctor_data.consultation_duration_minutes
            )
        if doctor_data.bio is not None:
            update_values["bio"] = doctor_data.bio
        if doctor_data.languages_spoken is not None:
            update_values["languages_spoken"] = doctor_data.languages_spoken
        if doctor_data.medical_council_registration is not None:
            update_values["medical_council_registration"] = doctor_data.medical_council_registration

        if not update_values:
            return existing

        # Update doctor
        from sqlalchemy import update

        query = (
            update(doctors)
            .where(doctors.c.id == doctor_id)
            .values(**update_values)
            .returning(doctors)
        )

        result = await db.execute(query)
        updated_doctor = result.mappings().first()

        await db.commit()

        # Invalidate cache
        if self.cache:
            cache_key = self._get_doctor_cache_key(doctor_id)
            self.cache.delete(cache_key)
            self.cache.delete_pattern("doctor:list:*")

        return dict(updated_doctor) if updated_doctor else None

    async def verify_doctor(
        self,
        db: AsyncSession,
        doctor_id: UUID,
        verified_by: UUID,
        verification_docs: dict | None = None,
    ) -> dict | None:
        """Verify a doctor."""
        from sqlalchemy import update

        update_values = {
            "is_verified": True,
            "verified_at": datetime.now(UTC),
            "verified_by": verified_by,
        }

        if verification_docs:
            update_values["verification_documents"] = verification_docs

        query = (
            update(doctors)
            .where(doctors.c.id == doctor_id)
            .values(**update_values)
            .returning(doctors)
        )

        result = await db.execute(query)
        updated_doctor = result.mappings().first()

        await db.commit()

        # Invalidate cache
        if self.cache:
            cache_key = self._get_doctor_cache_key(doctor_id)
            self.cache.delete(cache_key)

        return dict(updated_doctor) if updated_doctor else None

    async def unverify_doctor(self, db: AsyncSession, doctor_id: UUID) -> dict | None:
        """Unverify a doctor."""
        from sqlalchemy import update

        query = (
            update(doctors)
            .where(doctors.c.id == doctor_id)
            .values(is_verified=False, verified_at=None, verified_by=None)
            .returning(doctors)
        )

        result = await db.execute(query)
        updated_doctor = result.mappings().first()

        await db.commit()

        # Invalidate cache
        if self.cache:
            cache_key = self._get_doctor_cache_key(doctor_id)
            self.cache.delete(cache_key)

        return dict(updated_doctor) if updated_doctor else None
