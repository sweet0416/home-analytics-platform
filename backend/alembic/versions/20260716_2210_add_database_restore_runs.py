"""add database restore runs

Revision ID: 20260716_2210
Revises: 20260716_2145
Create Date: 2026-07-16 22:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260716_2210"
down_revision: str | None = "20260716_2145"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "database_restore_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_file_name", sa.String(length=255), nullable=False),
        sa.Column("safety_backup_file_name", sa.String(length=255), nullable=False),
        sa.Column("confirmation", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_database_restore_runs_created_at",
        "database_restore_runs",
        ["created_at"],
    )
    op.create_index(
        "ix_database_restore_runs_source_file_name",
        "database_restore_runs",
        ["source_file_name"],
    )
    op.create_index(
        "ix_database_restore_runs_status",
        "database_restore_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_database_restore_runs_status", table_name="database_restore_runs")
    op.drop_index("ix_database_restore_runs_source_file_name", table_name="database_restore_runs")
    op.drop_index("ix_database_restore_runs_created_at", table_name="database_restore_runs")
    op.drop_table("database_restore_runs")
