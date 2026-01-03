"""Add triggers for automatic role table management

Revision ID: 008
Revises: 007
Create Date: 2026-01-03 15:18:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add database triggers for automatic role table management."""

    # ===================================================================
    # TRIGGER FUNCTION: Create role record when user is inserted
    # ===================================================================
    op.execute(
        """
        CREATE OR REPLACE FUNCTION create_user_role_record()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Create role-specific record based on user's role
            IF NEW.role = 'patient' THEN
                INSERT INTO patients (user_id) VALUES (NEW.id);
            ELSIF NEW.role = 'doctor' THEN
                INSERT INTO doctors (user_id) VALUES (NEW.id);
            ELSIF NEW.role = 'admin' THEN
                INSERT INTO admins (user_id) VALUES (NEW.id);
            ELSIF NEW.role = 'pharmacy' THEN
                -- For pharmacy, we need pharmacy_id which will be set by application
                -- Create record with NULL pharmacy_id for now
                INSERT INTO pharmacy_staff (user_id, pharmacy_id) VALUES (NEW.id, NULL);
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Create trigger on INSERT
    op.execute(
        """
        CREATE TRIGGER trigger_create_user_role
        AFTER INSERT ON users
        FOR EACH ROW
        EXECUTE FUNCTION create_user_role_record();
    """
    )

    # ===================================================================
    # TRIGGER FUNCTION: Handle role changes when user is updated
    # ===================================================================
    op.execute(
        """
        CREATE OR REPLACE FUNCTION handle_user_role_change()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Only proceed if role has actually changed
            IF OLD.role IS DISTINCT FROM NEW.role THEN
                -- Delete from old role table
                IF OLD.role = 'patient' THEN
                    DELETE FROM patients WHERE user_id = OLD.id;
                ELSIF OLD.role = 'doctor' THEN
                    DELETE FROM doctors WHERE user_id = OLD.id;
                ELSIF OLD.role = 'pharmacy' THEN
                    DELETE FROM pharmacy_staff WHERE user_id = OLD.id;
                ELSIF OLD.role = 'admin' THEN
                    DELETE FROM admins WHERE user_id = OLD.id;
                END IF;

                -- Create record in new role table
                IF NEW.role = 'patient' THEN
                    INSERT INTO patients (user_id) VALUES (NEW.id);
                ELSIF NEW.role = 'doctor' THEN
                    INSERT INTO doctors (user_id) VALUES (NEW.id);
                ELSIF NEW.role = 'admin' THEN
                    INSERT INTO admins (user_id) VALUES (NEW.id);
                ELSIF NEW.role = 'pharmacy' THEN
                    -- For pharmacy, pharmacy_id should be set by application before role change
                    INSERT INTO pharmacy_staff (user_id, pharmacy_id) VALUES (NEW.id, NULL);
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Create trigger on UPDATE
    op.execute(
        """
        CREATE TRIGGER trigger_handle_role_change
        AFTER UPDATE OF role ON users
        FOR EACH ROW
        EXECUTE FUNCTION handle_user_role_change();
    """
    )


def downgrade() -> None:
    """Remove database triggers."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_handle_role_change ON users;")
    op.execute("DROP TRIGGER IF EXISTS trigger_create_user_role ON users;")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS handle_user_role_change();")
    op.execute("DROP FUNCTION IF EXISTS create_user_role_record();")
