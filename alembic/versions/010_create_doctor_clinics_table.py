"""Create doctor_clinics junction table

Revision ID: 010_create_doctor_clinics_table
Revises: 009_create_clinics_table
Create Date: 2026-02-07

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create doctor_clinics junction table."""
    # Create doctor_clinics table
    op.create_table(
        "doctor_clinics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "start_date",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consultation_fee", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("consultation_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("department", sa.String(length=200), nullable=True),
        sa.Column("designation", sa.String(length=200), nullable=True),
        sa.Column("available_days", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("available_time_slots", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "appointment_booking_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "total_appointments",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "completed_appointments",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("rating_at_clinic", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column(
            "rating_count_at_clinic",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinics.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'on_leave', 'temporarily_unavailable', 'inactive')",
            name="doctor_clinics_status_check",
        ),
    )

    # Create indexes
    op.create_index("idx_doctor_clinics_doctor_id", "doctor_clinics", ["doctor_id"])
    op.create_index("idx_doctor_clinics_clinic_id", "doctor_clinics", ["clinic_id"])
    op.create_index("idx_doctor_clinics_status", "doctor_clinics", ["status"])
    op.create_index("idx_doctor_clinics_is_primary", "doctor_clinics", ["is_primary"])
    op.create_index(
        "idx_doctor_clinics_doctor_status",
        "doctor_clinics",
        ["doctor_id", "status"],
    )
    op.create_index(
        "idx_doctor_clinics_clinic_status",
        "doctor_clinics",
        ["clinic_id", "status"],
    )
    op.create_index(
        "idx_doctor_clinics_active",
        "doctor_clinics",
        ["doctor_id", "clinic_id"],
        postgresql_where=sa.text("end_date IS NULL AND status = 'active'"),
    )

    # Create unique constraint for active associations
    op.execute(
        """
        CREATE UNIQUE INDEX uq_doctor_clinic_active
        ON doctor_clinics (doctor_id, clinic_id)
        WHERE end_date IS NULL;
        """
    )


def downgrade() -> None:
    """Drop doctor_clinics table."""
    op.drop_table("doctor_clinics")
