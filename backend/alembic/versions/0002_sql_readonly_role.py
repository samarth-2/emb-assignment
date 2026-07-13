"""create least-privilege sql_readonly role (SELECT on orders only)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-13

"""
from collections.abc import Sequence

from alembic import op

from app.config import get_settings

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    password = get_settings().sql_readonly_password
    # Password comes from trusted app settings (not user input), so inline formatting is safe here;
    # CREATE ROLE does not support bind parameters.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sql_readonly') THEN
                CREATE ROLE sql_readonly WITH LOGIN PASSWORD '{password}';
            ELSE
                ALTER ROLE sql_readonly WITH LOGIN PASSWORD '{password}';
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO sql_readonly', current_database());
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO sql_readonly")
    op.execute("GRANT SELECT ON orders TO sql_readonly")


def downgrade() -> None:
    op.execute("REVOKE SELECT ON orders FROM sql_readonly")
    op.execute("REVOKE USAGE ON SCHEMA public FROM sql_readonly")
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM sql_readonly', current_database());
        END
        $$;
        """
    )
    op.execute("DROP ROLE IF EXISTS sql_readonly")
