"""Recognize the additive notification health-state schema in rollback builds.

Revision ID: 20260927_1200
Revises: 20260808_0022
"""

import sqlalchemy as sa

from alembic import op

revision = "20260927_1200"
down_revision = "20260808_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("notification_delivery_runs"):
        return  # Fresh databases are populated by create_database_schema.
    if "health_state" not in {column["name"] for column in inspector.get_columns("notification_delivery_runs")}:
        op.add_column("notification_delivery_runs", sa.Column("health_state", sa.Text(), nullable=True))


def downgrade() -> None:
    raise RuntimeError("Rollback image does not support destructive database downgrade")
