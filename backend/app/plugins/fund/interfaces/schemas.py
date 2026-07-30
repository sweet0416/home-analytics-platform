from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.notification.schemas import NotificationChannel


class FundWatchlistCreate(BaseModel):
    fund_code: str = Field(min_length=1, max_length=16)
    fund_name: str = Field(min_length=1, max_length=128)
    fund_type: str = Field(default="unknown", max_length=64)
    priority: int = Field(default=3, ge=1, le=5)
    status: str = Field(default="watching", max_length=32)
    watch_reason: str = Field(default="", max_length=256)
    risk_level: str = Field(default="medium", max_length=32)
    target_position: str = Field(default="", max_length=64)
    tags: str = Field(default="", max_length=256)
    note: str = ""

    @field_validator(
        "fund_code",
        "fund_name",
        "fund_type",
        "status",
        "watch_reason",
        "risk_level",
        "target_position",
        "tags",
        "note",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class FundWatchlistUpdate(FundWatchlistCreate):
    pass


class FundWatchlistRead(BaseModel):
    id: int
    fund_id: int
    fund_code: str
    fund_name: str
    fund_type: str
    priority: int
    status: str
    watch_reason: str
    risk_level: str
    target_position: str
    tags: str
    note: str
    created_at: datetime
    updated_at: datetime


class FundNavRecordCreate(BaseModel):
    fund_code: str = Field(min_length=1, max_length=16)
    fund_name: str = Field(min_length=1, max_length=128)
    fund_type: str = Field(default="unknown", max_length=64)
    nav_date: date
    unit_nav: Decimal = Field(gt=0, decimal_places=4)
    accumulated_nav: Decimal | None = Field(default=None, gt=0, decimal_places=4)
    source: str = Field(default="manual", max_length=64)
    note: str = ""

    @field_validator("fund_code", "fund_name", "fund_type", "source", "note")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class FundNavSyncLatestRequest(BaseModel):
    fund_code: str = Field(min_length=1, max_length=16)
    fund_type: str = Field(default="unknown", max_length=64)

    @field_validator("fund_code", "fund_type")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class FundNavHistorySyncRequest(FundNavSyncLatestRequest):
    limit: int = Field(default=365, ge=2, le=500)


class FundNavHistorySyncRead(BaseModel):
    fund_code: str
    fund_name: str
    fund_type: str
    synced_count: int
    earliest_date: date
    latest_date: date
    source: str


class FundHoldingHistorySyncRequest(BaseModel):
    limit: int = Field(default=365, ge=2, le=500)


class FundHoldingHistorySyncItemRead(BaseModel):
    fund_code: str
    fund_name: str
    status: Literal["succeeded", "failed"]
    synced_count: int = 0
    earliest_date: date | None = None
    latest_date: date | None = None
    source: str = ""
    message: str = ""


class FundHoldingHistorySyncRead(BaseModel):
    total: int
    succeeded: int
    failed: int
    synced_count: int
    items: list[FundHoldingHistorySyncItemRead]


class FundLatestNavRead(BaseModel):
    fund_code: str
    fund_name: str
    fund_type: str
    nav_date: date
    unit_nav: Decimal
    accumulated_nav: Decimal | None
    source: str
    source_url: str


class FundWatchlistNavSyncItemRead(BaseModel):
    fund_code: str
    fund_name: str
    status: str
    nav_date: date | None = None
    unit_nav: Decimal | None = None
    updated: bool = False
    message: str = ""


class FundWatchlistNavSyncRead(BaseModel):
    total: int
    succeeded: int
    failed: int
    updated: int = 0
    items: list[FundWatchlistNavSyncItemRead]


class FundTrackedNavSyncRead(FundWatchlistNavSyncRead):
    pass


class FundScheduledNavSyncRunRead(BaseModel):
    status: Literal["succeeded", "partial", "failed"]
    started_at: datetime
    finished_at: datetime
    total: int
    succeeded: int
    failed: int
    updated: int
    skipped: bool
    message: str


class FundNavSchedulerStatusRead(BaseModel):
    enabled: bool
    running: bool
    cron: str
    timezone: str
    next_run_at: datetime | None
    last_run: FundScheduledNavSyncRunRead | None


class FundNavRecordRead(BaseModel):
    id: int
    fund_id: int
    fund_code: str
    fund_name: str
    fund_type: str
    nav_date: date
    unit_nav: Decimal
    accumulated_nav: Decimal | None
    source: str
    note: str
    created_at: datetime
    updated_at: datetime


class FundNavRiskRead(BaseModel):
    fund_code: str
    fund_name: str
    sample_count: int
    return_observation_count: int
    start_date: date | None
    end_date: date | None
    cumulative_return: Decimal | None
    annualized_volatility: Decimal | None
    maximum_drawdown: Decimal | None
    drawdown_peak_date: date | None
    drawdown_trough_date: date | None
    positive_day_ratio: Decimal | None
    calculation_available: bool
    warning: str


class FundPositionCreate(BaseModel):
    fund_code: str = Field(min_length=1, max_length=16)
    fund_name: str = Field(min_length=1, max_length=128)
    fund_type: str = Field(default="unknown", max_length=64)
    account_name: str = Field(default="默认账户", max_length=64)
    shares: Decimal = Field(gt=0, decimal_places=4)
    cost_price: Decimal = Field(gt=0, decimal_places=4)
    total_cost: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    current_nav: Decimal | None = Field(default=None, gt=0, decimal_places=4)
    opened_at: date | None = None
    tags: str = Field(default="", max_length=256)
    note: str = ""

    @field_validator("fund_code", "fund_name", "fund_type", "account_name", "tags", "note")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @property
    def normalized_total_cost(self) -> Decimal:
        value = self.total_cost if self.total_cost is not None else self.shares * self.cost_price
        return value.quantize(Decimal("0.01"))


class FundPositionUpdate(FundPositionCreate):
    pass


class FundPositionRead(BaseModel):
    id: int
    fund_id: int
    fund_code: str
    fund_name: str
    fund_type: str
    account_name: str
    shares: Decimal
    cost_price: Decimal
    total_cost: Decimal
    current_nav: Decimal | None
    current_value: Decimal | None
    unrealized_profit: Decimal | None
    unrealized_return_rate: Decimal | None
    opened_at: date | None
    tags: str
    note: str
    created_at: datetime
    updated_at: datetime


class FundTransactionCreate(BaseModel):
    fund_code: str = Field(min_length=1, max_length=16)
    fund_name: str = Field(min_length=1, max_length=128)
    fund_type: str = Field(default="unknown", max_length=64)
    account_name: str = Field(default="默认账户", max_length=64)
    transaction_type: Literal["buy", "sell", "dividend", "fee"]
    trade_date: date
    shares: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, gt=0)
    amount: Decimal | None = Field(default=None, gt=0)
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    note: str = ""

    @model_validator(mode="after")
    def validate_transaction_values(self) -> "FundTransactionCreate":
        if self.transaction_type in {"buy", "sell"}:
            if self.shares is None or self.unit_price is None:
                raise ValueError("Buy and sell transactions require shares and unit_price.")
        elif self.amount is None:
            raise ValueError("Dividend and fee transactions require amount.")
        return self

    @property
    def normalized_amount(self) -> Decimal:
        if self.transaction_type in {"buy", "sell"}:
            if self.shares is None or self.unit_price is None:
                raise ValueError("Transaction amount cannot be calculated.")
            return self.shares * self.unit_price
        if self.amount is None:
            raise ValueError("Transaction amount is required.")
        return self.amount


