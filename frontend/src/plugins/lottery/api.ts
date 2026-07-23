import { deleteApiData, getApiData, patchApiData, postApiData } from '@/api/client';

export interface PrizeTier {
  tier: number;
  tier_name: string;
  front_match_count: number;
  back_match_count: number;
  is_floating: boolean;
  base_prize_amount: string | null;
  addon_multiplier: string | null;
  description: string;
}

export interface LotteryRule {
  rule_code: string;
  rule_name: string;
  game_code: string;
  front: {
    count: number;
    min: number;
    max: number;
  };
  back: {
    count: number;
    min: number;
    max: number;
  };
  base_price: string;
  addon_price: string;
  addon_supported: boolean;
  official_url: string;
  prize_tiers: PrizeTier[];
}

export interface LotteryDraw {
  issue_no: string;
  draw_date: string;
  front_numbers: number[];
  back_numbers: number[];
  sales_amount: string | null;
  pool_amount: string | null;
  source_url: string | null;
}

export interface DrawPage {
  items: LotteryDraw[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
}

export interface LotteryDrawCoverage {
  total: number;
  latest_issue_no: string | null;
  latest_draw_date: string | null;
  earliest_issue_no: string | null;
  earliest_draw_date: string | null;
  start_year: number | null;
  end_year: number | null;
  year_span: number;
  status: string;
  status_label: string;
  description: string;
}

export interface LotterySyncRequest {
  sync_type: 'manual' | 'backfill';
  page: number;
  page_size: number;
  force: boolean;
}

export interface LotteryBackfillRequest {
  start_page: number;
  page_count: number;
  page_size: number;
  force: boolean;
}

export interface LotterySyncRun {
  run_id: number;
  game_code: string;
  source: string;
  sync_type: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  requested_page: number | null;
  requested_page_size: number | null;
  fetched_count: number;
  inserted_count: number;
  updated_count: number;
  skipped_count: number;
  failed_count: number;
  latest_issue_no: string | null;
  error_code: string | null;
  error_message: string | null;
  source_url: string | null;
  details: LotterySyncRunDetail[];
}

export interface LotterySyncRunDetail {
  issue_no: string;
  draw_date: string;
  action: 'inserted' | 'updated' | 'skipped' | 'failed' | string;
}

export interface SyncRunPage {
  items: LotterySyncRun[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
}

export interface LotteryBackfillRun {
  status: string;
  start_page: number;
  page_count: number;
  page_size: number;
  executed_pages: number;
  latest_issue_no: string | null;
  fetched_count: number;
  inserted_count: number;
  updated_count: number;
  skipped_count: number;
  failed_count: number;
  runs: LotterySyncRun[];
}

export interface LotteryBackfillJob {
  status: string;
  message: string;
  start_page: number;
  page_count: number;
  page_size: number;
  force: boolean;
}

export interface LotterySyncStatus {
  enabled: boolean;
  running: boolean;
  cron: string;
  timezone: string;
  page_size: number;
  next_run_at: string | null;
  latest_run: LotterySyncRun | null;
}

export interface LotteryNumberFrequency {
  number: number;
  count: number;
  missing: number;
  last_seen_issue_no: string | null;
}

export interface LotteryDrawMetric {
  issue_no: string;
  front_sum: number;
  front_span: number;
  front_parity_pattern: string;
  front_size_pattern: string;
  front_zone_pattern: string;
  front_route012_pattern: string;
  front_zone_counts: number[];
  front_route012_counts: number[];
  back_sum: number;
}

export interface LotteryOmissionTrendPoint {
  issue_no: string;
  draw_date: string;
  is_hit: boolean;
  missing: number;
}

export interface LotteryNumberOmission {
  area: 'front' | 'back';
  number: number;
  appearances: number;
  current_missing: number;
  max_missing: number;
  average_missing: number;
  last_seen_issue_no: string | null;
  last_seen_date: string | null;
  trend: LotteryOmissionTrendPoint[];
}

export interface LotteryNumberOmissionDetail extends LotteryNumberOmission {
  sample_size: number;
  requested_limit: number;
  hit_issues: Array<{
    issue_no: string;
    draw_date: string;
  }>;
}

export interface LotteryOmissionStatistics {
  sample_size: number;
  requested_limit: number;
  latest_issue_no: string | null;
  front: LotteryNumberOmission[];
  back: LotteryNumberOmission[];
}

export interface LotterySamePeriodItem {
  draw: LotteryDraw;
  front_matches: number[];
  back_matches: number[];
  front_match_count: number;
  back_match_count: number;
}

export interface LotterySamePeriodAnalysis {
  target: LotteryDraw;
  issue_suffix: string;
  requested_count: number;
  items: LotterySamePeriodItem[];
}

export interface LotteryRecommendationNumberDetail {
  number: number;
  score: number;
  same_period_hits: number;
  recent_frequency: number;
  current_missing: number;
  reasons: string[];
}

export interface LotteryRecommendationSet {
  rank: number;
  front_numbers: number[];
  back_numbers: number[];
  score: number;
  rationale: string[];
  front_sum: number;
  front_span: number;
  front_parity_pattern: string;
  front_zone_pattern: string;
  front_route012_pattern: string;
  front_details: LotteryRecommendationNumberDetail[];
  back_details: LotteryRecommendationNumberDetail[];
}

export interface LotteryRecommendationWeights {
  same_period: number;
  frequency: number;
  missing: number;
  structure: number;
}

export interface LotteryRecommendationAnalysis {
  target_issue_no: string;
  issue_suffix: string;
  sample_size: number;
  same_period_count: number;
  requested_sets: number;
  disclaimer: string;
  strategy_weights: LotteryRecommendationWeights;
  methodology: string[];
  same_period_repeated_front: LotteryRecommendationNumberDetail[];
  same_period_repeated_back: LotteryRecommendationNumberDetail[];
  recommendations: LotteryRecommendationSet[];
}

export interface LotterySimulationSet {
  rank: number;
  front_numbers: number[];
  back_numbers: number[];
  front_sum: number;
  front_span: number;
  front_parity_pattern: string;
  front_zone_pattern: string;
  front_route012_pattern: string;
}

export interface LotterySimulationFrequency {
  number: number;
  count: number;
  frequency: number;
  expected_probability: number;
  deviation: number;
}

export interface LotterySimulationAnalysis {
  simulations: number;
  requested_sets: number;
  seed: number | null;
  latest_issue_no: string;
  disclaimer: string;
  methodology: string[];
  theoretical: {
    front_probability: number;
    back_probability: number;
    jackpot_probability: string;
    jackpot_probability_decimal: number;
  };
  generated_sets: LotterySimulationSet[];
  front_frequency: LotterySimulationFrequency[];
  back_frequency: LotterySimulationFrequency[];
}

export interface LotteryDantuoRequest {
  front_dan: number[];
  front_tuo: number[];
  front_kill: number[];
  back_dan: number[];
  back_tuo: number[];
  back_kill: number[];
  addon: boolean;
  preview_limit: number;
}

export interface LotteryDantuoCombination {
  rank: number;
  front_numbers: number[];
  back_numbers: number[];
  front_sum: number;
  front_span: number;
  front_parity_pattern: string;
  front_zone_pattern: string;
  front_route012_pattern: string;
}

export interface LotteryDantuoAnalysis {
  disclaimer: string;
  addon: boolean;
  front_required: number;
  back_required: number;
  front_combination_count: number;
  back_combination_count: number;
  total_bets: number;
  base_cost: number;
  addon_cost: number;
  total_cost: number;
  front_dan: number[];
  front_tuo: number[];
  front_kill: number[];
  back_dan: number[];
  back_tuo: number[];
  back_kill: number[];
  available_front: number[];
  available_back: number[];
  preview_limit: number;
  preview: LotteryDantuoCombination[];
  warnings: string[];
  methodology: string[];
}

export interface LotteryBacktestRequest {
  front_numbers: number[];
  back_numbers: number[];
  addon: boolean;
  hit_limit: number;
}

export interface LotteryBacktestHit {
  issue_no: string;
  draw_date: string;
  draw_front_numbers: number[];
  draw_back_numbers: number[];
  front_matches: number[];
  back_matches: number[];
  front_match_count: number;
  back_match_count: number;
  match_key: string;
  prize_tier: number;
  tier_name: string;
  is_floating: boolean;
  base_prize_amount: number | null;
}

export interface LotteryBacktestDistribution {
  match_key: string;
  front_match_count: number;
  back_match_count: number;
  count: number;
  prize_tier: number | null;
  tier_name: string;
}

export interface LotteryBacktestAnalysis {
  disclaimer: string;
  front_numbers: number[];
  back_numbers: number[];
  addon: boolean;
  sample_size: number;
  earliest_issue_no: string;
  latest_issue_no: string;
  base_cost: number;
  addon_cost: number;
  total_cost: number;
  fixed_prize_return: number;
  floating_hit_count: number;
  net_fixed_result: number;
  hit_count: number;
  no_prize_count: number;
  highest_hit: LotteryBacktestHit | null;
  latest_hit: LotteryBacktestHit | null;
  hit_preview_limit: number;
  hits: LotteryBacktestHit[];
  distribution: LotteryBacktestDistribution[];
  methodology: string[];
}

export interface LotteryReplayStrategyRequest {
  same_period_weight: number;
  frequency_weight: number;
  missing_weight: number;
  structure_weight: number;
}

export interface LotteryReplayRequest {
  target_issue_no: string;
  sets: number;
  sample_limit: number;
  same_period_count: number;
  baseline_simulations: number;
  seed?: number | null;
  strategy: LotteryReplayStrategyRequest;
}

export interface LotteryReplayWarning {
  code: string;
  message: string;
}

export interface LotteryReplayLeakageCheck {
  passed: boolean;
  rule: string;
}

export interface LotteryReplayRange {
  earliest_issue_no: string | null;
  latest_issue_no: string | null;
  earliest_draw_date: string | null;
  latest_draw_date: string | null;
}

export interface LotterySamePeriodDeviationMetric {
  label: string;
  target_value: number;
  historical_average: number;
  deviation: number;
  level: string;
}

export interface LotterySamePeriodDeviationPattern {
  target_pattern: string;
  historical_top_pattern: string;
  historical_top_rate: number;
  target_pattern_rate: number;
  level: string;
}

export interface LotterySamePeriodDeviation {
  issue_suffix: string;
  sample_size: number;
  front_repeat: LotterySamePeriodDeviationMetric;
  back_repeat: LotterySamePeriodDeviationMetric;
  front_sum: LotterySamePeriodDeviationMetric;
  front_span: LotterySamePeriodDeviationMetric;
  front_zone: LotterySamePeriodDeviationPattern;
  front_route012: LotterySamePeriodDeviationPattern;
  notes: string[];
}

export interface LotteryReplayContext {
  target: LotteryDraw;
  cutoff: LotteryDraw | null;
  sample_size: number;
  requested_sample_limit: number;
  available_range: LotteryReplayRange;
  leakage_check: LotteryReplayLeakageCheck;
  warnings: LotteryReplayWarning[];
  same_period_deviation: LotterySamePeriodDeviation;
}

export interface LotteryReplayGeneratedSet extends LotteryRecommendationSet {
  front_matches: number[];
  back_matches: number[];
  front_match_count: number;
  back_match_count: number;
  match_key: string;
  prize_tier: number | null;
  baseline_percentile: number;
}

export interface LotteryReplayBaseline {
  simulations: number;
  seed: number | null;
  average_front_match: number;
  average_back_match: number;
  average_score: number;
  any_prize_rate: number;
  explanation: string;
}

export interface LotteryReplayRun {
  run_id: number;
  target_issue_no: string;
  target_draw: LotteryDraw;
  cutoff_issue_no: string;
  cutoff_draw_date: string;
  sample_size: number;
  same_period_count: number;
  strategy_name: string;
  strategy_params: Record<string, unknown>;
  generated_sets: LotteryReplayGeneratedSet[];
  baseline: LotteryReplayBaseline;
  warnings: LotteryReplayWarning[];
  leakage_check: LotteryReplayLeakageCheck;
  same_period_deviation: LotterySamePeriodDeviation;
  disclaimer: string;
}

export interface LotterySensitivityWeightProfile extends LotteryReplayStrategyRequest {
  name: string;
}

export interface LotterySensitivityRequest {
  target_issue_no: string;
  target_count: number;
  sets: number;
  same_period_count: number;
  sample_windows: number[];
  weight_profiles: LotterySensitivityWeightProfile[];
  baseline_simulations: number;
  seed?: number | null;
}

export interface LotterySensitivityResult {
  profile_name: string;
  target_issue_no: string;
  sample_window: number;
  actual_sample_size: number;
  same_period_sample_size: number;
  evaluated_target_count: number;
  positive_target_count: number;
  positive_target_rate: number;
  weights: Record<string, number>;
  average_match_score: number;
  average_score_delta: number;
  best_match_key: string | null;
  best_baseline_percentile: number;
  best_front_numbers: number[];
  best_back_numbers: number[];
  generated_sets: LotteryReplayGeneratedSet[];
  target_results: Array<Record<string, unknown>>;
  warning: string;
}

export interface LotterySensitivitySummary {
  best_profile_name: string | null;
  best_sample_window: number | null;
  positive_delta_count: number;
  positive_delta_rate: number;
  score_delta_spread: number;
  stability_label: string;
  overfit_warning: string;
}

export interface LotterySensitivityAnalysis {
  target_issue_no: string;
  target_issue_nos: string[];
  evaluated_target_count: number;
  target_draw: LotteryDraw;
  sets: number;
  same_period_count: number;
  sample_windows: number[];
  profile_count: number;
  combination_count: number;
  baseline: LotteryReplayBaseline;
  results: LotterySensitivityResult[];
  summary: LotterySensitivitySummary;
  leakage_check: LotteryReplayLeakageCheck;
  disclaimer: string;
}

export interface LotterySavedCombination {
  id: number;
  game_code: string;
  label: string;
  source: string;
  front_numbers: number[];
  back_numbers: number[];
  favorite: boolean;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface LotterySavedCombinationCreate {
  label: string;
  source: string;
  front_numbers: number[];
  back_numbers: number[];
  favorite: boolean;
  note: string;
}

export interface LotterySavedCombinationUpdate {
  label?: string;
  source?: string;
  favorite?: boolean;
  note?: string;
}

export interface LotteryBasicStatistics {
  sample_size: number;
  requested_limit: number;
  latest_issue_no: string | null;
  front_frequency: LotteryNumberFrequency[];
  back_frequency: LotteryNumberFrequency[];
  hot_numbers: {
    front: LotteryNumberFrequency[];
    back: LotteryNumberFrequency[];
  };
  cold_numbers: {
    front: LotteryNumberFrequency[];
    back: LotteryNumberFrequency[];
  };
  sum: {
    min: number | null;
    max: number | null;
    average: number | null;
  };
  span: {
    min: number | null;
    max: number | null;
    average: number | null;
  };
  parity: Array<{ pattern: string; count: number }>;
  size: Array<{ pattern: string; count: number }>;
  zone: Array<{ pattern: string; count: number }>;
  route012: Array<{ pattern: string; count: number }>;
  recent_metrics: LotteryDrawMetric[];
  trend: LotteryDrawMetric[];
}

export interface LotteryRandomnessDeviation {
  number: number;
  count: number;
  expected: number;
  deviation: number;
}

export interface LotteryEntropy {
  value: number;
  max: number;
  normalized: number;
}

export interface LotteryRandomnessFrequency {
  area: string;
  sample_size: number;
  total_observations: number;
  chi_square: number;
  degrees_of_freedom: number;
  p_value: number;
  p_value_method: string;
  entropy: LotteryEntropy;
  top_deviations: LotteryRandomnessDeviation[];
  interpretation: string;
}

export interface LotterySequenceSummary {
  min: number | null;
  max: number | null;
  average: number | null;
  stddev: number | null;
}

export interface LotteryFrontGapSummary extends LotterySequenceSummary {
  distribution: Array<{ pattern: string; count: number }>;
}

export interface LotteryAutocorrelation {
  lag: number;
  value: number | null;
  interpretation: string;
}

export interface LotteryRandomnessDiagnostics {
  sample_size: number;
  requested_limit: number;
  latest_issue_no: string | null;
  earliest_issue_no: string | null;
  front_frequency: LotteryRandomnessFrequency;
  back_frequency: LotteryRandomnessFrequency;
  front_sum: LotterySequenceSummary;
  front_sum_autocorrelation: LotteryAutocorrelation;
  front_parity_distribution: Array<{ pattern: string; count: number }>;
  front_gap_summary: LotteryFrontGapSummary;
  notes: string[];
}

export function fetchCurrentRule(): Promise<LotteryRule> {
  return getApiData<LotteryRule>('/lottery/dlt/rules/current');
}

export function fetchDraws(page = 1, pageSize = 20): Promise<DrawPage> {
  return getApiData<DrawPage>(`/lottery/dlt/draws?page=${page}&page_size=${pageSize}`);
}

export function fetchDrawCoverage(): Promise<LotteryDrawCoverage> {
  return getApiData<LotteryDrawCoverage>('/lottery/dlt/draws/coverage');
}

export function fetchDisclaimer(): Promise<{ disclaimer: string }> {
  return getApiData<{ disclaimer: string }>('/lottery/dlt/disclaimer');
}

export function fetchLatestSyncRun(): Promise<LotterySyncRun> {
  return getApiData<LotterySyncRun>('/lottery/dlt/sync/latest');
}

export function fetchSyncRuns(page = 1, pageSize = 10): Promise<SyncRunPage> {
  return getApiData<SyncRunPage>(`/lottery/dlt/sync/runs?page=${page}&page_size=${pageSize}`);
}

export function fetchSyncStatus(): Promise<LotterySyncStatus> {
  return getApiData<LotterySyncStatus>('/lottery/dlt/sync/status');
}

export function fetchBasicStatistics(limit = 100): Promise<LotteryBasicStatistics> {
  return getApiData<LotteryBasicStatistics>(`/lottery/dlt/statistics/basic?limit=${limit}`);
}

export function fetchOmissionStatistics(limit = 100): Promise<LotteryOmissionStatistics> {
  return getApiData<LotteryOmissionStatistics>(`/lottery/dlt/statistics/omissions?limit=${limit}`);
}

export function fetchRandomnessDiagnostics(limit = 500): Promise<LotteryRandomnessDiagnostics> {
  return getApiData<LotteryRandomnessDiagnostics>(
    `/lottery/dlt/statistics/randomness?limit=${limit}`,
  );
}

export function fetchNumberOmissionDetail(
  area: 'front' | 'back',
  number: number,
  limit = 200,
): Promise<LotteryNumberOmissionDetail> {
  return getApiData<LotteryNumberOmissionDetail>(
    `/lottery/dlt/numbers/${area}/${number}/omission?limit=${limit}`,
  );
}

export function fetchSamePeriodAnalysis(
  issueNo?: string,
  count = 5,
): Promise<LotterySamePeriodAnalysis> {
  const params = new URLSearchParams({ count: String(count) });
  if (issueNo) params.set('issue_no', issueNo);
  return getApiData<LotterySamePeriodAnalysis>(
    `/lottery/dlt/analysis/same-period?${params.toString()}`,
  );
}

export function fetchRecommendationAnalysis(
  issueNo?: string,
  sets = 5,
  samePeriodCount = 10,
  sampleLimit = 200,
  weights?: LotteryRecommendationWeights,
): Promise<LotteryRecommendationAnalysis> {
  const params = new URLSearchParams({
    sets: String(sets),
    same_period_count: String(samePeriodCount),
    sample_limit: String(sampleLimit),
  });
  if (weights) {
    params.set('same_period_weight', String(weights.same_period));
    params.set('frequency_weight', String(weights.frequency));
    params.set('missing_weight', String(weights.missing));
    params.set('structure_weight', String(weights.structure));
  }
  if (issueNo) params.set('issue_no', issueNo);
  return getApiData<LotteryRecommendationAnalysis>(
    `/lottery/dlt/analysis/recommendations?${params.toString()}`,
  );
}

export function fetchSimulationAnalysis(
  simulations = 10000,
  sets = 5,
  seed?: number,
): Promise<LotterySimulationAnalysis> {
  const params = new URLSearchParams({
    simulations: String(simulations),
    sets: String(sets),
  });
  if (seed !== undefined) params.set('seed', String(seed));
  return getApiData<LotterySimulationAnalysis>(
    `/lottery/dlt/analysis/simulation?${params.toString()}`,
  );
}

export function analyzeDantuo(payload: LotteryDantuoRequest): Promise<LotteryDantuoAnalysis> {
  return postApiData<LotteryDantuoAnalysis, LotteryDantuoRequest>(
    '/lottery/dlt/analysis/dantuo',
    payload,
  );
}

export function backtestNumbers(
  payload: LotteryBacktestRequest,
): Promise<LotteryBacktestAnalysis> {
  return postApiData<LotteryBacktestAnalysis, LotteryBacktestRequest>(
    '/lottery/dlt/analysis/backtest',
    payload,
  );
}

export function fetchReplayContext(
  targetIssueNo: string,
  sampleLimit = 500,
): Promise<LotteryReplayContext> {
  const params = new URLSearchParams({
    target_issue_no: targetIssueNo,
    sample_limit: String(sampleLimit),
  });
  return getApiData<LotteryReplayContext>(
    `/lottery/dlt/analysis/replay/context?${params.toString()}`,
  );
}

export function runReplay(payload: LotteryReplayRequest): Promise<LotteryReplayRun> {
  return postApiData<LotteryReplayRun, LotteryReplayRequest>(
    '/lottery/dlt/analysis/replay',
    payload,
  );
}

export function analyzeSensitivity(
  payload: LotterySensitivityRequest,
): Promise<LotterySensitivityAnalysis> {
  return postApiData<LotterySensitivityAnalysis, LotterySensitivityRequest>(
    '/lottery/dlt/analysis/replay/sensitivity',
    payload,
    { timeout: 60000 },
  );
}

export function fetchSavedCombinations(): Promise<LotterySavedCombination[]> {
  return getApiData<LotterySavedCombination[]>('/lottery/dlt/combinations');
}

export function saveCombination(
  payload: LotterySavedCombinationCreate,
): Promise<LotterySavedCombination> {
  return postApiData<LotterySavedCombination, LotterySavedCombinationCreate>(
    '/lottery/dlt/combinations',
    payload,
  );
}

export function updateSavedCombination(
  id: number,
  payload: LotterySavedCombinationUpdate,
): Promise<LotterySavedCombination> {
  return patchApiData<LotterySavedCombination, LotterySavedCombinationUpdate>(
    `/lottery/dlt/combinations/${id}`,
    payload,
  );
}

export function deleteSavedCombination(id: number): Promise<{ deleted: boolean; id: number }> {
  return deleteApiData<{ deleted: boolean; id: number }>(`/lottery/dlt/combinations/${id}`);
}

export function triggerDrawSync(payload: LotterySyncRequest): Promise<LotterySyncRun> {
  return postApiData<LotterySyncRun, LotterySyncRequest>('/lottery/dlt/sync', payload);
}

export function triggerBackfill(payload: LotteryBackfillRequest): Promise<LotteryBackfillRun> {
  return postApiData<LotteryBackfillRun, LotteryBackfillRequest>(
    '/lottery/dlt/sync/backfill',
    payload,
  );
}

export function startBackfill(payload: LotteryBackfillRequest): Promise<LotteryBackfillJob> {
  return postApiData<LotteryBackfillJob, LotteryBackfillRequest>(
    '/lottery/dlt/sync/backfill/start',
    payload,
  );
}
