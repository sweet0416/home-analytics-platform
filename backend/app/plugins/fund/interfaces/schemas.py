from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from urllib.parse import urlparse

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
    id: int | None = None
    trigger_type: str = "scheduled"
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
    notification_enabled: bool
    notification_channel: NotificationChannel
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
    target_weight: Decimal | None = Field(
        default=None,
        ge=0,
        le=1,
        decimal_places=8,
    )
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
    target_weight: Decimal | None
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


class FundNavFreshnessItemRead(BaseModel):
    fund_code: str
    fund_name: str
    fund_type: str
    account_names: list[str]
    latest_nav_date: date | None
    business_day_age: int | None
    allowed_business_days: int
    source: str | None
    status: Literal["fresh", "stale", "missing"]


class FundNavFreshnessRead(BaseModel):
    as_of_date: date
    stale_after_business_days: int
    qdii_stale_after_business_days: int
    position_count: int
    fund_count: int
    fresh_count: int
    stale_count: int
    missing_count: int
    oldest_nav_date: date | None
    items: list[FundNavFreshnessItemRead]


class FundProfileSyncItemRead(BaseModel):
    fund_code: str
    fund_name: str
    previous_type: str
    detected_type: str | None
    current_type: str
    status: Literal["updated", "unchanged", "failed"]
    message: str


class FundProfileSyncRead(BaseModel):
    total: int
    updated: int
    unchanged: int
    failed: int
    items: list[FundProfileSyncItemRead]


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
    target_weight: Decimal | None
    weight_deviation: Decimal | None
    target_amount: Decimal | None
    calibration_amount: Decimal | None
    valuation_basis: Literal["current_nav", "cost"]


class FundAllocationRead(BaseModel):
    position_count: int
    total_amount: Decimal
    current_nav_count: int
    cost_fallback_count: int
    top_holding_weight: Decimal | None
    concentration_hhi: Decimal | None
    configured_target_count: int
    target_weight_total: Decimal
    target_configuration_complete: bool
    target_warning: str
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


class FundPortfolioMemberRead(BaseModel):
    fund_code: str
    fund_name: str
    allocation_weight: Decimal
    sample_count: int


class FundPortfolioPerformancePointRead(BaseModel):
    nav_date: date
    portfolio_index: Decimal
    equal_weight_index: Decimal
    drawdown: Decimal


class FundPortfolioPerformanceRead(BaseModel):
    fund_count: int
    included_fund_count: int
    sample_limit: int
    sample_count: int
    start_date: date | None
    end_date: date | None
    valuation_complete: bool
    cumulative_return: Decimal | None
    equal_weight_return: Decimal | None
    annualized_volatility: Decimal | None
    maximum_drawdown: Decimal | None
    calculation_available: bool
    members: list[FundPortfolioMemberRead]
    excluded_fund_codes: list[str]
    points: list[FundPortfolioPerformancePointRead]
    warning: str


class FundPortfolioBenchmarkPointRead(BaseModel):
    nav_date: date
    portfolio_index: Decimal
    benchmark_index: Decimal
    relative_return: Decimal


class FundPortfolioBenchmarkRead(BaseModel):
    benchmark_code: str
    benchmark_name: str
    sample_limit: int
    sample_count: int
    start_date: date | None
    end_date: date | None
    portfolio_return: Decimal | None
    benchmark_return: Decimal | None
    relative_return: Decimal | None
    tracking_error: Decimal | None
    information_ratio: Decimal | None
    return_correlation: Decimal | None
    calculation_available: bool
    points: list[FundPortfolioBenchmarkPointRead]
    warning: str


class FundCorrelationMemberRead(BaseModel):
    fund_code: str
    fund_name: str
    allocation_weight: Decimal
    sample_count: int


class FundCorrelationPairRead(BaseModel):
    first_fund_code: str
    second_fund_code: str
    observation_count: int
    correlation: Decimal | None


class FundHoldingCorrelationRead(BaseModel):
    fund_count: int
    sample_limit: int
    calculated_pair_count: int
    total_pair_count: int
    average_pairwise_correlation: Decimal | None
    high_correlation_pair_count: int
    members: list[FundCorrelationMemberRead]
    pairs: list[FundCorrelationPairRead]
    warning: str


class FundRiskContributionItemRead(BaseModel):
    fund_code: str
    fund_name: str
    allocation_weight: Decimal
    annualized_volatility: Decimal
    component_volatility: Decimal
    contribution_ratio: Decimal


class FundRiskContributionRead(BaseModel):
    fund_count: int
    included_fund_count: int
    sample_limit: int
    sample_count: int
    start_date: date | None
    end_date: date | None
    portfolio_annualized_volatility: Decimal | None
    weighted_standalone_volatility: Decimal | None
    diversification_ratio: Decimal | None
    calculation_available: bool
    items: list[FundRiskContributionItemRead]
    excluded_fund_codes: list[str]
    warning: str


class FundDisclosureSyncItemRead(BaseModel):
    fund_code: str
    fund_name: str
    status: Literal["synced", "failed"]
    report_date: date | None
    holding_count: int
    message: str


