"""add AI usage metadata to fund summary archives

Revision ID: 20260808_0021
Revises: 20260808_0020
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0021"
down_revision: str | None = "20260808_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    if not sa.inspect(connection).has_table("fund_daily_ai_summaries"):
        return
    columns = {
        column["name"]
        for column in sa.inspect(connection).get_columns("fund_daily_ai_summaries")
    }
    additions = (
        ("model_name", sa.String(length=128), ""),
        ("prompt_version", sa.String(length=64), "fund-daily-prompt.v1"),
        ("input_tokens", sa.Integer(), None),
        ("output_tokens", sa.Integer(), None),
        ("cost", sa.Numeric(18, 8), None),
    )
    for name, column_type, default in additions:
        if name in columns:
            continue
        op.add_column(
            "fund_daily_ai_summaries",
            sa.Column(
                name,
                column_type,
                nullable=default is None,
                server_default=sa.text(f"'{default}'") if default is not None else None,
            ),
        )


def downgrade() -> None:
    connection = op.get_bind()
    if not sa.inspect(connection).has_table("fund_daily_ai_summaries"):
        return
    columns = {
        column["name"]
        for column in sa.inspect(connection).get_columns("fund_daily_ai_summaries")
    }
    for name in ("cost", "output_tokens", "input_tokens", "prompt_version", "model_name"):
        if name in columns:
            op.drop_column("fund_daily_ai_summaries", name)
