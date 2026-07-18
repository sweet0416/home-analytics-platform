"""add lottery saved combinations

Revision ID: 20260718_1530
Revises: 20260716_2210
Create Date: 2026-07-18 15:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260718_1530"
down_revision: str | None = "20260716_2210"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lottery_saved_combinations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_code", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("front_numbers_json", sa.Text(), nullable=False),
        sa.Column("back_numbers_json", sa.Text(), nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_code",
            "front_numbers_json",
            "back_numbers_json",
            name="uq_lottery_saved_combination_numbers",
        ),
    )
    op.create_index(
        "ix_lottery_saved_combinations_game_code",
        "lottery_saved_combinations",
        ["game_code"],
    )
    op.create_index(
        "ix_lottery_saved_combinations_game_created",
        "lottery_saved_combinations",
        ["game_code", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lottery_saved_combinations_game_created",
        table_name="lottery_saved_combinations",
    )
    op.drop_index(
        "ix_lottery_saved_combinations_game_code",
        table_name="lottery_saved_combinations",
    )
    op.drop_table("lottery_saved_combinations")
