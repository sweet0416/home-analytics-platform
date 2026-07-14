"""add lottery sync runs

Revision ID: 20260714_2230
Revises:
Create Date: 2026-07-14 22:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_2230"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lottery_sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_code", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("sync_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("requested_page", sa.Integer(), nullable=True),
        sa.Column("requested_page_size", sa.Integer(), nullable=True),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("latest_issue_no", sa.String(length=32), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=512), nullable=True),
        sa.Column("raw_metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lottery_sync_runs_game_code", "lottery_sync_runs", ["game_code"])
    op.create_index("ix_lottery_sync_runs_status", "lottery_sync_runs", ["status"])
    op.create_index("ix_lottery_sync_runs_started_at", "lottery_sync_runs", ["started_at"])
    op.create_index(
        "ix_lottery_sync_runs_game_started",
        "lottery_sync_runs",
        ["game_code", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_lottery_sync_runs_game_started", table_name="lottery_sync_runs")
    op.drop_index("ix_lottery_sync_runs_started_at", table_name="lottery_sync_runs")
    op.drop_index("ix_lottery_sync_runs_status", table_name="lottery_sync_runs")
    op.drop_index("ix_lottery_sync_runs_game_code", table_name="lottery_sync_runs")
    op.drop_table("lottery_sync_runs")
