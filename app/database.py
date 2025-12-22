"""Database configuration and connection management."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Convert sync PostgreSQL URL to async
DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine with connection pooling
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    connect_args={
        "server_settings": {
            "application_name": settings.app_name,
        },
    },
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# For Alembic migrations (sync engine)
sync_engine: Engine = create_engine(
    settings.database_url,
    poolclass=pool.NullPool,
)


@event.listens_for(sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn: Any, connection_record: Any) -> None:
    """Set database connection parameters."""
    # This is for PostgreSQL-specific settings if needed


async def check_database_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
