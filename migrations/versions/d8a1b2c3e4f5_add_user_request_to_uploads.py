"""add user_request column to uploads table

Revision ID: d8a1b2c3e4f5
Revises: c7f91a2b3d4e
Create Date: 2026-11-02 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8a1b2c3e4f5'
down_revision = 'c7f91a2b3d4e'
branch_labels = None
depends_on = None


def upgrade():
    """Add nullable user_request text column to uploads table."""
    with op.batch_alter_table('uploads', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_request', sa.Text(), nullable=True))


def downgrade():
    """Remove user_request column from uploads table."""
    with op.batch_alter_table('uploads', schema=None) as batch_op:
        batch_op.drop_column('user_request')
