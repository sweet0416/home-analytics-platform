"""add fund daily report snapshots

Revision ID: 20260802_0030
Revises: 20260801_2300
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260802_0030"
down_revision: str | None = "20260801_2300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("fund_daily_report_snapshots"):
        return

    op.create_table(
        "fund_daily_report_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("quality_level", sa.String(length=32), nullable=False),
        sa.Column("position_count", sa.Integer(), nullable=False),
        sa.Column("fund_count", sa.Integer(), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("unrealized_profit", sa.Numeric(18, 2), nullable=True),
        sa.Column("unrealized_return_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("valuation_complete", sa.Boolean(), nullable=False),
        sa.Column("latest_nav_date", sa.Date(), nullable=True),
        sa.Column("nav_age_days", sa.Integer(), nullable=True),
        sa.Column("risk_fund_count", sa.Integer(), nullable=False),
        sa.Column("risk_covered_fund_count", sa.Integer(), nullable=False),
        sa.Column("risk_sample_count", sa.Integer(), nullable=False),
        sa.Column("top_holding_weight", sa.Numeric(12, 8), nullable=True),
        sa.Column("concentration_hhi", sa.Numeric(12, 8), nullable=True),
        sa.Column("target_configured_count", sa.Integer(), nullable=False),
        sa.Column("target_configuration_complete", sa.Boolean(), nullable=False),
        sa.Column("target_weight_total", sa.Numeric(12, 8), nullable=False),
        sa.Column("alert_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fund_daily_report_snapshots_report_date",
        "fund_daily_report_snapshots",
        ["report_date"],
        unique=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    if not sa.inspect(connection).has_table("fund_daily_report_snapshots"):
        return
    op.drop_index(
        "ix_fund_daily_report_snapshots_report_date",
        table_name="fund_daily_report_snapshots",
    )
    op.drop_table("fund_daily_report_snapshots")
