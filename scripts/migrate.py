"""Script to run database migrations."""

import sys

from alembic import command
from alembic.config import Config


def run_migrations() -> None:
    """Run database migrations to latest version."""
    alembic_cfg = Config("alembic.ini")

    try:
        print("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        print("✓ Migrations completed successfully!")
    except Exception as e:
        print(f"✗ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)


def create_migration(message: str) -> None:
    """Create a new migration."""
    alembic_cfg = Config("alembic.ini")

    try:
        print(f"Creating migration: {message}")
        command.revision(alembic_cfg, message=message, autogenerate=True)
        print("✓ Migration created successfully!")
    except Exception as e:
        print(f"✗ Migration creation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "create" and len(sys.argv) > 2:
            create_migration(" ".join(sys.argv[2:]))
        else:
            print("Usage: python scripts/migrate.py [create <message>]")
    else:
        run_migrations()
