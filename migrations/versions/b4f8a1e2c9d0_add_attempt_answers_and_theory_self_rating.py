"""add attempt_answers and theory self rating

Revision ID: b4f8a1e2c9d0
Revises: ea3d4269939c
Create Date: 2026-11-01 17:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4f8a1e2c9d0'
down_revision = 'ea3d4269939c'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create attempt_answers table
    op.create_table(
        'attempt_answers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('attempt_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('self_rating', sa.String(length=20), nullable=True),
        sa.CheckConstraint(
            "self_rating IS NULL OR self_rating IN ('got_it', 'partly', 'missed')",
            name='ck_attempt_answers_self_rating',
        ),
        sa.ForeignKeyConstraint(
            ['attempt_id'],
            ['attempts.id'],
            name=op.f('fk_attempt_answers_attempt_id_attempts'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['question_id'],
            ['questions.id'],
            name=op.f('fk_attempt_answers_question_id_questions'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_attempt_answers')),
        sa.UniqueConstraint('attempt_id', 'question_id', name='uq_attempt_answers_attempt_id_question_id'),
    )
    with op.batch_alter_table('attempt_answers', schema=None) as batch_op:
        batch_op.create_index('ix_attempt_answers_attempt_id', ['attempt_id'], unique=False)

    # 2. Enable Row Level Security on attempt_answers in PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE attempt_answers ENABLE ROW LEVEL SECURITY;")

    # 3. Ensure attempts.wrong_count is Float to support half-point theory grading
    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.alter_column(
            'wrong_count',
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.alter_column(
            'wrong_count',
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=False,
        )

    with op.batch_alter_table('attempt_answers', schema=None) as batch_op:
        batch_op.drop_index('ix_attempt_answers_attempt_id')

    op.drop_table('attempt_answers')
