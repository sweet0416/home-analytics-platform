"""add fund automatic AI summary execution ledger

Revision ID: 20260808_0020
Revises: 20260808_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "20260808_0020"
down_revision: str | None = "20260808_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("fund_ai_automation_runs"):
        return
    op.create_table(
        "fund_ai_automation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_key", sa.String(length=64), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("latest_nav_date", sa.Date(), nullable=True),
        sa.Column("nav_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("summary_id", sa.Integer(), nullable=True),
        sa.Column("summary_version", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Numeric(18, 8), nullable=True),
        sa.Column("ai_status", sa.String(length=32), nullable=False),
        sa.Column("push_status", sa.String(length=32), nullable=False),
        sa.Column("ai_error_message", sa.Text(), nullable=False),
        sa.Column("push_error_message", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["summary_id"],
            ["fund_daily_ai_summaries.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fund_ai_automation_runs_scope_date",
        "fund_ai_automation_runs",
        ["scope_key", "report_date"],
        unique=True,
    )
    op.create_index(
        "ix_fund_ai_automation_runs_report_date",
        "fund_ai_automation_runs",
        ["report_date"],
    )
    op.create_index(
        "ix_fund_ai_automation_runs_ai_status",
        "fund_ai_automation_runs",
        ["ai_status"],
    )
    op.create_index(
        "ix_fund_ai_automation_runs_push_status",
        "fund_ai_automation_runs",
        ["push_status"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("fund_ai_automation_runs"):
        for index_name in (
            "ix_fund_ai_automation_runs_push_status",
            "ix_fund_ai_automation_runs_ai_status",
            "ix_fund_ai_automation_runs_report_date",
            "ix_fund_ai_automation_runs_scope_date",
        ):
            op.drop_index(index_name, table_name="fund_ai_automation_runs")
        op.drop_table("fund_ai_automation_runs")
