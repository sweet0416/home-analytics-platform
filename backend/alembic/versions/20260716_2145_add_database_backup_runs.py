"""add database backup runs

Revision ID: 20260716_2145
Revises: 20260714_2230
Create Date: 2026-07-16 21:45:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260716_2145"
down_revision: str | None = "20260714_2230"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "database_backup_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("local_file_name", sa.String(length=255), nullable=False),
        sa.Column("local_size_bytes", sa.Integer(), nullable=False),
        sa.Column("local_created_at", sa.DateTime(), nullable=False),
        sa.Column("remote_enabled", sa.Boolean(), nullable=False),
        sa.Column("remote_configured", sa.Boolean(), nullable=False),
        sa.Column("remote_status", sa.String(length=32), nullable=False),
        sa.Column("remote_message", sa.Text(), nullable=False),
        sa.Column("remote_asset_name", sa.String(length=255), nullable=True),
        sa.Column("remote_uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_database_backup_runs_created_at",
        "database_backup_runs",
        ["created_at"],
    )
    op.create_index(
        "ix_database_backup_runs_local_file_name",
        "database_backup_runs",
        ["local_file_name"],
    )
    op.create_index(
        "ix_database_backup_runs_remote_status",
        "database_backup_runs",
        ["remote_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_database_backup_runs_remote_status", table_name="database_backup_runs")
    op.drop_index("ix_database_backup_runs_local_file_name", table_name="database_backup_runs")
    op.drop_index("ix_database_backup_runs_created_at", table_name="database_backup_runs")
    op.drop_table("database_backup_runs")
