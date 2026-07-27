"""add lottery random ticket runs

Revision ID: 20260727_1100
Revises: 20260723_0900
Create Date: 2026-07-27 11:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_1100"
down_revision: str | None = "20260723_0900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lottery_random_ticket_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_code", sa.String(length=32), nullable=False),
        sa.Column("target_issue_no", sa.String(length=32), nullable=False),
        sa.Column("latest_issue_no", sa.String(length=32), nullable=False),
        sa.Column("stage_code", sa.String(length=64), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("requested_sets", sa.Integer(), nullable=False),
        sa.Column("sample_weight", sa.Numeric(8, 2), nullable=False),
        sa.Column("input_combinations_json", sa.Text(), nullable=False),
        sa.Column("sample_summary_json", sa.Text(), nullable=False),
        sa.Column("recommendations_json", sa.Text(), nullable=False),
        sa.Column("methodology_json", sa.Text(), nullable=False),
        sa.Column("notes_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lottery_random_ticket_runs_game_code",
        "lottery_random_ticket_runs",
        ["game_code"],
    )
    op.create_index(
        "ix_lottery_random_ticket_runs_target_issue_no",
        "lottery_random_ticket_runs",
        ["target_issue_no"],
    )
    op.create_index(
        "ix_lottery_random_ticket_runs_game_created",
        "lottery_random_ticket_runs",
        ["game_code", "created_at"],
    )
    op.create_index(
        "ix_lottery_random_ticket_runs_game_target",
        "lottery_random_ticket_runs",
        ["game_code", "target_issue_no"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lottery_random_ticket_runs_game_target",
        table_name="lottery_random_ticket_runs",
    )
    op.drop_index(
        "ix_lottery_random_ticket_runs_game_created",
        table_name="lottery_random_ticket_runs",
    )
    op.drop_index(
        "ix_lottery_random_ticket_runs_target_issue_no",
        table_name="lottery_random_ticket_runs",
    )
    op.drop_index(
        "ix_lottery_random_ticket_runs_game_code",
        table_name="lottery_random_ticket_runs",
    )
    op.drop_table("lottery_random_ticket_runs")
