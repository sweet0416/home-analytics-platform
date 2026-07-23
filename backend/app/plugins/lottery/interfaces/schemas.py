from pydantic import BaseModel, Field, field_validator


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
    details: list[dict[str, str]]


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


class LotteryRecommendationNumberRead(BaseModel):
    number: int
    score: float
    same_period_hits: int
    recent_frequency: int
    current_missing: int
    reasons: list[str]


class LotteryRecommendationSetRead(BaseModel):
    rank: int
    front_numbers: list[int] = Field(min_length=5, max_length=5)
    back_numbers: list[int] = Field(min_length=2, max_length=2)
    score: float
    rationale: list[str]
    front_sum: int
    front_span: int
    front_parity_pattern: str
    front_zone_pattern: str
    front_route012_pattern: str
    front_details: list[LotteryRecommendationNumberRead]
    back_details: list[LotteryRecommendationNumberRead]


class LotteryRecommendationRead(BaseModel):
    target_issue_no: str
    issue_suffix: str
    sample_size: int
    same_period_count: int
    requested_sets: int
    disclaimer: str
    strategy_weights: dict[str, float]
    methodology: list[str]
    same_period_repeated_front: list[LotteryRecommendationNumberRead]
    same_period_repeated_back: list[LotteryRecommendationNumberRead]
    recommendations: list[LotteryRecommendationSetRead]


class LotterySimulationSetRead(BaseModel):
    rank: int
    front_numbers: list[int] = Field(min_length=5, max_length=5)
    back_numbers: list[int] = Field(min_length=2, max_length=2)
    front_sum: int
    front_span: int
    front_parity_pattern: str
    front_zone_pattern: str
    front_route012_pattern: str


class LotterySimulationFrequencyRead(BaseModel):
    number: int
    count: int
    frequency: float
    expected_probability: float
    deviation: float


class LotterySimulationTheoreticalRead(BaseModel):
    front_probability: float
    back_probability: float
    jackpot_probability: str
    jackpot_probability_decimal: float


class LotterySimulationRead(BaseModel):
    simulations: int
    requested_sets: int
    seed: int | None
    latest_issue_no: str
    disclaimer: str
    methodology: list[str]
    theoretical: LotterySimulationTheoreticalRead
    generated_sets: list[LotterySimulationSetRead]
    front_frequency: list[LotterySimulationFrequencyRead]
    back_frequency: list[LotterySimulationFrequencyRead]


class LotteryDantuoRequest(BaseModel):
    front_dan: list[int] = Field(default_factory=list)
    front_tuo: list[int] = Field(default_factory=list)
    front_kill: list[int] = Field(default_factory=list)
    back_dan: list[int] = Field(default_factory=list)
    back_tuo: list[int] = Field(default_factory=list)
    back_kill: list[int] = Field(default_factory=list)
    addon: bool = False
    preview_limit: int = Field(default=20, ge=1, le=200)


class LotteryDantuoCombinationRead(BaseModel):
    rank: int
    front_numbers: list[int] = Field(min_length=5, max_length=5)
    back_numbers: list[int] = Field(min_length=2, max_length=2)
    front_sum: int
    front_span: int
    front_parity_pattern: str
    front_zone_pattern: str
    front_route012_pattern: str


class LotteryDantuoAnalysisRead(BaseModel):
    disclaimer: str
    addon: bool
    front_required: int
    back_required: int
    front_combination_count: int
    back_combination_count: int
    total_bets: int
    base_cost: int
    addon_cost: int
    total_cost: int
    front_dan: list[int]
    front_tuo: list[int]
    front_kill: list[int]
    back_dan: list[int]
    back_tuo: list[int]
    back_kill: list[int]
    available_front: list[int]
    available_back: list[int]
    preview_limit: int
    preview: list[LotteryDantuoCombinationRead]
    warnings: list[str]
    methodology: list[str]


