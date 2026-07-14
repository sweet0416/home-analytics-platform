from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class LotteryGameModel(Base):
    __tablename__ = "lottery_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    region: Mapped[str] = mapped_column(String(32), default="CN")
    official_source: Mapped[str] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LotteryRuleVersionModel(Base):
    __tablename__ = "lottery_rule_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_code: Mapped[str] = mapped_column(String(32), index=True)
    rule_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(128))
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    front_count: Mapped[int] = mapped_column(Integer)
    front_min: Mapped[int] = mapped_column(Integer)
    front_max: Mapped[int] = mapped_column(Integer)
    back_count: Mapped[int] = mapped_column(Integer)
    back_min: Mapped[int] = mapped_column(Integer)
    back_max: Mapped[int] = mapped_column(Integer)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    addon_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    addon_supported: Mapped[bool] = mapped_column(Boolean, default=True)
    official_url: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    prize_tiers: Mapped[list["LotteryPrizeTierModel"]] = relationship(
        back_populates="rule_version",
        cascade="all, delete-orphan",
    )


class LotteryPrizeTierModel(Base):
    __tablename__ = "lottery_prize_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_version_id: Mapped[int] = mapped_column(ForeignKey("lottery_rule_versions.id"))
    tier: Mapped[int] = mapped_column(Integer)
    tier_name: Mapped[str] = mapped_column(String(64))
    front_match_count: Mapped[int] = mapped_column(Integer)
    back_match_count: Mapped[int] = mapped_column(Integer)
    condition_type: Mapped[str] = mapped_column(String(64), default="exact_match")
    is_floating: Mapped[bool] = mapped_column(Boolean, default=False)
    base_prize_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    addon_multiplier: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rule_version: Mapped[LotteryRuleVersionModel] = relationship(back_populates="prize_tiers")


class LotteryDrawModel(Base):
    __tablename__ = "lottery_draws"
    __table_args__ = (UniqueConstraint("game_code", "issue_no", name="uq_lottery_draw_game_issue"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_code: Mapped[str] = mapped_column(String(32), index=True)
    issue_no: Mapped[str] = mapped_column(String(32), index=True)
    draw_date: Mapped[date] = mapped_column(Date, index=True)
    front_numbers_json: Mapped[str] = mapped_column(Text)
    back_numbers_json: Mapped[str] = mapped_column(Text)
    sales_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    pool_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    rule_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("lottery_rule_versions.id"),
        nullable=True,
    )
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LotteryDrawPrizeResultModel(Base):
    __tablename__ = "lottery_draw_prize_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draw_id: Mapped[int] = mapped_column(ForeignKey("lottery_draws.id"), index=True)
    tier: Mapped[int] = mapped_column(Integer)
    base_winner_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_prize_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    addon_winner_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    addon_prize_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

