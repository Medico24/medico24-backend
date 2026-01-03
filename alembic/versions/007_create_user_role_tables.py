"""Create user role tables (patients, doctors, pharmacy_staff, admins)

Revision ID: 007
Revises: 006
Create Date: 2026-01-03 12:00:00.000000

Industry-grade schema for role-based user management.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create role-specific tables for all user types."""

    # ===================================================================
    # PATIENTS TABLE - Medical records and health information
    # ===================================================================
    op.create_table(
        "patients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Personal health information
        sa.Column("blood_group", sa.String(10), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        # Address information
        sa.Column("address_line_1", sa.Text(), nullable=True),
        sa.Column("address_line_2", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("pincode", sa.String(20), nullable=True),
        # Emergency contact
        sa.Column("emergency_contact_name", sa.Text(), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(20), nullable=True),
        sa.Column("emergency_contact_relation", sa.String(50), nullable=True),
        # Medical information (JSON for flexibility)
        sa.Column("medical_history", postgresql.JSON(), nullable=True),
        sa.Column("current_medications", postgresql.JSON(), nullable=True),
        sa.Column("allergies", postgresql.JSON(), nullable=True),
        sa.Column("chronic_conditions", postgresql.JSON(), nullable=True),
        # Insurance information
        sa.Column("insurance_provider", sa.Text(), nullable=True),
        sa.Column("insurance_policy_number", sa.String(100), nullable=True),
        # Metadata
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

    op.create_index("ix_patients_user_id", "patients", ["user_id"], unique=True)

    # ===================================================================
    # DOCTORS TABLE - Medical professionals
    # ===================================================================
    op.create_table(
        "doctors",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Professional credentials
        sa.Column("license_number", sa.String(100), nullable=True, unique=True),
        sa.Column("specialization", sa.String(200), nullable=True),
        sa.Column("sub_specialization", sa.String(200), nullable=True),
        sa.Column("qualification", sa.Text(), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        # Practice information
        sa.Column("consultation_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("clinic_name", sa.Text(), nullable=True),
        sa.Column("clinic_address", sa.Text(), nullable=True),
        sa.Column("clinic_city", sa.String(100), nullable=True),
        sa.Column("clinic_phone", sa.String(20), nullable=True),
        # Professional details
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("languages_spoken", postgresql.JSON(), nullable=True),
        sa.Column("medical_council_registration", sa.String(100), nullable=True),
        # Verification and ratings
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verification_documents", postgresql.JSON(), nullable=True),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_consultations", sa.Integer(), nullable=False, server_default=sa.text("0")),
        # Availability (JSON for flexible scheduling)
        sa.Column("available_days", postgresql.JSON(), nullable=True),
        sa.Column("available_time_slots", postgresql.JSON(), nullable=True),
        sa.Column("consultation_duration_minutes", sa.Integer(), server_default=sa.text("30")),
        # Metadata
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

    op.create_index("ix_doctors_user_id", "doctors", ["user_id"], unique=True)
    op.create_index("ix_doctors_license_number", "doctors", ["license_number"], unique=True)
    op.create_index("ix_doctors_specialization", "doctors", ["specialization"])
    op.create_index("ix_doctors_is_verified", "doctors", ["is_verified"])

    # ===================================================================
    # PHARMACY_STAFF TABLE - Pharmacy employees/owners
    # ===================================================================
    op.create_table(
        "pharmacy_staff",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "pharmacy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pharmacies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Staff information
        sa.Column("position", sa.String(100), nullable=True),  # owner, pharmacist, manager, staff
        sa.Column("license_number", sa.String(100), nullable=True),
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "is_primary_contact", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        # Employment details
        sa.Column(
            "employment_type", sa.String(50), nullable=True
        ),  # full-time, part-time, contract
        sa.Column("date_joined", sa.Date(), nullable=True),
        sa.Column("date_left", sa.Date(), nullable=True),
        # Permissions (JSON for flexible access control)
        sa.Column("permissions", postgresql.JSON(), nullable=True),
        # Metadata
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

    op.create_index("ix_pharmacy_staff_user_id", "pharmacy_staff", ["user_id"], unique=True)
    op.create_index("ix_pharmacy_staff_pharmacy_id", "pharmacy_staff", ["pharmacy_id"])
    op.create_index("ix_pharmacy_staff_is_owner", "pharmacy_staff", ["is_owner"])

    # ===================================================================
    # ADMINS TABLE - System administrators
    # ===================================================================
    op.create_table(
        "admins",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Admin information
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column(
            "access_level", sa.String(50), nullable=False, server_default=sa.text("'standard'")
        ),
        sa.Column("job_title", sa.String(100), nullable=True),
        # Permissions (JSON for granular access control)
        sa.Column("permissions", postgresql.JSON(), nullable=True),
        sa.Column("allowed_modules", postgresql.JSON(), nullable=True),
        # Audit information
        sa.Column("last_login_ip", sa.String(45), nullable=True),  # IPv6 max length
        sa.Column("login_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        # Metadata
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

    op.create_index("ix_admins_user_id", "admins", ["user_id"], unique=True)
    op.create_index("ix_admins_access_level", "admins", ["access_level"])

    # ===================================================================
    # DATA MIGRATION - Create role records for existing users
    # ===================================================================

    # Migrate patients
    op.execute(
        """
        INSERT INTO patients (user_id)
        SELECT id FROM users WHERE role = 'patient'
        ON CONFLICT (user_id) DO NOTHING
    """
    )

    # Migrate doctors
    op.execute(
        """
        INSERT INTO doctors (user_id)
        SELECT id FROM users WHERE role = 'doctor'
        ON CONFLICT (user_id) DO NOTHING
    """
    )

    # Migrate admins
    op.execute(
        """
        INSERT INTO admins (user_id)
        SELECT id FROM users WHERE role = 'admin'
        ON CONFLICT (user_id) DO NOTHING
    """
    )

    # Migrate pharmacy staff
    # For pharmacy users, we need to handle the case where they might not have a pharmacy_id
    # We'll create records but leave pharmacy_id null for now (to be updated later)
    op.execute(
        """
        INSERT INTO pharmacy_staff (user_id, pharmacy_id)
        SELECT u.id, NULL
        FROM users u
        WHERE u.role = 'pharmacy'
        ON CONFLICT (user_id) DO NOTHING
    """
    )


def downgrade() -> None:
    """Drop all role-specific tables."""
    op.drop_index("ix_admins_access_level", table_name="admins")
    op.drop_index("ix_admins_user_id", table_name="admins")
    op.drop_table("admins")

    op.drop_index("ix_pharmacy_staff_is_owner", table_name="pharmacy_staff")
    op.drop_index("ix_pharmacy_staff_pharmacy_id", table_name="pharmacy_staff")
    op.drop_index("ix_pharmacy_staff_user_id", table_name="pharmacy_staff")
    op.drop_table("pharmacy_staff")

    op.drop_index("ix_doctors_is_verified", table_name="doctors")
    op.drop_index("ix_doctors_specialization", table_name="doctors")
    op.drop_index("ix_doctors_license_number", table_name="doctors")
    op.drop_index("ix_doctors_user_id", table_name="doctors")
    op.drop_table("doctors")

    op.drop_index("ix_patients_user_id", table_name="patients")
    op.drop_table("patients")
