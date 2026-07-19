"""add notification delivery runs

Revision ID: 20260719_1545
Revises: 20260718_1530
Create Date: 2026-07-19 15:45:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_1545"
down_revision: str | None = "20260718_1530"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_delivery_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message_preview", sa.Text(), nullable=False),
        sa.Column("result_message", sa.Text(), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_delivery_runs_channel",
        "notification_delivery_runs",
        ["channel"],
    )
    op.create_index(
        "ix_notification_delivery_runs_channel_status",
        "notification_delivery_runs",
        ["channel", "status"],
    )
    op.create_index(
        "ix_notification_delivery_runs_created_at",
        "notification_delivery_runs",
        ["created_at"],
    )
    op.create_index(
        "ix_notification_delivery_runs_source",
        "notification_delivery_runs",
        ["source"],
    )
    op.create_index(
        "ix_notification_delivery_runs_status",
        "notification_delivery_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_delivery_runs_status", table_name="notification_delivery_runs")
    op.drop_index("ix_notification_delivery_runs_source", table_name="notification_delivery_runs")
    op.drop_index("ix_notification_delivery_runs_created_at", table_name="notification_delivery_runs")
    op.drop_index("ix_notification_delivery_runs_channel_status", table_name="notification_delivery_runs")
    op.drop_index("ix_notification_delivery_runs_channel", table_name="notification_delivery_runs")
    op.drop_table("notification_delivery_runs")
