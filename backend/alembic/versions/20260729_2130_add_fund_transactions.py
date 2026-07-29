"""add fund transactions

Revision ID: 20260729_2130
Revises: 20260728_2300
Create Date: 2026-07-29 21:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_2130"
down_revision: str | None = "20260728_2300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fund_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("account_name", sa.String(length=64), nullable=False),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("shares", sa.Numeric(18, 4), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("fee", sa.Numeric(18, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fund_transactions_fund_id", "fund_transactions", ["fund_id"])
    op.create_index(
        "ix_fund_transactions_fund_date",
        "fund_transactions",
        ["fund_id", "trade_date"],
    )
    op.create_index(
        "ix_fund_transactions_account_date",
        "fund_transactions",
        ["account_name", "trade_date"],
    )
    op.create_index(
        "ix_fund_transactions_type_date",
        "fund_transactions",
        ["transaction_type", "trade_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_fund_transactions_type_date", table_name="fund_transactions")
    op.drop_index("ix_fund_transactions_account_date", table_name="fund_transactions")
    op.drop_index("ix_fund_transactions_fund_date", table_name="fund_transactions")
    op.drop_index("ix_fund_transactions_fund_id", table_name="fund_transactions")
    op.drop_table("fund_transactions")
