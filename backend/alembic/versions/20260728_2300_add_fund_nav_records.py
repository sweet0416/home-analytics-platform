"""add fund nav records

Revision ID: 20260728_2300
Revises: 20260728_2230
Create Date: 2026-07-28 23:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_2300"
down_revision: str | None = "20260728_2230"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fund_nav_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fund_id", sa.Integer(), nullable=False),
        sa.Column("nav_date", sa.Date(), nullable=False),
        sa.Column("unit_nav", sa.Numeric(18, 4), nullable=False),
        sa.Column("accumulated_nav", sa.Numeric(18, 4), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fund_nav_records_fund_id", "fund_nav_records", ["fund_id"])
    op.create_index(
        "ix_fund_nav_records_fund_date",
        "fund_nav_records",
        ["fund_id", "nav_date"],
        unique=True,
    )
    op.create_index("ix_fund_nav_records_date", "fund_nav_records", ["nav_date"])


def downgrade() -> None:
    op.drop_index("ix_fund_nav_records_date", table_name="fund_nav_records")
    op.drop_index("ix_fund_nav_records_fund_date", table_name="fund_nav_records")
    op.drop_index("ix_fund_nav_records_fund_id", table_name="fund_nav_records")
    op.drop_table("fund_nav_records")
