"""Safe conversational references; never store raw tool payloads as planner memory."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ai_messages",
        sa.Column(
            "planner_context",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("ai_messages", "planner_context")