class FundDisclosureSyncRead(BaseModel):
    total: int
    succeeded: int
    failed: int
    items: list[FundDisclosureSyncItemRead]


class FundTargetLinkCreate(BaseModel):
    parent_fund_code: str = Field(pattern=r"^\d{6}$")
    target_fund_code: str = Field(pattern=r"^\d{6}$")
    target_fund_name: str = Field(min_length=1, max_length=128)
    target_allocation_ratio: Decimal = Field(gt=0, le=1)
    report_date: date
    source_url: str = Field(min_length=1, max_length=512)

    @field_validator("parent_fund_code", "target_fund_code", "target_fund_name")
    @classmethod
    def strip_target_link_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        stripped = value.strip()
        parsed = urlparse(stripped)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must be an HTTP or HTTPS URL")
        return stripped

    @model_validator(mode="after")
    def validate_distinct_funds(self) -> "FundTargetLinkCreate":
        if self.parent_fund_code == self.target_fund_code:
            raise ValueError("parent and target fund codes must be different")
        return self


class FundTargetLinkRead(FundTargetLinkCreate):
    origin: Literal["environment", "database"]


class FundLookthroughAssetRead(BaseModel):
    asset_code: str
    asset_name: str
    portfolio_weight: Decimal
    fund_count: int


class FundLookthroughSnapshotRead(BaseModel):
    fund_code: str
    fund_name: str
    allocation_weight: Decimal
    covered_weight: Decimal
    report_date: date | None
    report_period: str | None
    age_days: int | None
    holding_count: int
    status: Literal["current", "stale", "missing"]
    source_mode: Literal["direct", "target_etf", "none"]
    target_fund_code: str | None
    target_fund_name: str | None
    target_allocation_ratio: Decimal | None
    relation_report_date: date | None


class FundLookthroughRead(BaseModel):
    as_of_date: date
    stale_after_days: int
    fund_count: int
    current_disclosure_count: int
    coverage_weight: Decimal
    disclosed_weight: Decimal
    assets: list[FundLookthroughAssetRead]
    snapshots: list[FundLookthroughSnapshotRead]
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


class FundDailyDataQualityRead(BaseModel):
    level: Literal["complete", "partial", "insufficient"]
    position_count: int
    valued_position_count: int
    latest_nav_date: date | None
    nav_age_days: int | None
    risk_fund_count: int
    risk_covered_fund_count: int
    risk_sample_count: int
    target_configured_count: int
    target_configuration_complete: bool
    target_weight_total: Decimal
    warnings: list[str]


class FundDailyFactRead(BaseModel):
    code: str
    category: Literal["performance", "risk", "allocation", "data_quality"]
    label: str
    value: str
    unit: str
    sample_scope: str
    severity: Literal["info", "warning"]


class FundDailyAnalysisContextRead(BaseModel):
    contract_version: Literal["fund-daily-context.v1"]
    report_date: date
    data_quality: FundDailyDataQualityRead
    facts: list[FundDailyFactRead]
    disclaimers: list[str]


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
    analysis_context: FundDailyAnalysisContextRead


class FundDailySnapshotChangeRead(BaseModel):
    position_count: int
    current_value: Decimal | None
    unrealized_profit: Decimal | None
    unrealized_return_rate: Decimal | None
    concentration_hhi: Decimal | None


class FundDailySnapshotRead(BaseModel):
    id: int
    report_date: date
    generated_at: datetime
    contract_version: str
    quality_level: Literal["complete", "partial", "insufficient"]
    position_count: int
    fund_count: int
    total_cost: Decimal
    current_value: Decimal | None
    unrealized_profit: Decimal | None
    unrealized_return_rate: Decimal | None
    valuation_complete: bool
    latest_nav_date: date | None
    nav_age_days: int | None
    risk_fund_count: int
    risk_covered_fund_count: int
    risk_sample_count: int
    top_holding_weight: Decimal | None
    concentration_hhi: Decimal | None
    target_configured_count: int
    target_configuration_complete: bool
    target_weight_total: Decimal
    alert_count: int
    warning_count: int
    change_from_previous: FundDailySnapshotChangeRead | None


class FundDailySnapshotHistoryRead(BaseModel):
    count: int
    items: list[FundDailySnapshotRead]


class FundDailyPeriodComparisonRead(BaseModel):
    period_days: Literal[7, 30]
    status: Literal["available", "insufficient"]
    latest_date: date | None
    baseline_date: date | None
    sample_count: int
    observed_span_days: int
    change: FundDailySnapshotChangeRead | None
    explanation: str


class FundDailyInsightAlertRead(BaseModel):
    code: str
    level: Literal["info", "warning"]
    message: str
    sample_scope: str


class FundDailyInsightsRead(BaseModel):
    contract_version: Literal["fund-daily-insights.v1"]
    generated_at: datetime
    snapshot_count: int
    latest_date: date | None
    comparisons: list[FundDailyPeriodComparisonRead]
    alerts: list[FundDailyInsightAlertRead]
    disclaimers: list[str]


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