class LotteryBacktestRequest(BaseModel):
    front_numbers: list[int] = Field(min_length=5, max_length=5)
    back_numbers: list[int] = Field(min_length=2, max_length=2)
    addon: bool = False
    hit_limit: int = Field(default=20, ge=1, le=100)


class LotteryBacktestHitRead(BaseModel):
    issue_no: str
    draw_date: str
    draw_front_numbers: list[int] = Field(min_length=5, max_length=5)
    draw_back_numbers: list[int] = Field(min_length=2, max_length=2)
    front_matches: list[int]
    back_matches: list[int]
    front_match_count: int
    back_match_count: int
    match_key: str
    prize_tier: int
    tier_name: str
    is_floating: bool
    base_prize_amount: int | None


class LotteryBacktestDistributionRead(BaseModel):
    match_key: str
    front_match_count: int
    back_match_count: int
    count: int
    prize_tier: int | None
    tier_name: str


class LotteryBacktestAnalysisRead(BaseModel):
    disclaimer: str
    front_numbers: list[int] = Field(min_length=5, max_length=5)
    back_numbers: list[int] = Field(min_length=2, max_length=2)
    addon: bool
    sample_size: int
    earliest_issue_no: str
    latest_issue_no: str
    base_cost: int
    addon_cost: int
    total_cost: int
    fixed_prize_return: int
    floating_hit_count: int
    net_fixed_result: int
    hit_count: int
    no_prize_count: int
    highest_hit: LotteryBacktestHitRead | None
    latest_hit: LotteryBacktestHitRead | None
    hit_preview_limit: int
    hits: list[LotteryBacktestHitRead]
    distribution: list[LotteryBacktestDistributionRead]
    methodology: list[str]


class LotteryReplayStrategyRequest(BaseModel):
    same_period_weight: float = Field(default=45, ge=0, le=100)
    frequency_weight: float = Field(default=25, ge=0, le=100)
    missing_weight: float = Field(default=20, ge=0, le=100)
    structure_weight: float = Field(default=10, ge=0, le=100)


class LotteryReplayRequest(BaseModel):
    target_issue_no: str = Field(min_length=3, max_length=16)
    sets: int = Field(default=5, ge=1, le=12)
    sample_limit: int = Field(default=500, ge=20, le=2000)
    same_period_count: int = Field(default=10, ge=1, le=20)
    baseline_simulations: int = Field(default=10000, ge=100, le=50000)
    seed: int | None = Field(default=None, ge=0, le=2147483647)
    strategy: LotteryReplayStrategyRequest = Field(default_factory=LotteryReplayStrategyRequest)


class LotterySensitivityWeightProfileRequest(LotteryReplayStrategyRequest):
    name: str = Field(min_length=1, max_length=32)


class LotterySensitivityRequest(BaseModel):
    target_issue_no: str = Field(min_length=3, max_length=16)
    target_count: int = Field(default=1, ge=1, le=20)
    sets: int = Field(default=5, ge=1, le=12)
    same_period_count: int = Field(default=10, ge=1, le=20)
    sample_windows: list[int] = Field(default_factory=lambda: [50, 100, 200, 500])
    weight_profiles: list[LotterySensitivityWeightProfileRequest] = Field(default_factory=list)
    baseline_simulations: int = Field(default=3000, ge=100, le=20000)
    seed: int | None = Field(default=None, ge=0, le=2147483647)

    @field_validator("sample_windows")
    @classmethod
    def validate_sample_windows(cls, value: list[int]) -> list[int]:
        windows = sorted(set(value))
        if not windows:
            raise ValueError("At least one sample window is required.")
        if len(windows) > 8:
            raise ValueError("At most 8 sample windows are supported.")
        invalid = [item for item in windows if item < 20 or item > 2000]
        if invalid:
            raise ValueError("Sample windows must be between 20 and 2000.")
        return windows

    @field_validator("weight_profiles")
    @classmethod
    def validate_weight_profiles(
        cls,
        value: list[LotterySensitivityWeightProfileRequest],
    ) -> list[LotterySensitivityWeightProfileRequest]:
        if len(value) > 8:
            raise ValueError("At most 8 weight profiles are supported.")
        return value


