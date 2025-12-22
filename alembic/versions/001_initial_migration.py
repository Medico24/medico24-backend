"""Initial migration - create appointments table.

Revision ID: 001
Revises:
Create Date: 2025-12-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Enable pgcrypto extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # Create appointments table
    op.create_table(
        "appointments",
        sa.Column(
            "id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("patient_id", postgresql.UUID(), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(), nullable=True),
        sa.Column("clinic_id", postgresql.UUID(), nullable=True),
        sa.Column("clinic_name", sa.Text(), nullable=True),
        sa.Column("doctor_name", sa.Text(), nullable=False),
        sa.Column("appointment_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("appointment_end_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("contact_phone", sa.VARCHAR(length=20), nullable=False),
        sa.Column("status", sa.Text(), server_default="scheduled", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), server_default="patient_app", nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("cancelled_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'rescheduled', 'cancelled', 'completed', 'no_show')",
            name="appointments_status_check",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"])
    op.create_index("ix_appointments_clinic_id", "appointments", ["clinic_id"])
    op.create_index("ix_appointments_status", "appointments", ["status"])
    op.create_index("ix_appointments_appointment_at", "appointments", ["appointment_at"])
    op.create_index("ix_appointments_deleted_at", "appointments", ["deleted_at"])


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes
    op.drop_index("ix_appointments_deleted_at", table_name="appointments")
    op.drop_index("ix_appointments_appointment_at", table_name="appointments")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_clinic_id", table_name="appointments")
    op.drop_index("ix_appointments_doctor_id", table_name="appointments")
    op.drop_index("ix_appointments_patient_id", table_name="appointments")

    # Drop table
    op.drop_table("appointments")
