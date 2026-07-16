from pydantic import BaseModel, Field


class LotteryNumbersRead(BaseModel):
    count: int
    min: int
    max: int


class PrizeTierRead(BaseModel):
    tier: int
    tier_name: str
    front_match_count: int
    back_match_count: int
    is_floating: bool
    base_prize_amount: str | None
    addon_multiplier: str | None
    description: str


class LotteryRuleRead(BaseModel):
    rule_code: str
    rule_name: str
    game_code: str
    front: LotteryNumbersRead
    back: LotteryNumbersRead
    base_price: str
    addon_price: str
    addon_supported: bool
    official_url: str
    prize_tiers: list[PrizeTierRead]


class LotteryDrawRead(BaseModel):
    issue_no: str
    draw_date: str
    front_numbers: list[int] = Field(min_length=5, max_length=5)
    back_numbers: list[int] = Field(min_length=2, max_length=2)
    sales_amount: str | None
    pool_amount: str | None
    source_url: str | None


class LotteryDrawPageRead(BaseModel):
    items: list[LotteryDrawRead]
    pagination: dict[str, int]


class LotteryDrawCoverageRead(BaseModel):
    total: int
    latest_issue_no: str | None
    latest_draw_date: str | None
    earliest_issue_no: str | None
    earliest_draw_date: str | None
    start_year: int | None
    end_year: int | None
    year_span: int
    status: str
    status_label: str
    description: str


class DisclaimerRead(BaseModel):
    disclaimer: str


class LotterySyncRequest(BaseModel):
    sync_type: str = Field(default="manual", pattern="^(manual|backfill)$")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=500)
    force: bool = False


class LotteryBackfillRequest(BaseModel):
    start_page: int = Field(default=1, ge=1)
    page_count: int = Field(default=3, ge=1, le=20)
    page_size: int = Field(default=100, ge=1, le=500)
    force: bool = False


class LotterySyncRunRead(BaseModel):
    run_id: int
    game_code: str
    source: str
    sync_type: str
    status: str
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    requested_page: int | None
    requested_page_size: int | None
    fetched_count: int
    inserted_count: int
    updated_count: int
    skipped_count: int
    failed_count: int
    latest_issue_no: str | None
    error_code: str | None
    error_message: str | None
    source_url: str | None


class LotterySyncRunPageRead(BaseModel):
    items: list[LotterySyncRunRead]
    pagination: dict[str, int]


class LotteryBackfillRunRead(BaseModel):
    status: str
    start_page: int
    page_count: int
    page_size: int
    executed_pages: int
    latest_issue_no: str | None
    fetched_count: int
    inserted_count: int
    updated_count: int
    skipped_count: int
    failed_count: int
    runs: list[LotterySyncRunRead]


class LotteryBackfillJobRead(BaseModel):
    status: str
    message: str
    start_page: int
    page_count: int
    page_size: int
    force: bool


class LotterySyncStatusRead(BaseModel):
    enabled: bool
    running: bool
    cron: str
    timezone: str
    page_size: int
    next_run_at: str | None
    latest_run: LotterySyncRunRead | None


class LotteryNumberFrequencyRead(BaseModel):
    number: int
    count: int
    missing: int
    last_seen_issue_no: str | None


class LotteryNumericSummaryRead(BaseModel):
    min: int | None
    max: int | None
    average: float | None


class LotteryDistributionItemRead(BaseModel):
    pattern: str
    count: int


class LotteryDrawMetricRead(BaseModel):
    issue_no: str
    front_sum: int
    front_span: int
    front_parity_pattern: str
    front_size_pattern: str
    front_zone_pattern: str
    front_route012_pattern: str
    front_zone_counts: list[int] = Field(min_length=3, max_length=3)
    front_route012_counts: list[int] = Field(min_length=3, max_length=3)
    back_sum: int


class LotteryOmissionTrendPointRead(BaseModel):
    issue_no: str
    draw_date: str
    is_hit: bool
    missing: int


class LotteryNumberOmissionRead(BaseModel):
    area: str
    number: int
    appearances: int
    current_missing: int
    max_missing: int
    average_missing: float
    last_seen_issue_no: str | None
    last_seen_date: str | None
    trend: list[LotteryOmissionTrendPointRead]


class LotteryNumberHitIssueRead(BaseModel):
    issue_no: str
    draw_date: str


class LotteryNumberOmissionDetailRead(LotteryNumberOmissionRead):
    sample_size: int
    requested_limit: int
    hit_issues: list[LotteryNumberHitIssueRead]


class LotteryOmissionStatisticsRead(BaseModel):
    sample_size: int
    requested_limit: int
    latest_issue_no: str | None
    front: list[LotteryNumberOmissionRead]
    back: list[LotteryNumberOmissionRead]


class LotterySamePeriodItemRead(BaseModel):
    draw: LotteryDrawRead
    front_matches: list[int]
    back_matches: list[int]
    front_match_count: int
    back_match_count: int


class LotterySamePeriodAnalysisRead(BaseModel):
    target: LotteryDrawRead
    issue_suffix: str
    requested_count: int
    items: list[LotterySamePeriodItemRead]


class LotteryHotColdRead(BaseModel):
    front: list[LotteryNumberFrequencyRead]
    back: list[LotteryNumberFrequencyRead]


class LotteryBasicStatisticsRead(BaseModel):
    sample_size: int
    requested_limit: int
    latest_issue_no: str | None
    front_frequency: list[LotteryNumberFrequencyRead]
    back_frequency: list[LotteryNumberFrequencyRead]
    hot_numbers: LotteryHotColdRead
    cold_numbers: LotteryHotColdRead
    sum: LotteryNumericSummaryRead
    span: LotteryNumericSummaryRead
    parity: list[LotteryDistributionItemRead]
    size: list[LotteryDistributionItemRead]
    zone: list[LotteryDistributionItemRead]
    route012: list[LotteryDistributionItemRead]
    recent_metrics: list[LotteryDrawMetricRead]
    trend: list[LotteryDrawMetricRead]
