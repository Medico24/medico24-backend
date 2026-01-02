import os
import sys
from collections.abc import AsyncGenerator
from datetime import timedelta

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Load environment variables from .env file
load_dotenv()

# Combine all metadata
from sqlalchemy import MetaData

from app.config import settings
from app.core.security import create_access_token
from app.database import get_db
from app.main import app
from app.models.appointments import metadata as appointments_metadata
from app.models.notifications import metadata as notifications_metadata
from app.models.pharmacies import metadata as pharmacies_metadata
from app.models.push_tokens import metadata as push_tokens_metadata
from app.models.users import metadata as users_metadata

metadata = MetaData()
for table in appointments_metadata.tables.values():
    table.to_metadata(metadata)
for table in users_metadata.tables.values():
    table.to_metadata(metadata)
for table in pharmacies_metadata.tables.values():
    table.to_metadata(metadata)
for table in push_tokens_metadata.tables.values():
    table.to_metadata(metadata)
for table in notifications_metadata.tables.values():
    table.to_metadata(metadata)

# Test database URL - MUST be different from production
# Set TEST_DATABASE_URL in .env or use environment variable
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

# Safety check: prevent running tests against production database
if not TEST_DATABASE_URL:
    # Fallback to settings but add _test suffix to database name
    prod_url = settings.database_url
    # Extract database name and add _test suffix
    if "?" in prod_url:
        base_url, params = prod_url.rsplit("?", 1)
        db_name = base_url.rsplit("/", 1)[1]
        base_path = base_url.rsplit("/", 1)[0]
        TEST_DATABASE_URL = f"{base_path}/{db_name}_test?{params}"
    else:
        db_name = prod_url.rsplit("/", 1)[1]
        base_path = prod_url.rsplit("/", 1)[0]
        TEST_DATABASE_URL = f"{base_path}/{db_name}_test"

    print("\n⚠️  WARNING: TEST_DATABASE_URL not set in environment")
    print(f"Using auto-generated test database: {TEST_DATABASE_URL}")
    print("Set TEST_DATABASE_URL in .env to avoid this warning\n")

# Additional safety: ensure we're not using production database
if settings.database_url == TEST_DATABASE_URL:
    print("\n❌ CRITICAL ERROR: Test database URL is same as production database!")
    print("This would DROP all production data during tests.")
    print("Please set TEST_DATABASE_URL to a separate test database in .env")
    sys.exit(1)

# Ensure we're using asyncpg driver for async operations
if not TEST_DATABASE_URL.startswith("postgresql+asyncpg://"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create test engine with appropriate settings for testing
# Use NullPool to avoid event loop issues with remote databases
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    poolclass=NullPool,  # Disable connection pooling for tests
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)
        from sqlalchemy import text

        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "postgis"'))

        # Add geo column to pharmacy_locations (requires PostGIS)
        await conn.execute(
            text(
                """
            ALTER TABLE pharmacy_locations
            ADD COLUMN IF NOT EXISTS geo GEOGRAPHY(Point, 4326)
        """
            )
        )

        # Create spatial index
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_pharmacy_geo
            ON pharmacy_locations
            USING GIST (geo)
        """
            )
        )

    # Create session
    async with TestSessionLocal() as session:
        yield session

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_appointment_data() -> dict:
    """Sample appointment data for testing."""
    from datetime import datetime, timedelta

    return {
        "doctor_name": "Dr. John Doe",
        "clinic_name": "Health Clinic",
        "appointment_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "appointment_end_at": (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat(),
        "reason": "Regular checkup",
        "contact_phone": "+1234567890",
        "notes": "First time patient",
    }


@pytest.fixture
async def test_user(db_session):
    """Create a test user in the database."""
    from uuid import uuid4

    from sqlalchemy import insert

    from app.models.users import users

    # Generate a UUID for test user
    user_id = uuid4()
    user_data = {
        "id": user_id,
        "firebase_uid": f"test_firebase_uid_{user_id}",
        "email": "test@example.com",
        "email_verified": True,
        "auth_provider": "google",
        "full_name": "Test User",
        "phone": "+1234567890",
        "role": "patient",
        "is_active": True,
        "is_onboarded": True,
    }

    # Insert user
    await db_session.execute(insert(users).values(**user_data))
    await db_session.commit()

    # Return user data for test use
    return {
        "id": user_id,
        "firebase_uid": user_data["firebase_uid"],
        "email": user_data["email"],
        "full_name": user_data["full_name"],
        "phone": user_data["phone"],
        "role": user_data["role"],
        "is_active": user_data["is_active"],
    }


@pytest.fixture
def auth_headers(test_user) -> dict:
    """Create authentication headers for testing protected endpoints."""

    token_data = {
        "sub": str(test_user["id"]),  # Use the UUID as string
        "email": test_user["email"],
    }
    token = create_access_token(data=token_data, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}
