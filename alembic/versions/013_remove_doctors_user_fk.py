"""Remove foreign key constraint from doctors.user_id

Revision ID: 013
Revises: 012
Create Date: 2026-02-15

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove foreign key constraint from doctors.user_id column."""
    # Drop the foreign key constraint
    op.drop_constraint("doctors_user_id_fkey", "doctors", type_="foreignkey")


def downgrade() -> None:
    """Re-add foreign key constraint to doctors.user_id column."""
    # Re-add the foreign key constraint
    op.create_foreign_key(
        "doctors_user_id_fkey",
        "doctors",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