class FundTransactionRead(BaseModel):
    id: int
    fund_id: int
    fund_code: str
    fund_name: str
    fund_type: str
    account_name: str
    transaction_type: Literal["buy", "sell", "dividend", "fee"]
    trade_date: date
    shares: Decimal | None
    unit_price: Decimal | None
    amount: Decimal
    fee: Decimal
    cash_flow: Decimal
    note: str
    created_at: datetime
    updated_at: datetime


class FundTransactionSummaryRead(BaseModel):
    transaction_count: int
    total_buy: Decimal
    total_sell: Decimal
    total_dividend: Decimal
    total_fee: Decimal
    net_cash_flow: Decimal


class FundCashFlowPerformanceRead(BaseModel):
    transaction_count: int
    position_count: int
    valuation_complete: bool
    calculation_available: bool
    invested_cash: Decimal
    recovered_cash: Decimal
    current_value: Decimal | None
    net_profit: Decimal | None
    simple_return_rate: Decimal | None
    earliest_trade_date: date | None
    latest_trade_date: date | None
    calculation_basis: str
    warning: str


class FundHoldingSummaryRead(BaseModel):
    position_count: int
    fund_count: int
    total_cost: Decimal
    current_value: Decimal | None
    unrealized_profit: Decimal | None
    unrealized_return_rate: Decimal | None
    valued_position_count: int
    fund_types: list[str]
    accounts: list[str]


