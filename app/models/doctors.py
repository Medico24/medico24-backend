"""Doctor model definition using SQLAlchemy Core."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

doctors = Table(
    "doctors",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    ),
    # Professional credentials
    Column("license_number", String(100), unique=True, index=True),
    Column("specialization", String(200), index=True),
    Column("sub_specialization", String(200)),
    Column("qualification", Text),
    Column("experience_years", Integer),
    # Practice information
    Column("consultation_fee", Numeric(10, 2)),
    Column("clinic_name", Text),
    Column("clinic_address", Text),
    Column("clinic_city", String(100)),
    Column("clinic_phone", String(20)),
    # Professional details
    Column("bio", Text),
    Column("languages_spoken", JSON),
    Column("medical_council_registration", String(100)),
    # Verification and ratings
    Column("is_verified", Boolean, nullable=False, server_default=text("false"), index=True),
    Column("verification_documents", JSON),
    Column("verified_at", DateTime(timezone=True)),
    Column("verified_by", UUID(as_uuid=True)),
    Column("rating", Numeric(3, 2)),
    Column("rating_count", Integer, nullable=False, server_default=text("0")),
    Column("total_consultations", Integer, nullable=False, server_default=text("0")),
    # Availability
    Column("available_days", JSON),
    Column("available_time_slots", JSON),
    Column("consultation_duration_minutes", Integer, server_default=text("30")),
    # Metadata
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
)
