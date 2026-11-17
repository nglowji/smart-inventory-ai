"""Revocable sessions and durable administrative audit events."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("auth_version", sa.Integer(), server_default="0", nullable=False)
    )
    op.create_check_constraint(
        op.f("ck_users_auth_version_nonnegative"), "users", "auth_version >= 0"
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column(
            "metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_audit_logs_actor_id_users")
        ),
    )
    op.create_index("ix_audit_created_id", "audit_logs", ["created_at", "id"])
    op.create_index("ix_audit_event_created", "audit_logs", ["event_type", "created_at"])


def downgrade():
    op.drop_index("ix_audit_event_created", table_name="audit_logs")
    op.drop_index("ix_audit_created_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_constraint(op.f("ck_users_auth_version_nonnegative"), "users", type_="check")
    op.drop_column("users", "auth_version")
