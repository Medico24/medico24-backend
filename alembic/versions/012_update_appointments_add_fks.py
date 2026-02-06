"""Update appointments table - add foreign keys for new structure

Revision ID: 012_update_appointments_add_fks
Revises: 011_update_doctors_remove_clinic_fields
Create Date: 2026-02-07

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add foreign keys and doctor_clinic_id to appointments table."""
    # Add doctor_clinic_id column
    op.add_column(
        "appointments",
        sa.Column(
            "doctor_clinic_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # Clean up orphaned appointments (those without valid patient_id)
    op.execute(
        """
        DELETE FROM appointments
        WHERE patient_id NOT IN (SELECT id FROM patients);
        """
    )

    # Add foreign key constraints
    # Note: Using NOT VALID for existing data, then validating
    op.create_foreign_key(
        "fk_appointments_patient_id",
        "appointments",
        "patients",
        ["patient_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_appointments_doctor_id",
        "appointments",
        "doctors",
        ["doctor_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_appointments_clinic_id",
        "appointments",
        "clinics",
        ["clinic_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_appointments_doctor_clinic_id",
        "appointments",
        "doctor_clinics",
        ["doctor_clinic_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create indexes for better query performance
    op.create_index("idx_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("idx_appointments_doctor_id", "appointments", ["doctor_id"])
    # Note: clinic_id index already exists from migration 001


def downgrade() -> None:
    """Remove foreign keys and doctor_clinic_id from appointments table."""
    # Drop indexes
    op.drop_index("idx_appointments_doctor_id", table_name="appointments")
    op.drop_index("idx_appointments_patient_id", table_name="appointments")

    # Drop foreign keys
    op.drop_constraint("fk_appointments_doctor_clinic_id", "appointments", type_="foreignkey")
    op.drop_constraint("fk_appointments_clinic_id", "appointments", type_="foreignkey")
    op.drop_constraint("fk_appointments_doctor_id", "appointments", type_="foreignkey")
    op.drop_constraint("fk_appointments_patient_id", "appointments", type_="foreignkey")

    # Drop doctor_clinic_id column
    op.drop_column("appointments", "doctor_clinic_id")
