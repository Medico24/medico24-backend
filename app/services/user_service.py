"""User service for business logic."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import users
from app.schemas.users import UserCreate, UserUpdate


class UserService:
    """Service for user operations."""

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> dict:
        """Create a new user."""
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
            )
            .returning(users)
        )

        result = await db.execute(query)
        await db.commit()
        return result.mappings().first()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> dict | None:
        """Get user by internal ID."""
        query = select(users).where(users.c.id == user_id)
        result = await db.execute(query)
        return result.mappings().first()

    @staticmethod
    async def get_user_by_firebase_uid(db: AsyncSession, firebase_uid: str) -> dict | None:
        """Get user by Firebase UID."""
        query = select(users).where(users.c.firebase_uid == firebase_uid)
        result = await db.execute(query)
        return result.mappings().first()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> dict | None:
        """Get user by email."""
        query = select(users).where(users.c.email == email)
        result = await db.execute(query)
        return result.mappings().first()

    @staticmethod
    async def get_or_create_user(
        db: AsyncSession, firebase_uid: str, email: str, user_data: UserCreate | None = None
    ) -> dict:
        """Get existing user or create a new one."""
        # Try to get existing user
        user = await UserService.get_user_by_firebase_uid(db, firebase_uid)

        if user:
            # Update last login
            await UserService.update_last_login(db, user["id"])
            return user

        # Create new user if not exists
        if not user_data:
            user_data = UserCreate(
                firebase_uid=firebase_uid,
                email=email,
                email_verified=True,
            )

        return await UserService.create_user(db, user_data)

    @staticmethod
    async def update_user(db: AsyncSession, user_id: UUID, user_data: UserUpdate) -> dict | None:
        """Update user profile."""
        # Prepare update data
        update_data = user_data.model_dump(exclude_unset=True)
        if not update_data:
            return await UserService.get_user_by_id(db, user_id)

        update_data["updated_at"] = datetime.now(UTC)

        query = update(users).where(users.c.id == user_id).values(**update_data).returning(users)

        result = await db.execute(query)
        await db.commit()
        return result.mappings().first()

    @staticmethod
    async def update_last_login(db: AsyncSession, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        query = update(users).where(users.c.id == user_id).values(last_login_at=datetime.now(UTC))
        await db.execute(query)
        await db.commit()

    @staticmethod
    async def mark_onboarded(db: AsyncSession, user_id: UUID) -> dict | None:
        """Mark user as onboarded."""
        query = (
            update(users)
            .where(users.c.id == user_id)
            .values(is_onboarded=True, updated_at=datetime.now(UTC))
            .returning(users)
        )

        result = await db.execute(query)
        await db.commit()
        return result.mappings().first()

    @staticmethod
    async def deactivate_user(db: AsyncSession, user_id: UUID) -> dict | None:
        """Deactivate a user account."""
        query = (
            update(users)
            .where(users.c.id == user_id)
            .values(is_active=False, updated_at=datetime.now(UTC))
            .returning(users)
        )

        result = await db.execute(query)
        await db.commit()
        return result.mappings().first()

    @staticmethod
    async def activate_user(db: AsyncSession, user_id: UUID) -> dict | None:
        """Activate a user account."""
        query = (
            update(users)
            .where(users.c.id == user_id)
            .values(is_active=True, updated_at=datetime.now(UTC))
            .returning(users)
        )

        result = await db.execute(query)
        await db.commit()
        return result.mappings().first()

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: UUID) -> bool:
        """Delete a user (hard delete)."""
        query = delete(users).where(users.c.id == user_id)
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0
