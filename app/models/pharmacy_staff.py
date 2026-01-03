"""Pharmacy staff model definition using SQLAlchemy Core."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

pharmacy_staff = Table(
    "pharmacy_staff",
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
    Column(
        "pharmacy_id",
        UUID(as_uuid=True),
        ForeignKey("pharmacies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    # Staff information
    Column("position", String(100)),  # owner, pharmacist, manager, staff
    Column("license_number", String(100)),
    Column("is_owner", Boolean, nullable=False, server_default=text("false"), index=True),
    Column("is_primary_contact", Boolean, nullable=False, server_default=text("false")),
    # Employment details
    Column("employment_type", String(50)),  # full-time, part-time, contract
    Column("date_joined", Date),
    Column("date_left", Date),
    # Permissions (JSON for flexible access control)
    Column("permissions", JSON),
    # Metadata
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
)