class LotteryReplayLeakageCheckRead(BaseModel):
    passed: bool
    rule: str


class LotteryReplayRangeRead(BaseModel):
    earliest_issue_no: str | None
    latest_issue_no: str | None
    earliest_draw_date: str | None
    latest_draw_date: str | None


class LotteryReplayWarningRead(BaseModel):
    code: str
    message: str


class LotterySamePeriodDeviationMetricRead(BaseModel):
    label: str
    target_value: float
    historical_average: float
    deviation: float
    level: str


class LotterySamePeriodDeviationPatternRead(BaseModel):
    target_pattern: str
    historical_top_pattern: str
    historical_top_rate: float
    target_pattern_rate: float
    level: str


class LotterySamePeriodDeviationRead(BaseModel):
    issue_suffix: str
    sample_size: int
    front_repeat: LotterySamePeriodDeviationMetricRead
    back_repeat: LotterySamePeriodDeviationMetricRead
    front_sum: LotterySamePeriodDeviationMetricRead
    front_span: LotterySamePeriodDeviationMetricRead
    front_zone: LotterySamePeriodDeviationPatternRead
    front_route012: LotterySamePeriodDeviationPatternRead
    notes: list[str]


class LotteryReplayContextRead(BaseModel):
    target: LotteryDrawRead
    cutoff: LotteryDrawRead | None
    sample_size: int
    requested_sample_limit: int
    available_range: LotteryReplayRangeRead
    leakage_check: LotteryReplayLeakageCheckRead
    warnings: list[LotteryReplayWarningRead]
    same_period_deviation: LotterySamePeriodDeviationRead


class LotteryReplayGeneratedSetRead(BaseModel):
    rank: int
    front_numbers: list[int] = Field(min_length=5, max_length=5)
    back_numbers: list[int] = Field(min_length=2, max_length=2)
    score: float
    rationale: list[str]
    front_sum: int
    front_span: int
    front_parity_pattern: str
    front_zone_pattern: str
    front_route012_pattern: str
    front_details: list[LotteryRecommendationNumberRead]
    back_details: list[LotteryRecommendationNumberRead]
    front_matches: list[int]
    back_matches: list[int]
    front_match_count: int
    back_match_count: int
    match_key: str
    prize_tier: int | None
    baseline_percentile: float


class LotteryReplayBaselineRead(BaseModel):
    simulations: int
    seed: int | None
    average_front_match: float
    average_back_match: float
    average_score: float
    any_prize_rate: float
    explanation: str


class LotteryReplayRunRead(BaseModel):
    run_id: int
    target_issue_no: str
    target_draw: LotteryDrawRead
    cutoff_issue_no: str
    cutoff_draw_date: str
    sample_size: int
    same_period_count: int
    strategy_name: str
    strategy_params: dict[str, object]
    generated_sets: list[LotteryReplayGeneratedSetRead]
    baseline: LotteryReplayBaselineRead
    warnings: list[LotteryReplayWarningRead]
    leakage_check: LotteryReplayLeakageCheckRead
    same_period_deviation: LotterySamePeriodDeviationRead
    disclaimer: str


class LotterySensitivityResultRead(BaseModel):
    profile_name: str
    target_issue_no: str
    sample_window: int
    actual_sample_size: int
    same_period_sample_size: int
    evaluated_target_count: int
    positive_target_count: int
    positive_target_rate: float
    weights: dict[str, float]
    average_match_score: float
    average_score_delta: float
    best_match_key: str | None
    best_baseline_percentile: float
    best_front_numbers: list[int]
    best_back_numbers: list[int]
    generated_sets: list[LotteryReplayGeneratedSetRead]
    target_results: list[dict[str, object]]
    warning: str


