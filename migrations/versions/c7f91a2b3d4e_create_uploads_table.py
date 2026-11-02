"""create uploads table and enable row level security

Revision ID: c7f91a2b3d4e
Revises: b4f8a1e2c9d0
Create Date: 2026-11-02 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7f91a2b3d4e'
down_revision = 'b4f8a1e2c9d0'
branch_labels = None
depends_on = None


def upgrade():
    """Create uploads table with indices and enable RLS in PostgreSQL."""
    op.create_table(
        'uploads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_ref', sa.String(length=500), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=False),
        sa.Column('summary', sa.JSON(), nullable=False),
        sa.Column('simple_explanation', sa.Text(), nullable=False),
        sa.Column('key_terms', sa.JSON(), nullable=False),
        sa.Column('questions', sa.JSON(), nullable=False),
        sa.Column('attempts_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_score', sa.Float(), nullable=True),
        sa.Column('last_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name=op.f('fk_uploads_user_id_users'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_uploads')),
    )
    with op.batch_alter_table('uploads', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_uploads_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_uploads_content_hash'), ['content_hash'], unique=False)

    # Enable Row Level Security on uploads in PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;")


def downgrade():
    """Drop uploads table and disable RLS."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE uploads DISABLE ROW LEVEL SECURITY;")

    with op.batch_alter_table('uploads', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_uploads_content_hash'))
        batch_op.drop_index(batch_op.f('ix_uploads_user_id'))

    op.drop_table('uploads')
