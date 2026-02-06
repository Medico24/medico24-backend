"""Create clinics table

Revision ID: 009_create_clinics_table
Revises: 008_add_role_table_triggers
Create Date: 2026-02-07

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create clinics table."""
    # Create clinics table
    op.create_table(
        "clinics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("contacts", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=11, scale=8), nullable=True),
        sa.Column("opening_hours", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("rating", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("rating_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'temporarily_closed', 'permanently_closed')",
            name="clinics_status_check",
        ),
    )

    # Create indexes
    op.create_index("idx_clinics_name", "clinics", ["name"])
    op.create_index("idx_clinics_slug", "clinics", ["slug"], unique=True)
    op.create_index("idx_clinics_status", "clinics", ["status"])
    op.create_index("idx_clinics_is_active", "clinics", ["is_active"])


def downgrade() -> None:
    """Drop clinics table."""
    op.drop_table("clinics")
