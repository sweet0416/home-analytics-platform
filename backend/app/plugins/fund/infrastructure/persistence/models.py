from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
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
    watchlist_items: Mapped[list["FundWatchlistItemModel"]] = relationship(back_populates="fund")


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
    opened_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    tags: Mapped[str] = mapped_column(String(256), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fund: Mapped[FundModel] = relationship(back_populates="positions")