class FundAllocationGroupRead(BaseModel):
    label: str
    amount: Decimal
    weight: Decimal
    position_count: int


class FundAllocationHoldingRead(BaseModel):
    position_id: int
    fund_code: str
    fund_name: str
    fund_type: str
    account_name: str
    amount: Decimal
    weight: Decimal
    valuation_basis: Literal["current_nav", "cost"]


class FundAllocationRead(BaseModel):
    position_count: int
    total_amount: Decimal
    current_nav_count: int
    cost_fallback_count: int
    top_holding_weight: Decimal | None
    concentration_hhi: Decimal | None
    by_fund_type: list[FundAllocationGroupRead]
    by_account: list[FundAllocationGroupRead]
    holdings: list[FundAllocationHoldingRead]


class FundHoldingRiskItemRead(BaseModel):
    fund_code: str
    fund_name: str
    fund_type: str
    position_count: int
    allocation_weight: Decimal
    sample_count: int
    start_date: date | None
    end_date: date | None
    cumulative_return: Decimal | None
    annualized_volatility: Decimal | None
    maximum_drawdown: Decimal | None
    positive_day_ratio: Decimal | None
    calculation_available: bool


class FundHoldingRiskRead(BaseModel):
    fund_count: int
    analyzed_fund_count: int
    sample_limit: int
    items: list[FundHoldingRiskItemRead]
    warning: str


class FundWatchlistSummaryRead(BaseModel):
    item_count: int
    fund_count: int
    high_priority_count: int
    statuses: list[str]
    risk_levels: list[str]


class FundNavSummaryRead(BaseModel):
    record_count: int
    fund_count: int
    latest_nav_date: date | None
    sources: list[str]


class FundDailyAlertRead(BaseModel):
    code: str
    level: Literal["info", "warning"]
    message: str


class FundDailyReportRead(BaseModel):
    report_date: date
    generated_at: datetime
    holding_summary: FundHoldingSummaryRead
    allocation: FundAllocationRead
    holding_risk: FundHoldingRiskRead
    watchlist_summary: FundWatchlistSummaryRead
    nav_summary: FundNavSummaryRead
    transaction_summary: FundTransactionSummaryRead
    valuation_complete: bool
    nav_age_days: int | None
    alerts: list[FundDailyAlertRead]


class FundDailyPushRequest(BaseModel):
    channel: NotificationChannel = NotificationChannel.bark


class FundModuleRead(BaseModel):
    code: str
    name: str
    description: str
    status: str


class FundStatusRead(BaseModel):
    plugin: str
    display_name: str
    version: str
    status: str
    description: str
    modules: list[FundModuleRead]
    data_source_status: str
    storage_status: str
    next_step: str
