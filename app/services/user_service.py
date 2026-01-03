"""User service for business logic."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import CacheManager
from app.models.admins import admins
from app.models.doctors import doctors
from app.models.patients import patients
from app.models.pharmacy_staff import pharmacy_staff
from app.models.users import users
from app.schemas.users import UserCreate, UserUpdate


class UserService:
    """Service for user operations."""

    # Cache TTL in seconds (30 minutes for user profiles)
    USER_CACHE_TTL = 1800

    def __init__(self, cache_manager: CacheManager | None = None):
        """Initialize service with optional cache manager."""
        self.cache = cache_manager

    @staticmethod
    def _get_user_cache_key(user_id: UUID) -> str:
        """Generate cache key for user."""
        return f"user:{user_id}"

    async def create_user(
        self, db: AsyncSession, user_data: UserCreate, pharmacy_id: UUID | None = None
    ) -> dict:
        """Create a new user and associated role record.

        Args:
            db: Database session
            user_data: User creation data
            pharmacy_id: Required if role is 'pharmacy' - the pharmacy this staff member belongs to

        Note:
            Role-specific records are automatically created by database triggers.
            For pharmacy users, we update the pharmacy_id after creation.
        """
        # Determine role (default to 'patient' if not specified)
        role = user_data.role if hasattr(user_data, "role") and user_data.role else "patient"

        # Validate pharmacy_id for pharmacy role
        if role == "pharmacy" and not pharmacy_id:
            raise ValueError("pharmacy_id is required when creating a pharmacy staff user")

        query = (
            users.insert()
            .values(
                firebase_uid=user_data.firebase_uid,
                email=user_data.email,
                email_verified=user_data.email_verified,
                auth_provider=user_data.auth_provider,
                full_name=user_data.full_name,
                given_name=user_data.given_name,
                family_name=user_data.family_name,
                photo_url=user_data.photo_url,
                phone=user_data.phone,
                role=role,
            )
            .returning(users)
        )

        result = await db.execute(query)
        user = result.mappings().first()

        if not user:
            raise ValueError("Failed to create user")

        user_dict = dict(user)
        user_id = user_dict["id"]

        # Database trigger automatically creates role record
        # For pharmacy staff, update the pharmacy_id
        if role == "pharmacy" and pharmacy_id:
            await db.execute(
                update(pharmacy_staff)
                .where(pharmacy_staff.c.user_id == user_id)
                .values(pharmacy_id=pharmacy_id)
            )

        await db.commit()

        # Cache the new user
        if self.cache:
            cache_key = self._get_user_cache_key(user_dict["id"])
            self.cache.set_json(cache_key, user_dict, ttl=self.USER_CACHE_TTL)

        return user_dict

    async def get_user_by_id(self, db: AsyncSession, user_id: UUID) -> dict | None:
        """Get user by internal ID with caching."""
        # Try cache first
        if self.cache:
            cache_key = self._get_user_cache_key(user_id)
            cached_user = self.cache.get_json(cache_key)
            if cached_user:
                return cached_user

        # Query database
        query = select(users).where(users.c.id == user_id)
        result = await db.execute(query)
        user = result.mappings().first()

        if not user:
            return None

        user_dict = dict(user)

        # Cache the result
        if self.cache:
            cache_key = self._get_user_cache_key(user_id)
            self.cache.set_json(cache_key, user_dict, ttl=self.USER_CACHE_TTL)

        return user_dict

    async def get_user_by_firebase_uid(self, db: AsyncSession, firebase_uid: str) -> dict | None:
        """Get user by Firebase UID."""
        query = select(users).where(users.c.firebase_uid == firebase_uid)
        result = await db.execute(query)
        user = result.mappings().first()
        return dict(user) if user else None

    async def get_user_by_email(self, db: AsyncSession, email: str) -> dict | None:
        """Get user by email."""
        query = select(users).where(users.c.email == email)
        result = await db.execute(query)
        user = result.mappings().first()
        return dict(user) if user else None

    async def get_or_create_user(
        self, db: AsyncSession, firebase_uid: str, email: str, user_data: UserCreate | None = None
    ) -> dict:
        """Get existing user or create a new one."""
        # Try to get existing user
        user = await self.get_user_by_firebase_uid(db, firebase_uid)

        if user:
            # Update last login
            await self.update_last_login(db, user["id"])
            return user

        # Create new user if not exists
        if not user_data:
            user_data = UserCreate(
                firebase_uid=firebase_uid,
                email=email,
                email_verified=True,
                phone=None,
            )

        return await self.create_user(db, user_data)

    async def update_user(
        self, db: AsyncSession, user_id: UUID, user_data: UserUpdate
    ) -> dict | None:
        """Update user profile."""
        # Prepare update data
        update_data = user_data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_user_by_id(db, user_id)

        update_data["updated_at"] = datetime.now(UTC)

        query = update(users).where(users.c.id == user_id).values(**update_data).returning(users)

        result = await db.execute(query)
        await db.commit()
        user = result.mappings().first()

        if not user:
            return None

        user_dict = dict(user)

        # Invalidate cache
        if self.cache:
            cache_key = self._get_user_cache_key(user_id)
            self.cache.delete(cache_key)

        return user_dict

    async def update_last_login(self, db: AsyncSession, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        query = update(users).where(users.c.id == user_id).values(last_login_at=datetime.now(UTC))
        await db.execute(query)
        await db.commit()

        # Invalidate cache on last login update
        if self.cache:
            cache_key = self._get_user_cache_key(user_id)
            self.cache.delete(cache_key)

    async def mark_onboarded(self, db: AsyncSession, user_id: UUID) -> dict | None:
        """Mark user as onboarded."""
        query = (
            update(users)
            .where(users.c.id == user_id)
            .values(is_onboarded=True, updated_at=datetime.now(UTC))
            .returning(users)
        )

        result = await db.execute(query)
        await db.commit()
        user = result.mappings().first()

        if not user:
            return None

        user_dict = dict(user)

        # Invalidate cache
        if self.cache:
            cache_key = self._get_user_cache_key(user_id)
            self.cache.delete(cache_key)

        return user_dict

    async def deactivate_user(self, db: AsyncSession, user_id: UUID) -> dict | None:
        """Deactivate a user account."""
        query = (
            update(users)
            .where(users.c.id == user_id)
            .values(is_active=False, updated_at=datetime.now(UTC))
            .returning(users)
        )

        result = await db.execute(query)
        await db.commit()
        user = result.mappings().first()

        if not user:
            return None

        user_dict = dict(user)

        # Invalidate cache
        if self.cache:
            cache_key = self._get_user_cache_key(user_id)
            self.cache.delete(cache_key)

        return user_dict

    async def activate_user(self, db: AsyncSession, user_id: UUID) -> dict | None:
        """Activate a user account."""
        query = (
            update(users)
            .where(users.c.id == user_id)
            .values(is_active=True, updated_at=datetime.now(UTC))
            .returning(users)
        )

        result = await db.execute(query)
        await db.commit()
        user = result.mappings().first()

        if not user:
            return None

        user_dict = dict(user)

        # Invalidate cache
        if self.cache:
            cache_key = self._get_user_cache_key(user_id)
            self.cache.delete(cache_key)

        return user_dict

    async def delete_user(self, db: AsyncSession, user_id: UUID) -> bool:
        """Delete a user (hard delete)."""
        query = delete(users).where(users.c.id == user_id)
        result = await db.execute(query)
        await db.commit()

        # Invalidate cache
        if self.cache:
            cache_key = self._get_user_cache_key(user_id)
            self.cache.delete(cache_key)

        return result.rowcount > 0  # type: ignore[attr-defined]

    async def update_user_role(
        self, db: AsyncSession, user_id: UUID, new_role: str, pharmacy_id: UUID | None = None
    ) -> dict | None:
        """Update user role and create/delete corresponding role records.

        Args:
            db: Database session
            user_id: User ID to update
            new_role: New role to assign
            pharmacy_id: Required if new_role is 'pharmacy'

        Note:
            Database triggers automatically handle role record deletion/creation.
            For pharmacy users, we update the pharmacy_id after role change.
        """
        # Get current user
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return None

        old_role = user.get("role", "patient")

        if old_role == new_role:
            return user  # No change needed

        # Validate pharmacy_id for pharmacy role
        if new_role == "pharmacy" and not pharmacy_id:
            raise ValueError("pharmacy_id is required when changing role to pharmacy")

        # Update users table role (trigger handles role table changes)
        query = (
            update(users)
            .where(users.c.id == user_id)
            .values(role=new_role, updated_at=datetime.now(UTC))
            .returning(users)
        )

        result = await db.execute(query)
        user = result.mappings().first()

        if not user:
            return None

        user_dict = dict(user)

        # Database trigger automatically deletes old role record and creates new one
        # For pharmacy staff, update the pharmacy_id
        if new_role == "pharmacy" and pharmacy_id:
            await db.execute(
                update(pharmacy_staff)
                .where(pharmacy_staff.c.user_id == user_id)
                .values(pharmacy_id=pharmacy_id)
            )

        await db.commit()

        # Invalidate cache
        if self.cache:
            cache_key = self._get_user_cache_key(user_id)
            self.cache.delete(cache_key)

        return user_dict

    async def get_patient_profile(self, db: AsyncSession, user_id: UUID) -> dict | None:
        """Get patient-specific profile data."""
        query = select(patients).where(patients.c.user_id == user_id)
        result = await db.execute(query)
        patient = result.mappings().first()
        return dict(patient) if patient else None

    async def get_doctor_profile(self, db: AsyncSession, user_id: UUID) -> dict | None:
        """Get doctor-specific profile data."""
        query = select(doctors).where(doctors.c.user_id == user_id)
        result = await db.execute(query)
        doctor = result.mappings().first()
        return dict(doctor) if doctor else None

    async def get_pharmacy_staff_profile(self, db: AsyncSession, user_id: UUID) -> dict | None:
        """Get pharmacy staff-specific profile data."""
        query = select(pharmacy_staff).where(pharmacy_staff.c.user_id == user_id)
        result = await db.execute(query)
        staff = result.mappings().first()
        return dict(staff) if staff else None

    async def get_admin_profile(self, db: AsyncSession, user_id: UUID) -> dict | None:
        """Get admin-specific profile data."""
        query = select(admins).where(admins.c.user_id == user_id)
        result = await db.execute(query)
        admin = result.mappings().first()
        return dict(admin) if admin else None
