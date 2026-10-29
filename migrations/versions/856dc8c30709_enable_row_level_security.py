"""enable row level security

Revision ID: 856dc8c30709
Revises: fe0300e0055e
Create Date: 2026-10-29 14:18:38.842008

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "856dc8c30709"
down_revision = "fe0300e0055e"
branch_labels = None
depends_on = None

APPLICATION_TABLES: list[str] = [
    "users",
    "topics",
    "prerequisites",
    "resources",
    "questions",
    "attempts",
]


def upgrade() -> None:
    """Enable Row Level Security (RLS) on all application tables in PostgreSQL.

    Guarded by dialect check so this operation is a safe no-op on SQLite.
    Enabling RLS prevents unauthorized data exposure via Supabase's auto-generated
    PostgREST Public Data API, while allowing the direct connection database role
    (e.g., postgres) to operate unimpeded.
    """
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in APPLICATION_TABLES:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    """Disable Row Level Security (RLS) on all application tables in PostgreSQL.

    Guarded by dialect check so this operation is a safe no-op on SQLite.
    """
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in APPLICATION_TABLES:
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
