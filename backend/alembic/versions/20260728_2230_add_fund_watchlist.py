"""add fund watchlist

Revision ID: 20260728_2230
Revises: 20260728_2100
Create Date: 2026-07-28 22:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_2230"
down_revision: str | None = "20260728_2100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fund_watchlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("watch_reason", sa.String(length=256), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("target_position", sa.String(length=64), nullable=False),
        sa.Column("tags", sa.String(length=256), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fund_watchlist_items_fund_id", "fund_watchlist_items", ["fund_id"])
    op.create_index(
        "ix_fund_watchlist_priority_created",
        "fund_watchlist_items",
        ["priority", "created_at"],
    )
    op.create_index(
        "ix_fund_watchlist_status_created",
        "fund_watchlist_items",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_fund_watchlist_status_created", table_name="fund_watchlist_items")
    op.drop_index("ix_fund_watchlist_priority_created", table_name="fund_watchlist_items")
    op.drop_index("ix_fund_watchlist_items_fund_id", table_name="fund_watchlist_items")
    op.drop_table("fund_watchlist_items")
