"""add fund daily AI summary archives

Revision ID: 20260808_0010
Revises: 20260808_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0010"
down_revision: str | None = "20260808_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("fund_daily_ai_summaries"):
        return
    op.create_table(
        "fund_daily_ai_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("source_contract", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["fund_daily_report_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fund_daily_ai_summaries_snapshot_id",
        "fund_daily_ai_summaries",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_fund_daily_ai_summaries_snapshot_provider",
        "fund_daily_ai_summaries",
        ["snapshot_id", "provider"],
        unique=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("fund_daily_ai_summaries"):
        op.drop_index(
            "ix_fund_daily_ai_summaries_snapshot_provider",
            table_name="fund_daily_ai_summaries",
        )
        op.drop_index(
            "ix_fund_daily_ai_summaries_snapshot_id",
            table_name="fund_daily_ai_summaries",
        )
        op.drop_table("fund_daily_ai_summaries")
