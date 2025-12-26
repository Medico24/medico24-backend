"""Create pharmacy tables

Revision ID: 003
Revises: 002
Create Date: 2025-12-29 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pharmacy-related tables."""
    # Enable PostGIS extension for geographic data
    op.execute('CREATE EXTENSION IF NOT EXISTS "postgis"')

    # Create pharmacies table
    op.create_table(
        "pharmacies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "rating",
            sa.Numeric(precision=2, scale=1),
            nullable=True,
            server_default=sa.text("0.0"),
        ),
        sa.Column("rating_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column(
            "supports_delivery",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "supports_pickup",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Create indexes for pharmacies table
    op.create_index("idx_pharmacies_active", "pharmacies", ["is_active"])
    op.create_index("idx_pharmacies_verified", "pharmacies", ["is_verified"])

    # Create pharmacy_locations table
    op.create_table(
        "pharmacy_locations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("pharmacy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("address_line", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=False, server_default=sa.text("'India'")),
        sa.Column("pincode", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["pharmacy_id"],
            ["pharmacies.id"],
            name="fk_pharmacy_location",
            ondelete="CASCADE",
        ),
    )

    # Add geography column for spatial queries
    op.execute(
        """
        ALTER TABLE pharmacy_locations
        ADD COLUMN geo GEOGRAPHY(Point, 4326)
        """
    )

    # Update existing rows with geography data
    op.execute(
        """
        UPDATE pharmacy_locations
        SET geo = ST_MakePoint(longitude, latitude)
        """
    )

    # Create spatial index
    op.execute(
        """
        CREATE INDEX idx_pharmacy_geo
        ON pharmacy_locations
        USING GIST (geo)
        """
    )

    # Create index for pharmacy_id
    op.create_index("idx_locations_pharmacy", "pharmacy_locations", ["pharmacy_id"])

    # Create pharmacy_hours table
    op.create_table(
        "pharmacy_hours",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("pharmacy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("open_time", sa.Time(), nullable=False),
        sa.Column("close_time", sa.Time(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(
            ["pharmacy_id"],
            ["pharmacies.id"],
            name="fk_pharmacy_hours",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("pharmacy_id", "day_of_week", name="unique_day_per_pharmacy"),
    )


def downgrade() -> None:
    """Drop pharmacy-related tables."""
    op.drop_table("pharmacy_hours")
    op.drop_table("pharmacy_locations")
    op.drop_table("pharmacies")
    # Note: Not dropping PostGIS extension as it might be used by other tables
