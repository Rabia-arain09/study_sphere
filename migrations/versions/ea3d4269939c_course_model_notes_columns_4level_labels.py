"""course_model_notes_columns_4level_labels

Revision ID: ea3d4269939c
Revises: 856dc8c30709
Create Date: 2026-10-30 11:13:45.117001

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea3d4269939c'
down_revision = '856dc8c30709'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create courses table
    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=100), nullable=False),
        sa.Column('credit_hours', sa.Integer(), nullable=False),
        sa.Column('contact_hours', sa.String(length=20), nullable=False),
        sa.Column('is_elective', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_courses')),
        sa.UniqueConstraint('code', name=op.f('uq_courses_code')),
        sa.UniqueConstraint('title', name=op.f('uq_courses_title')),
    )
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_courses_code'), ['code'], unique=False)
        batch_op.create_index(batch_op.f('ix_courses_title'), ['title'], unique=False)
        batch_op.create_index(batch_op.f('ix_courses_semester'), ['semester'], unique=False)

    # 2. Create course_prerequisites table
    op.create_table(
        'course_prerequisites',
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('prerequisite_course_id', sa.Integer(), nullable=False),
        sa.CheckConstraint('course_id != prerequisite_course_id', name=op.f('ck_course_prerequisites_check_no_self_course_prerequisite')),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_course_prerequisites_course_id_courses'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prerequisite_course_id'], ['courses.id'], name=op.f('fk_course_prerequisites_prerequisite_course_id_courses'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('course_id', 'prerequisite_course_id', name=op.f('pk_course_prerequisites')),
        sa.UniqueConstraint('course_id', 'prerequisite_course_id', name='uq_course_prerequisites_course_prerequisite'),
    )

    # 3. Add course_id and note columns to topics
    with op.batch_alter_table('topics', schema=None) as batch_op:
        batch_op.add_column(sa.Column('course_id', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('week', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('content', sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                'content_source',
                sa.Enum('lecture', 'ai_generated', name='contentsource', native_enum=False, length=20),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column('content_reviewed', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.create_foreign_key(
            op.f('fk_topics_course_id_courses'),
            'courses',
            ['course_id'],
            ['id'],
            ondelete='CASCADE',
        )
        batch_op.create_index(batch_op.f('ix_topics_course_id'), ['course_id'], unique=False)

    # 4. Handle MasteryLabel enum replacement (Weak, Good, Better, Excellent)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE attempts ALTER COLUMN label DROP DEFAULT;")
        op.execute("ALTER TABLE attempts ALTER COLUMN label TYPE VARCHAR(30) USING label::text;")
        op.execute("DROP TYPE IF EXISTS masterylabel CASCADE;")
        op.execute("CREATE TYPE masterylabel AS ENUM ('Weak', 'Good', 'Better', 'Excellent');")
        op.execute("ALTER TABLE attempts ALTER COLUMN label TYPE masterylabel USING label::masterylabel;")
    else:
        with op.batch_alter_table('attempts', schema=None) as batch_op:
            batch_op.alter_column(
                'label',
                existing_type=sa.Enum('STRONG', 'NEEDS_REVISION', 'WEAK', name='masterylabel', native_enum=False, length=30),
                type_=sa.Enum('Weak', 'Good', 'Better', 'Excellent', name='masterylabel', native_enum=False, length=30),
                existing_nullable=True,
            )

    # 5. Enable Row Level Security on the new tables (PostgreSQL only)
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE courses ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE course_prerequisites ENABLE ROW LEVEL SECURITY;")


def downgrade():
    bind = op.get_bind()

    # 1. Disable Row Level Security on new tables (PostgreSQL only)
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE course_prerequisites DISABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE courses DISABLE ROW LEVEL SECURITY;")

    # 2. Revert MasteryLabel enum replacement
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE attempts ALTER COLUMN label DROP DEFAULT;")
        op.execute("ALTER TABLE attempts ALTER COLUMN label TYPE VARCHAR(30) USING label::text;")
        op.execute("DROP TYPE IF EXISTS masterylabel CASCADE;")
        op.execute("CREATE TYPE masterylabel AS ENUM ('STRONG', 'NEEDS_REVISION', 'WEAK');")
        op.execute("ALTER TABLE attempts ALTER COLUMN label TYPE masterylabel USING label::masterylabel;")
    else:
        with op.batch_alter_table('attempts', schema=None) as batch_op:
            batch_op.alter_column(
                'label',
                existing_type=sa.Enum('Weak', 'Good', 'Better', 'Excellent', name='masterylabel', native_enum=False, length=30),
                type_=sa.Enum('STRONG', 'NEEDS_REVISION', 'WEAK', name='masterylabel', native_enum=False, length=30),
                existing_nullable=True,
            )

    # 3. Drop columns and foreign key from topics
    with op.batch_alter_table('topics', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_topics_course_id'))
        batch_op.drop_constraint(op.f('fk_topics_course_id_courses'), type_='foreignkey')
        batch_op.drop_column('content_reviewed')
        batch_op.drop_column('content_source')
        batch_op.drop_column('content')
        batch_op.drop_column('week')
        batch_op.drop_column('course_id')

    # 4. Drop course_prerequisites table
    op.drop_table('course_prerequisites')

    # 5. Drop courses table
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_courses_semester'))
        batch_op.drop_index(batch_op.f('ix_courses_title'))
        batch_op.drop_index(batch_op.f('ix_courses_code'))
    op.drop_table('courses')
