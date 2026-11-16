"""Protect movement before/after arithmetic at the database boundary."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_check_constraint(
        op.f("ck_stock_movements_balance_delta"),
        "stock_movements",
        "(movement_type IN ('IN','ADJUST_IN') AND stock_after = stock_before + quantity) "
        "OR (movement_type IN ('OUT','ADJUST_OUT') AND stock_after = stock_before - quantity)",
    )


def downgrade():
    op.drop_constraint(op.f("ck_stock_movements_balance_delta"), "stock_movements", type_="check")