class LotterySensitivitySummaryRead(BaseModel):
    best_profile_name: str | None
    best_sample_window: int | None
    positive_delta_count: int
    positive_delta_rate: float
    score_delta_spread: float
    stability_label: str
    overfit_warning: str


class LotterySensitivityRead(BaseModel):
    target_issue_no: str
    target_issue_nos: list[str]
    evaluated_target_count: int
    target_draw: LotteryDrawRead
    sets: int
    same_period_count: int
    sample_windows: list[int]
    profile_count: int
    combination_count: int
    baseline: LotteryReplayBaselineRead
    results: list[LotterySensitivityResultRead]
    summary: LotterySensitivitySummaryRead
    leakage_check: LotteryReplayLeakageCheckRead
    disclaimer: str


class LotterySavedCombinationCreate(BaseModel):
    label: str = Field(min_length=1, max_length=64)
    source: str = Field(default="manual", min_length=1, max_length=64)
    front_numbers: list[int] = Field(min_length=5, max_length=5)
    back_numbers: list[int] = Field(min_length=2, max_length=2)
    favorite: bool = False
    note: str = Field(default="", max_length=500)

    @field_validator("front_numbers")
    @classmethod
    def validate_front_numbers(cls, value: list[int]) -> list[int]:
        return _normalize_numbers(value=value, min_number=1, max_number=35, required_count=5)

    @field_validator("back_numbers")
    @classmethod
    def validate_back_numbers(cls, value: list[int]) -> list[int]:
        return _normalize_numbers(value=value, min_number=1, max_number=12, required_count=2)


class LotterySavedCombinationUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=64)
    source: str | None = Field(default=None, min_length=1, max_length=64)
    favorite: bool | None = None
    note: str | None = Field(default=None, max_length=500)


class LotterySavedCombinationRead(BaseModel):
    id: int
    game_code: str
    label: str
    source: str
    front_numbers: list[int] = Field(min_length=5, max_length=5)
    back_numbers: list[int] = Field(min_length=2, max_length=2)
    favorite: bool
    note: str
    created_at: str
    updated_at: str


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


class LotteryRandomnessDeviationRead(BaseModel):
    number: int
    count: int
    expected: float
    deviation: float


class LotteryEntropyRead(BaseModel):
    value: float
    max: float
    normalized: float


class LotteryRandomnessFrequencyRead(BaseModel):
    area: str
    sample_size: int
    total_observations: int
    chi_square: float
    degrees_of_freedom: int
    p_value: float
    p_value_method: str
    entropy: LotteryEntropyRead
    top_deviations: list[LotteryRandomnessDeviationRead]
    interpretation: str


class LotterySequenceSummaryRead(BaseModel):
    min: int | None
    max: int | None
    average: float | None
    stddev: float | None


class LotteryFrontGapSummaryRead(LotterySequenceSummaryRead):
    distribution: list[LotteryDistributionItemRead]


class LotteryAutocorrelationRead(BaseModel):
    lag: int
    value: float | None
    interpretation: str


class LotteryRandomnessDiagnosticsRead(BaseModel):
    sample_size: int
    requested_limit: int
    latest_issue_no: str | None
    earliest_issue_no: str | None
    front_frequency: LotteryRandomnessFrequencyRead
    back_frequency: LotteryRandomnessFrequencyRead
    front_sum: LotterySequenceSummaryRead
    front_sum_autocorrelation: LotteryAutocorrelationRead
    front_parity_distribution: list[LotteryDistributionItemRead]
    front_gap_summary: LotteryFrontGapSummaryRead
    notes: list[str]


def _normalize_numbers(
    *,
    value: list[int],
    min_number: int,
    max_number: int,
    required_count: int,
) -> list[int]:
    normalized = sorted(set(value))
    if len(normalized) != required_count:
        raise ValueError(f"Must provide {required_count} unique numbers.")
    if any(number < min_number or number > max_number for number in normalized):
        raise ValueError(f"Numbers must be between {min_number} and {max_number}.")
    return normalized
