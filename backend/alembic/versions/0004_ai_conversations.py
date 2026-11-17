"""Private conversations and retry-safe assistant turns."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_audit_actor_event_created", "audit_logs", ["actor_id", "event_type", "created_at"]
    )
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("pending_request_id", sa.Uuid(), nullable=True),
        sa.Column("pending_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_conversations")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_ai_conversations_user_id_users")
        ),
    )
    op.create_index(
        "ix_ai_conversations_owner_updated", "ai_conversations", ["user_id", "updated_at", "id"]
    )
    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("client_request_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "sources", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column(
            "tool_calls", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_messages")),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["ai_conversations.id"],
            name=op.f("fk_ai_messages_conversation_id_ai_conversations"),
        ),
        sa.CheckConstraint("role IN ('USER','ASSISTANT')", name=op.f("ck_ai_messages_role")),
        sa.UniqueConstraint(
            "conversation_id", "client_request_id", "role", name="uq_ai_message_turn"
        ),
    )
    op.create_index(
        "ix_ai_messages_conversation_created",
        "ai_messages",
        ["conversation_id", "created_at", "id"],
    )


def downgrade():
    op.drop_index("ix_audit_actor_event_created", table_name="audit_logs")
    op.drop_index("ix_ai_messages_conversation_created", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_conversations_owner_updated", table_name="ai_conversations")
    op.drop_table("ai_conversations")
