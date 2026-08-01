"""add fund position target weight

Revision ID: 20260801_2300
Revises: 20260731_2200
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_2300"
down_revision: str | None = "20260731_2200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(connection).get_columns("fund_positions")
    }
    if "target_weight" in columns:
        return
    op.add_column(
        "fund_positions",
        sa.Column("target_weight", sa.Numeric(12, 8), nullable=True),
    )


def downgrade() -> None:
    connection = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(connection).get_columns("fund_positions")
    }
    if "target_weight" not in columns:
        return
    with op.batch_alter_table("fund_positions") as batch_op:
        batch_op.drop_column("target_weight")
