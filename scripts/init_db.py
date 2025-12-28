"""Script to initialize the database."""

import asyncio

from app.database import engine
from app.models.appointments import metadata


async def init_db() -> None:
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        # Enable pgcrypto extension
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

        # Create all tables
        await conn.run_sync(metadata.create_all)

        print("✓ Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
