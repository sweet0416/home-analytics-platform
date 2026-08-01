from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class FundModel(Base):
    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    fund_type: Mapped[str] = mapped_column(String(64), default="unknown")
    source: Mapped[str] = mapped_column(String(64), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    positions: Mapped[list["FundPositionModel"]] = relationship(back_populates="fund")
    transactions: Mapped[list["FundTransactionModel"]] = relationship(back_populates="fund")
    watchlist_items: Mapped[list["FundWatchlistItemModel"]] = relationship(back_populates="fund")
    nav_records: Mapped[list["FundNavRecordModel"]] = relationship(back_populates="fund")
    disclosures: Mapped[list["FundDisclosureModel"]] = relationship(
        back_populates="fund",
        cascade="all, delete-orphan",
    )


class FundTargetLinkModel(Base):
    __tablename__ = "fund_target_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_fund_code: Mapped[str] = mapped_column(
        String(16), unique=True, index=True
    )
    target_fund_code: Mapped[str] = mapped_column(String(16), index=True)
    target_fund_name: Mapped[str] = mapped_column(String(128))
    target_allocation_ratio: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    report_date: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str] = mapped_column(String(512))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FundWatchlistItemModel(Base):
    __tablename__ = "fund_watchlist_items"
    __table_args__ = (
        Index("ix_fund_watchlist_priority_created", "priority", "created_at"),
        Index("ix_fund_watchlist_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(32), default="watching")
    watch_reason: Mapped[str] = mapped_column(String(256), default="")
    risk_level: Mapped[str] = mapped_column(String(32), default="medium")
    target_position: Mapped[str] = mapped_column(String(64), default="")
    tags: Mapped[str] = mapped_column(String(256), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fund: Mapped[FundModel] = relationship(back_populates="watchlist_items")


class FundNavRecordModel(Base):
    __tablename__ = "fund_nav_records"
    __table_args__ = (
        Index("ix_fund_nav_records_fund_date", "fund_id", "nav_date", unique=True),
        Index("ix_fund_nav_records_date", "nav_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), index=True)
    nav_date: Mapped[date] = mapped_column(Date)
    unit_nav: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    accumulated_nav: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="manual")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fund: Mapped[FundModel] = relationship(back_populates="nav_records")


class FundPositionModel(Base):
    __tablename__ = "fund_positions"
    __table_args__ = (
        Index("ix_fund_positions_fund_created", "fund_id", "created_at"),
        Index("ix_fund_positions_account_created", "account_name", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), index=True)
    account_name: Mapped[str] = mapped_column(String(64), default="默认账户")
    shares: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    current_nav: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    target_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 8),
        nullable=True,
    )
    opened_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    tags: Mapped[str] = mapped_column(String(256), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fund: Mapped[FundModel] = relationship(back_populates="positions")


class FundTransactionModel(Base):
    __tablename__ = "fund_transactions"
    __table_args__ = (
        Index("ix_fund_transactions_fund_date", "fund_id", "trade_date"),
        Index("ix_fund_transactions_account_date", "account_name", "trade_date"),
        Index("ix_fund_transactions_type_date", "transaction_type", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), index=True)
    account_name: Mapped[str] = mapped_column(String(64), default="默认账户")
    transaction_type: Mapped[str] = mapped_column(String(32))
    trade_date: Mapped[date] = mapped_column(Date)
    shares: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fund: Mapped[FundModel] = relationship(back_populates="transactions")


class FundNavSyncRunModel(Base):
    __tablename__ = "fund_nav_sync_runs"
    __table_args__ = (
        Index("ix_fund_nav_sync_runs_finished", "finished_at"),
        Index("ix_fund_nav_sync_runs_status_finished", "status", "finished_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger_type: Mapped[str] = mapped_column(String(32), default="scheduled")
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime] = mapped_column(DateTime)
    total: Mapped[int] = mapped_column(Integer, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FundDisclosureModel(Base):
    __tablename__ = "fund_disclosures"
    __table_args__ = (
        Index(
            "ix_fund_disclosures_fund_report_type",
            "fund_id",
            "report_date",
            "asset_type",
            unique=True,
        ),
        Index("ix_fund_disclosures_report_date", "report_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), index=True)
    report_date: Mapped[date] = mapped_column(Date)
    report_period: Mapped[str] = mapped_column(String(16))
    asset_type: Mapped[str] = mapped_column(String(32), default="stock")
    source: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fund: Mapped[FundModel] = relationship(back_populates="disclosures")
    holdings: Mapped[list["FundDisclosureHoldingModel"]] = relationship(
        back_populates="disclosure",
        cascade="all, delete-orphan",
        order_by="FundDisclosureHoldingModel.rank",
    )


class FundDisclosureHoldingModel(Base):
    __tablename__ = "fund_disclosure_holdings"
    __table_args__ = (
        Index(
            "ix_fund_disclosure_holdings_disclosure_rank",
            "disclosure_id",
            "rank",
            unique=True,
        ),
        Index(
            "ix_fund_disclosure_holdings_asset",
            "asset_type",
            "asset_code",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disclosure_id: Mapped[int] = mapped_column(
        ForeignKey("fund_disclosures.id"),
        index=True,
    )
    rank: Mapped[int] = mapped_column(Integer)
    asset_type: Mapped[str] = mapped_column(String(32), default="stock")
    asset_code: Mapped[str] = mapped_column(String(32))
    asset_name: Mapped[str] = mapped_column(String(128))
    nav_ratio: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    reported_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 4),
        nullable=True,
    )
    reported_market_value: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 4),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    disclosure: Mapped[FundDisclosureModel] = relationship(
        back_populates="holdings"
    )
