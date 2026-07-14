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


class DisclaimerRead(BaseModel):
    disclaimer: str


class LotterySyncRequest(BaseModel):
    sync_type: str = Field(default="manual", pattern="^(manual|backfill)$")
    page: int = Field(default=1, ge=1)
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
