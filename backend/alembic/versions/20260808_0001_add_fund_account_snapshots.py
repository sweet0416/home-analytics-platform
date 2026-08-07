"""add fund account holding snapshots

Revision ID: 20260808_0001
Revises: 20260802_0030
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0001"
down_revision: str | None = "20260802_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not inspector.has_table("fund_account_snapshots"):
        op.create_table(
            "fund_account_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=64), nullable=False),
            sa.Column("account_label", sa.String(length=64), nullable=False),
            sa.Column("contract_version", sa.String(length=64), nullable=False),
            sa.Column("captured_at", sa.DateTime(), nullable=False),
            sa.Column("holding_count", sa.Integer(), nullable=False),
            sa.Column("total_asset_value", sa.Numeric(18, 2), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_fund_account_snapshots_captured",
            "fund_account_snapshots",
            ["captured_at"],
        )

    inspector = sa.inspect(connection)
    if inspector.has_table("fund_account_holding_snapshots"):
        return
    op.create_table(
        "fund_account_holding_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("asset_code", sa.String(length=32), nullable=False),
        sa.Column("asset_name", sa.String(length=128), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("asset_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("daily_profit", sa.Numeric(18, 2), nullable=True),
        sa.Column("hold_profit", sa.Numeric(18, 2), nullable=True),
        sa.Column("hold_profit_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("constant_profit", sa.Numeric(18, 2), nullable=True),
        sa.Column("constant_profit_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["fund_account_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fund_account_holding_snapshots_snapshot_id",
        "fund_account_holding_snapshots",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_fund_account_holding_snapshot_asset",
        "fund_account_holding_snapshots",
        ["snapshot_id", "asset_type", "asset_code"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if inspector.has_table("fund_account_holding_snapshots"):
        op.drop_index(
            "ix_fund_account_holding_snapshot_asset",
            table_name="fund_account_holding_snapshots",
        )
        op.drop_index(
            "ix_fund_account_holding_snapshots_snapshot_id",
            table_name="fund_account_holding_snapshots",
        )
        op.drop_table("fund_account_holding_snapshots")
    if sa.inspect(connection).has_table("fund_account_snapshots"):
        op.drop_index(
            "ix_fund_account_snapshots_captured",
            table_name="fund_account_snapshots",
        )
        op.drop_table("fund_account_snapshots")
