"""Update doctors table - remove clinic fields and availability

Revision ID: 011_update_doctors_remove_clinic_fields
Revises: 010_create_doctor_clinics_table
Create Date: 2026-02-07

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove clinic-specific fields and availability from doctors table."""
    # Remove clinic-related columns (now in clinics table)
    op.drop_column("doctors", "clinic_name")
    op.drop_column("doctors", "clinic_address")
    op.drop_column("doctors", "clinic_city")
    op.drop_column("doctors", "clinic_phone")

    # Remove availability columns (now in doctor_clinics junction table)
    op.drop_column("doctors", "available_days")
    op.drop_column("doctors", "available_time_slots")


def downgrade() -> None:
    """Re-add clinic-specific fields and availability to doctors table."""
    # Re-add availability columns
    op.add_column("doctors", sa.Column("available_time_slots", sa.JSON(), nullable=True))
    op.add_column("doctors", sa.Column("available_days", sa.JSON(), nullable=True))

    # Re-add clinic-related columns
    op.add_column("doctors", sa.Column("clinic_phone", sa.String(length=20), nullable=True))
    op.add_column("doctors", sa.Column("clinic_city", sa.String(length=100), nullable=True))
    op.add_column("doctors", sa.Column("clinic_address", sa.Text(), nullable=True))
    op.add_column("doctors", sa.Column("clinic_name", sa.Text(), nullable=True))
