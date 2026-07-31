"""add fund target links

Revision ID: 20260731_2200
Revises: 20260731_1000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_2200"
down_revision: str | None = "20260731_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("fund_target_links"):
        return

    op.create_table(
        "fund_target_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_fund_code", sa.String(length=16), nullable=False),
        sa.Column("target_fund_code", sa.String(length=16), nullable=False),
        sa.Column("target_fund_name", sa.String(length=128), nullable=False),
        sa.Column(
            "target_allocation_ratio",
            sa.Numeric(12, 8),
            nullable=False,
        ),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("source_url", sa.String(length=512), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fund_target_links_parent_fund_code",
        "fund_target_links",
        ["parent_fund_code"],
        unique=True,
    )
    op.create_index(
        "ix_fund_target_links_target_fund_code",
        "fund_target_links",
        ["target_fund_code"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    if not sa.inspect(connection).has_table("fund_target_links"):
        return
    op.drop_index(
        "ix_fund_target_links_target_fund_code",
        table_name="fund_target_links",
    )
    op.drop_index(
        "ix_fund_target_links_parent_fund_code",
        table_name="fund_target_links",
    )
    op.drop_table("fund_target_links")
