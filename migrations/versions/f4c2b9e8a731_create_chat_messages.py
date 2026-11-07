"""create private study chat messages

Revision ID: f4c2b9e8a731
Revises: d8a1b2c3e4f5
Create Date: 2026-11-07 12:06:14.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4c2b9e8a731"
down_revision = "d8a1b2c3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create persisted topic and upload chat messages with cascade cleanup."""
    op.create_table(
        "chat_message",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("upload_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name=op.f("ck_chat_message_role"),
        ),
        sa.CheckConstraint(
            "(topic_id IS NOT NULL AND upload_id IS NULL) OR "
            "(topic_id IS NULL AND upload_id IS NOT NULL)",
            name=op.f("ck_chat_message_single_context"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_chat_message_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_chat_message_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["upload_id"],
            ["uploads.id"],
            name=op.f("fk_chat_message_upload_id_uploads"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_message")),
    )
    op.create_index(
        op.f("ix_chat_message_user_topic_created"),
        "chat_message",
        ["user_id", "topic_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chat_message_user_upload_created"),
        "chat_message",
        ["user_id", "upload_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chat_message_user_role_created"),
        "chat_message",
        ["user_id", "role", "created_at"],
        unique=False,
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE chat_message ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Drop persisted chat messages and their indexes."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE chat_message DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_chat_message_user_role_created"), table_name="chat_message")
    op.drop_index(
        op.f("ix_chat_message_user_upload_created"),
        table_name="chat_message",
    )
    op.drop_index(op.f("ix_chat_message_user_topic_created"), table_name="chat_message")
    op.drop_table("chat_message")
