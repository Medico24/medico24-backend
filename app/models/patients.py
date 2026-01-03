"""Patient model definition using SQLAlchemy Core."""

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

patients = Table(
    "patients",
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
    # Personal health information
    Column("blood_group", String(10)),
    Column("date_of_birth", Date),
    Column("gender", String(20)),
    # Address information
    Column("address_line_1", Text),
    Column("address_line_2", Text),
    Column("city", String(100)),
    Column("state", String(100)),
    Column("country", String(100)),
    Column("pincode", String(20)),
    # Emergency contact
    Column("emergency_contact_name", Text),
    Column("emergency_contact_phone", String(20)),
    Column("emergency_contact_relation", String(50)),
    # Medical information (JSON for flexibility)
    Column("medical_history", JSON),
    Column("current_medications", JSON),
    Column("allergies", JSON),
    Column("chronic_conditions", JSON),
    # Insurance information
    Column("insurance_provider", Text),
    Column("insurance_policy_number", String(100)),
    # Metadata
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
)
