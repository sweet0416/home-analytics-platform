"""add external identity and confirmation fields to fund transactions

Revision ID: 20260808_0022
Revises: 20260808_0021
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0022"
down_revision: str | None = "20260808_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not inspector.has_table("fund_transactions"):
        return
    columns = {column["name"] for column in inspector.get_columns("fund_transactions")}
    additions = (
        ("external_source", sa.String(length=64)),
        ("external_trade_id", sa.String(length=128)),
        ("external_trade_type", sa.String(length=32)),
        ("external_business_code", sa.String(length=32)),
        ("external_status", sa.String(length=64)),
        ("external_confirm_status", sa.String(length=32)),
        ("confirm_date", sa.Date()),
        ("source_updated_at", sa.DateTime()),
    )
    for name, column_type in additions:
        if name not in columns:
            op.add_column("fund_transactions", sa.Column(name, column_type, nullable=True))
    if "ix_fund_transactions_external_trade" not in {
        index["name"] for index in inspector.get_indexes("fund_transactions")
    }:
        op.create_index(
            "ix_fund_transactions_external_trade",
            "fund_transactions",
            ["external_source", "external_trade_id"],
            unique=True,
        )


def downgrade() -> None:
    connection = op.get_bind()
    if not sa.inspect(connection).has_table("fund_transactions"):
        return
    if "ix_fund_transactions_external_trade" in {
        index["name"] for index in sa.inspect(connection).get_indexes("fund_transactions")
    }:
        op.drop_index("ix_fund_transactions_external_trade", table_name="fund_transactions")
    columns = {column["name"] for column in sa.inspect(connection).get_columns("fund_transactions")}
    for name in (
        "source_updated_at",
        "confirm_date",
        "external_confirm_status",
        "external_status",
        "external_business_code",
        "external_trade_type",
        "external_trade_id",
        "external_source",
    ):
        if name in columns:
            op.drop_column("fund_transactions", name)
