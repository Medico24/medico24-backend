"""Admin model definition using SQLAlchemy Core."""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

admins = Table(
    "admins",
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
    # Admin information
    Column("department", String(100)),
    Column(
        "access_level", String(50), nullable=False, server_default=text("'standard'"), index=True
    ),
    Column("job_title", String(100)),
    # Permissions (JSON for granular access control)
    Column("permissions", JSON),
    Column("allowed_modules", JSON),
    # Audit information
    Column("last_login_ip", String(45)),  # IPv6 max length
    Column("login_count", Integer, nullable=False, server_default=text("0")),
    # Metadata
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
)
