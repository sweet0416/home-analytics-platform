"""add fund disclosures

Revision ID: 20260731_1000
Revises: 20260730_1930
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_1000"
down_revision: str | None = "20260730_1930"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not inspector.has_table("fund_disclosures"):
        op.create_table(
            "fund_disclosures",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("fund_id", sa.Integer(), nullable=False),
            sa.Column("report_date", sa.Date(), nullable=False),
            sa.Column("report_period", sa.String(length=16), nullable=False),
            sa.Column("asset_type", sa.String(length=32), nullable=False),
            sa.Column("source", sa.String(length=64), nullable=False),
            sa.Column("source_url", sa.String(length=512), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["fund_id"], ["funds.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_fund_disclosures_fund_id",
            "fund_disclosures",
            ["fund_id"],
        )
        op.create_index(
            "ix_fund_disclosures_fund_report_type",
            "fund_disclosures",
            ["fund_id", "report_date", "asset_type"],
            unique=True,
        )
        op.create_index(
            "ix_fund_disclosures_report_date",
            "fund_disclosures",
            ["report_date"],
        )

    inspector = sa.inspect(connection)
    if not inspector.has_table("fund_disclosure_holdings"):
        op.create_table(
            "fund_disclosure_holdings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("disclosure_id", sa.Integer(), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("asset_type", sa.String(length=32), nullable=False),
            sa.Column("asset_code", sa.String(length=32), nullable=False),
            sa.Column("asset_name", sa.String(length=128), nullable=False),
            sa.Column("nav_ratio", sa.Numeric(12, 8), nullable=False),
            sa.Column("reported_quantity", sa.Numeric(24, 4), nullable=True),
            sa.Column("reported_market_value", sa.Numeric(24, 4), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["disclosure_id"],
                ["fund_disclosures.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_fund_disclosure_holdings_disclosure_id",
            "fund_disclosure_holdings",
            ["disclosure_id"],
        )
        op.create_index(
            "ix_fund_disclosure_holdings_disclosure_rank",
            "fund_disclosure_holdings",
            ["disclosure_id", "rank"],
            unique=True,
        )
        op.create_index(
            "ix_fund_disclosure_holdings_asset",
            "fund_disclosure_holdings",
            ["asset_type", "asset_code"],
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if inspector.has_table("fund_disclosure_holdings"):
        op.drop_index(
            "ix_fund_disclosure_holdings_asset",
            table_name="fund_disclosure_holdings",
        )
        op.drop_index(
            "ix_fund_disclosure_holdings_disclosure_rank",
            table_name="fund_disclosure_holdings",
        )
        op.drop_index(
            "ix_fund_disclosure_holdings_disclosure_id",
            table_name="fund_disclosure_holdings",
        )
        op.drop_table("fund_disclosure_holdings")

    inspector = sa.inspect(connection)
    if inspector.has_table("fund_disclosures"):
        op.drop_index(
            "ix_fund_disclosures_report_date",
            table_name="fund_disclosures",
        )
        op.drop_index(
            "ix_fund_disclosures_fund_report_type",
            table_name="fund_disclosures",
        )
        op.drop_index(
            "ix_fund_disclosures_fund_id",
            table_name="fund_disclosures",
        )
        op.drop_table("fund_disclosures")
