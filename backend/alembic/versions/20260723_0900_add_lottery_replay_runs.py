"""add lottery replay runs

Revision ID: 20260723_0900
Revises: 20260719_1545
Create Date: 2026-07-23 09:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_0900"
down_revision: str | None = "20260719_1545"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lottery_replay_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_code", sa.String(length=32), nullable=False),
        sa.Column("target_issue_no", sa.String(length=32), nullable=False),
        sa.Column("target_draw_date", sa.Date(), nullable=False),
        sa.Column("cutoff_issue_no", sa.String(length=32), nullable=True),
        sa.Column("cutoff_draw_date", sa.Date(), nullable=True),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_params_json", sa.Text(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("baseline_simulations", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("warnings_json", sa.Text(), nullable=False),
        sa.Column("result_summary_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lottery_replay_runs_game_code", "lottery_replay_runs", ["game_code"])
    op.create_index(
        "ix_lottery_replay_runs_game_created",
        "lottery_replay_runs",
        ["game_code", "created_at"],
    )
    op.create_index(
        "ix_lottery_replay_runs_game_target",
        "lottery_replay_runs",
        ["game_code", "target_issue_no"],
    )
    op.create_index(
        "ix_lottery_replay_runs_status",
        "lottery_replay_runs",
        ["status"],
    )
    op.create_index(
        "ix_lottery_replay_runs_target_draw_date",
        "lottery_replay_runs",
        ["target_draw_date"],
    )
    op.create_index(
        "ix_lottery_replay_runs_target_issue_no",
        "lottery_replay_runs",
        ["target_issue_no"],
    )

    op.create_table(
        "lottery_replay_generated_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("replay_run_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("front_numbers_json", sa.Text(), nullable=False),
        sa.Column("back_numbers_json", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(12, 4), nullable=True),
        sa.Column("rationale_json", sa.Text(), nullable=False),
        sa.Column("front_match_count", sa.Integer(), nullable=False),
        sa.Column("back_match_count", sa.Integer(), nullable=False),
        sa.Column("prize_tier", sa.Integer(), nullable=True),
        sa.Column("baseline_percentile", sa.Numeric(8, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["replay_run_id"], ["lottery_replay_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lottery_replay_generated_sets_replay_run_id",
        "lottery_replay_generated_sets",
        ["replay_run_id"],
    )
    op.create_index(
        "ix_lottery_replay_generated_sets_run_rank",
        "lottery_replay_generated_sets",
        ["replay_run_id", "rank"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lottery_replay_generated_sets_run_rank",
        table_name="lottery_replay_generated_sets",
    )
    op.drop_index(
        "ix_lottery_replay_generated_sets_replay_run_id",
        table_name="lottery_replay_generated_sets",
    )
    op.drop_table("lottery_replay_generated_sets")
    op.drop_index("ix_lottery_replay_runs_target_issue_no", table_name="lottery_replay_runs")
    op.drop_index("ix_lottery_replay_runs_target_draw_date", table_name="lottery_replay_runs")
    op.drop_index("ix_lottery_replay_runs_status", table_name="lottery_replay_runs")
    op.drop_index("ix_lottery_replay_runs_game_target", table_name="lottery_replay_runs")
    op.drop_index("ix_lottery_replay_runs_game_created", table_name="lottery_replay_runs")
    op.drop_index("ix_lottery_replay_runs_game_code", table_name="lottery_replay_runs")
    op.drop_table("lottery_replay_runs")
