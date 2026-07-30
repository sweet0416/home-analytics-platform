"""add fund nav sync runs

Revision ID: 20260730_1930
Revises: 20260729_2200
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260730_1930"
down_revision: str | None = "20260729_2200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("fund_nav_sync_runs"):
        return

    op.create_table(
        "fund_nav_sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("succeeded", sa.Integer(), nullable=False),
        sa.Column("failed", sa.Integer(), nullable=False),
        sa.Column("updated", sa.Integer(), nullable=False),
        sa.Column("skipped", sa.Boolean(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fund_nav_sync_runs_finished",
        "fund_nav_sync_runs",
        ["finished_at"],
        unique=False,
    )
    op.create_index(
        "ix_fund_nav_sync_runs_status_finished",
        "fund_nav_sync_runs",
        ["status", "finished_at"],
        unique=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    if not sa.inspect(connection).has_table("fund_nav_sync_runs"):
        return

    op.drop_index(
        "ix_fund_nav_sync_runs_status_finished",
        table_name="fund_nav_sync_runs",
    )
    op.drop_index(
        "ix_fund_nav_sync_runs_finished",
        table_name="fund_nav_sync_runs",
    )
    op.drop_table("fund_nav_sync_runs")
