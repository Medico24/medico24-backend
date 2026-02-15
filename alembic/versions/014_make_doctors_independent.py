"""Make doctors independent from users table

Revision ID: 014
Revises: 013
Create Date: 2026-02-15

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop user_id column and add personal information fields to doctors table."""
    # Add new personal information columns
    op.add_column("doctors", sa.Column("email", sa.Text(), nullable=True))
    op.add_column("doctors", sa.Column("full_name", sa.Text(), nullable=True))
    op.add_column("doctors", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column("doctors", sa.Column("profile_picture_url", sa.Text(), nullable=True))

    # Create indexes for new columns
    op.create_index("ix_doctors_email", "doctors", ["email"], unique=True)

    # Migrate data from users table to doctors table before dropping user_id
    op.execute(
        """
        UPDATE doctors
        SET
            email = users.email,
            full_name = users.full_name,
            phone = users.phone,
            profile_picture_url = users.photo_url
        FROM users
        WHERE doctors.user_id = users.id
    """
    )

    # Make email and full_name NOT NULL after data migration
    op.alter_column("doctors", "email", nullable=False)
    op.alter_column("doctors", "full_name", nullable=False)

    # Drop the user_id index and column
    op.drop_index("ix_doctors_user_id", table_name="doctors")
    op.drop_column("doctors", "user_id")


def downgrade() -> None:
    """Re-add user_id column and remove personal information fields."""
    # Re-add user_id column
    op.add_column(
        "doctors",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True, unique=True),
    )
    op.create_index("ix_doctors_user_id", "doctors", ["user_id"], unique=True)

    # Drop personal information fields
    op.drop_index("ix_doctors_email", table_name="doctors")
    op.drop_column("doctors", "profile_picture_url")
    op.drop_column("doctors", "phone")
    op.drop_column("doctors", "full_name")
    op.drop_column("doctors", "email")

    # Note: Cannot fully restore user_id mappings without additional data
    # This downgrade is lossy - consider backing up data before upgrade
