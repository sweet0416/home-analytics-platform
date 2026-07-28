"""add fund holdings

Revision ID: 20260728_2100
Revises: 20260727_1100
Create Date: 2026-07-28 21:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_2100"
down_revision: str | None = "20260727_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "funds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("fund_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_funds_code", "funds", ["code"], unique=True)

    op.create_table(
        "fund_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("account_name", sa.String(length=64), nullable=False),
        sa.Column("shares", sa.Numeric(18, 4), nullable=False),
        sa.Column("cost_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_nav", sa.Numeric(18, 4), nullable=True),
        sa.Column("opened_at", sa.Date(), nullable=True),
        sa.Column("tags", sa.String(length=256), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fund_positions_fund_id", "fund_positions", ["fund_id"])
    op.create_index(
        "ix_fund_positions_fund_created",
        "fund_positions",
        ["fund_id", "created_at"],
    )
    op.create_index(
        "ix_fund_positions_account_created",
        "fund_positions",
        ["account_name", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fund_positions_account_created",
        table_name="fund_positions",
    )
    op.drop_index("ix_fund_positions_fund_created", table_name="fund_positions")
    op.drop_index("ix_fund_positions_fund_id", table_name="fund_positions")
    op.drop_table("fund_positions")
    op.drop_index("ix_funds_code", table_name="funds")
    op.drop_table("funds")
