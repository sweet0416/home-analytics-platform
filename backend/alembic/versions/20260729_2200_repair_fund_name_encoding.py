"""Repair incorrectly decoded UTF-8 fund names.

Revision ID: 20260729_2200
Revises: 20260729_2130
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260729_2200"
down_revision: str | None = "20260729_2130"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MOJIBAKE_MARKERS = ("Ã", "Â", "æ", "ç", "è", "é")


def _repair_utf8_mojibake(value: str) -> str:
    if not any(marker in value for marker in _MOJIBAKE_MARKERS):
        return value
    try:
        repaired = value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return repaired if repaired != value else value


def upgrade() -> None:
    connection = op.get_bind()
    funds = sa.table(
        "funds",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )
    rows = connection.execute(sa.select(funds.c.id, funds.c.name)).mappings()
    for row in rows:
        repaired = _repair_utf8_mojibake(row["name"])
        if repaired != row["name"]:
            connection.execute(
                funds.update().where(funds.c.id == row["id"]).values(name=repaired)
            )


def downgrade() -> None:
    # Restoring corrupted display text would be destructive and has no value.
    pass
