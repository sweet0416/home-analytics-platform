import { apiClient, getApiData, postApiData, type ApiResponse } from '@/api/client';

export interface FundModule {
  code: string;
  name: string;
  description: string;
  status: string;
}

export interface FundStatus {
  plugin: string;
  display_name: string;
  version: string;
  status: string;
  description: string;
  modules: FundModule[];
  data_source_status: string;
  storage_status: string;
  next_step: string;
}

export interface FundNavSchedulerStatus {
  enabled: boolean;
  running: boolean;
  cron: string;
  timezone: string;
  notification_enabled: boolean;
  notification_channel: 'all' | 'bark' | 'wecom' | 'whatsapp' | 'custom_webhook';
  next_run_at: string | null;
  last_run: {
    id: number | null;
    trigger_type: string;
    status: 'succeeded' | 'partial' | 'failed';
    started_at: string;
    finished_at: string;
    total: number;
    succeeded: number;
    failed: number;
    updated: number;
    skipped: boolean;
    message: string;
  } | null;
}

export interface FundPosition {
  id: number;
  fund_id: number;
  fund_code: string;
  fund_name: string;
  fund_type: string;
  account_name: string;
  shares: string;
  cost_price: string;
  total_cost: string;
  current_nav: string | null;
  target_weight: string | null;
  current_value: string | null;
  unrealized_profit: string | null;
  unrealized_return_rate: string | null;
  opened_at: string | null;
  tags: string;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface FundWatchlistItem {
  id: number;
  fund_id: number;
  fund_code: string;
  fund_name: string;
  fund_type: string;
  priority: number;
  status: string;
  watch_reason: string;
  risk_level: string;
  target_position: string;
  tags: string;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface FundWatchlistCreate {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  priority: number;
  status: string;
  watch_reason: string;
  risk_level: string;
  target_position: string;
  tags: string;
  note: string;
}

export interface FundNavRecord {
  id: number;
  fund_id: number;
  fund_code: string;
  fund_name: string;
  fund_type: string;
  nav_date: string;
  unit_nav: string;
  accumulated_nav: string | null;
  source: string;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface FundNavRisk {
  fund_code: string;
  fund_name: string;
  sample_count: number;
  return_observation_count: number;
  start_date: string | null;
  end_date: string | null;
  cumulative_return: string | null;
  annualized_volatility: string | null;
  maximum_drawdown: string | null;
  drawdown_peak_date: string | null;
  drawdown_trough_date: string | null;
  positive_day_ratio: string | null;
  calculation_available: boolean;
  warning: string;
}

export interface FundNavRecordCreate {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  nav_date: string;
  unit_nav: number;
  accumulated_nav?: number | null;
  source: string;
  note: string;
}

export interface FundNavSyncLatestRequest {
  fund_code: string;
  fund_type: string;
}

export interface FundNavHistorySyncRequest extends FundNavSyncLatestRequest {
  limit: number;
}

export interface FundNavHistorySyncResult {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  synced_count: number;
  earliest_date: string;
  latest_date: string;
  source: string;
}

export interface FundHoldingHistorySyncItem {
  fund_code: string;
  fund_name: string;
  status: 'succeeded' | 'failed';
  synced_count: number;
  earliest_date: string | null;
  latest_date: string | null;
  source: string;
  message: string;
}

export interface FundHoldingHistorySyncResult {
  total: number;
  succeeded: number;
  failed: number;
  synced_count: number;
  items: FundHoldingHistorySyncItem[];
}

export interface FundLatestNav {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  nav_date: string;
  unit_nav: string;
  accumulated_nav: string | null;
  source: string;
  source_url: string;
}

export interface FundWatchlistNavSyncItem {
  fund_code: string;
  fund_name: string;
  status: 'succeeded' | 'failed';
  nav_date: string | null;
  unit_nav: string | null;
  message: string;
}

export interface FundWatchlistNavSyncResult {
  total: number;
  succeeded: number;
  failed: number;
  items: FundWatchlistNavSyncItem[];
}

export interface FundPositionCreate {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  account_name: string;
  shares: number;
  cost_price: number;
  total_cost?: number | null;
  current_nav?: number | null;
  target_weight?: number | null;
  opened_at?: string | null;
  tags: string;
  note: string;
}

export type FundTransactionType = 'buy' | 'sell' | 'dividend' | 'fee';

export interface FundTransactionCreate {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  account_name: string;
  transaction_type: FundTransactionType;
  trade_date: string;
  shares?: number | null;
  unit_price?: number | null;
  amount?: number | null;
  fee: number;
  note: string;
}

export interface FundTransaction {
  id: number;
  fund_id: number;
  fund_code: string;
  fund_name: string;
  fund_type: string;
  account_name: string;
  transaction_type: FundTransactionType;
  trade_date: string;
  shares: string | null;
  unit_price: string | null;
  amount: string;
  fee: string;
  cash_flow: string;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface FundTransactionSummary {
  transaction_count: number;
  total_buy: string;
  total_sell: string;
  total_dividend: string;
  total_fee: string;
  net_cash_flow: string;
}

export interface FundCashFlowPerformance {
  transaction_count: number;
  position_count: number;
  valuation_complete: boolean;
  calculation_available: boolean;
  invested_cash: string;
  recovered_cash: string;
  current_value: string | null;
  net_profit: string | null;
  simple_return_rate: string | null;
  earliest_trade_date: string | null;
  latest_trade_date: string | null;
  calculation_basis: string;
  warning: string;
}

export interface FundHoldingSummary {
  position_count: number;
  fund_count: number;
  total_cost: string;
  current_value: string | null;
  unrealized_profit: string | null;
  unrealized_return_rate: string | null;
  valued_position_count: number;
  fund_types: string[];
  accounts: string[];
}

export interface FundAllocationGroup {
  label: string;
  amount: string;
  weight: string;
  position_count: number;
}

export interface FundAllocationHolding {
  position_id: number;
  fund_code: string;
  fund_name: string;
  fund_type: string;
  account_name: string;
  amount: string;
  weight: string;
  target_weight: string | null;
  weight_deviation: string | null;
  target_amount: string | null;
  calibration_amount: string | null;
  valuation_basis: 'current_nav' | 'cost';
}

export interface FundAllocation {
  position_count: number;
  total_amount: string;
  current_nav_count: number;
  cost_fallback_count: number;
  top_holding_weight: string | null;
  concentration_hhi: string | null;
  configured_target_count: number;
  target_weight_total: string;
  target_configuration_complete: boolean;
  target_warning: string;
  by_fund_type: FundAllocationGroup[];
  by_account: FundAllocationGroup[];
  holdings: FundAllocationHolding[];
}

export interface FundHoldingRiskItem {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  position_count: number;
  allocation_weight: string;
  sample_count: number;
  start_date: string | null;
  end_date: string | null;
  cumulative_return: string | null;
  annualized_volatility: string | null;
  maximum_drawdown: string | null;
  positive_day_ratio: string | null;
  calculation_available: boolean;
}

export interface FundHoldingRisk {
  fund_count: number;
  analyzed_fund_count: number;
  sample_limit: number;
  items: FundHoldingRiskItem[];
  warning: string;
}

export interface FundPortfolioMember {
  fund_code: string;
  fund_name: string;
  allocation_weight: string;
  sample_count: number;
}

export interface FundPortfolioPerformancePoint {
  nav_date: string;
  portfolio_index: string;
  equal_weight_index: string;
  drawdown: string;
}

export interface FundPortfolioPerformance {
  fund_count: number;
  included_fund_count: number;
  sample_limit: number;
  sample_count: number;
  start_date: string | null;
  end_date: string | null;
  valuation_complete: boolean;
  cumulative_return: string | null;
  equal_weight_return: string | null;
  annualized_volatility: string | null;
  maximum_drawdown: string | null;
  calculation_available: boolean;
  members: FundPortfolioMember[];
  excluded_fund_codes: string[];
  points: FundPortfolioPerformancePoint[];
  warning: string;
}

export interface FundPortfolioBenchmarkPoint {
  nav_date: string;
  portfolio_index: string;
  benchmark_index: string;
  relative_return: string;
}

export interface FundPortfolioBenchmark {
  benchmark_code: string;
  benchmark_name: string;
  sample_limit: number;
  sample_count: number;
  start_date: string | null;
  end_date: string | null;
  portfolio_return: string | null;
  benchmark_return: string | null;
  relative_return: string | null;
  tracking_error: string | null;
  information_ratio: string | null;
  return_correlation: string | null;
  calculation_available: boolean;
  points: FundPortfolioBenchmarkPoint[];
  warning: string;
}

export interface FundCorrelationMember {
  fund_code: string;
  fund_name: string;
  allocation_weight: string;
  sample_count: number;
}

export interface FundCorrelationPair {
  first_fund_code: string;
  second_fund_code: string;
  observation_count: number;
  correlation: string | null;
}

export interface FundHoldingCorrelation {
  fund_count: number;
  sample_limit: number;
  calculated_pair_count: number;
  total_pair_count: number;
  average_pairwise_correlation: string | null;
  high_correlation_pair_count: number;
  members: FundCorrelationMember[];
  pairs: FundCorrelationPair[];
  warning: string;
}

export interface FundRiskContributionItem {
  fund_code: string;
  fund_name: string;
  allocation_weight: string;
  annualized_volatility: string;
  component_volatility: string;
  contribution_ratio: string;
}

export interface FundRiskContribution {
  fund_count: number;
  included_fund_count: number;
  sample_limit: number;
  sample_count: number;
  start_date: string | null;
  end_date: string | null;
  portfolio_annualized_volatility: string | null;
  weighted_standalone_volatility: string | null;
  diversification_ratio: string | null;
  calculation_available: boolean;
  items: FundRiskContributionItem[];
  excluded_fund_codes: string[];
  warning: string;
}

export interface FundDisclosureSyncResult {
  total: number;
  succeeded: number;
  failed: number;
  items: Array<{
    fund_code: string;
    fund_name: string;
    status: 'synced' | 'failed';
    report_date: string | null;
    holding_count: number;
    message: string;
  }>;
}

export interface FundTargetLinkInput {
  parent_fund_code: string;
  target_fund_code: string;
  target_fund_name: string;
  target_allocation_ratio: number;
  report_date: string;
  source_url: string;
}

export interface FundTargetLink {
  parent_fund_code: string;
  target_fund_code: string;
  target_fund_name: string;
  target_allocation_ratio: string;
  report_date: string;
  source_url: string;
  origin: 'environment' | 'database';
}

export interface FundLookthroughAsset {
  asset_code: string;
  asset_name: string;
  portfolio_weight: string;
  fund_count: number;
}

export interface FundLookthroughSnapshot {
  fund_code: string;
  fund_name: string;
  allocation_weight: string;
  covered_weight: string;
  report_date: string | null;
  report_period: string | null;
  age_days: number | null;
  holding_count: number;
  status: 'current' | 'stale' | 'missing';
  source_mode: 'direct' | 'target_etf' | 'none';
  target_fund_code: string | null;
  target_fund_name: string | null;
  target_allocation_ratio: string | null;
  relation_report_date: string | null;
}

export interface FundLookthrough {
  as_of_date: string;
  stale_after_days: number;
  fund_count: number;
  current_disclosure_count: number;
  coverage_weight: string;
  disclosed_weight: string;
  assets: FundLookthroughAsset[];
  snapshots: FundLookthroughSnapshot[];
  warning: string;
}

export interface FundWatchlistSummary {
  item_count: number;
  fund_count: number;
  high_priority_count: number;
  statuses: string[];
  risk_levels: string[];
}

export interface FundNavSummary {
  record_count: number;
  fund_count: number;
  latest_nav_date: string | null;
  sources: string[];
}

export interface FundNavFreshnessItem {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  account_names: string[];
  latest_nav_date: string | null;
  business_day_age: number | null;
  allowed_business_days: number;
  source: string | null;
  status: 'fresh' | 'stale' | 'missing';
}

export interface FundNavFreshness {
  as_of_date: string;
  stale_after_business_days: number;
  qdii_stale_after_business_days: number;
  position_count: number;
  fund_count: number;
  fresh_count: number;
  stale_count: number;
  missing_count: number;
  oldest_nav_date: string | null;
  items: FundNavFreshnessItem[];
}

export interface FundProfileSyncItem {
  fund_code: string;
  fund_name: string;
  previous_type: string;
  detected_type: string | null;
  current_type: string;
  status: 'updated' | 'unchanged' | 'failed';
  message: string;
}

export interface FundProfileSync {
  total: number;
  updated: number;
  unchanged: number;
  failed: number;
  items: FundProfileSyncItem[];
}

export interface FundDailyAlert {
  code: string;
  level: 'info' | 'warning';
  message: string;
}

export interface FundDailyDataQuality {
  level: 'complete' | 'partial' | 'insufficient';
  position_count: number;
  valued_position_count: number;
  latest_nav_date: string | null;
  nav_age_days: number | null;
  risk_fund_count: number;
  risk_covered_fund_count: number;
  risk_sample_count: number;
  target_configured_count: number;
  target_configuration_complete: boolean;
  target_weight_total: string;
  warnings: string[];
}

export interface FundDailyFact {
  code: string;
  category: 'performance' | 'risk' | 'allocation' | 'data_quality';
  label: string;
  value: string;
  unit: string;
  sample_scope: string;
  severity: 'info' | 'warning';
}

export interface FundDailyAnalysisContext {
  contract_version: 'fund-daily-context.v1';
  report_date: string;
  data_quality: FundDailyDataQuality;
  facts: FundDailyFact[];
  disclaimers: string[];
}

export interface FundDailyReport {
  report_date: string;
  generated_at: string;
  holding_summary: FundHoldingSummary;
  allocation: FundAllocation;
  holding_risk: FundHoldingRisk;
  watchlist_summary: FundWatchlistSummary;
  nav_summary: FundNavSummary;
  transaction_summary: FundTransactionSummary;
  valuation_complete: boolean;
  nav_age_days: number | null;
  alerts: FundDailyAlert[];
  analysis_context: FundDailyAnalysisContext;
}

export interface FundDailyPushResult {
  requested_channel: 'all' | 'bark' | 'wecom' | 'whatsapp' | 'custom_webhook';
  results: Array<{
    channel: 'all' | 'bark' | 'wecom' | 'whatsapp' | 'custom_webhook';
    status: 'sent' | 'skipped' | 'failed';
    message: string;
    sent_at: string | null;
    provider_message_id: string | null;
  }>;
}

export function fetchFundStatus(): Promise<FundStatus> {
  return getApiData<FundStatus>('/fund/status');
}

export function fetchFundNavSchedulerStatus(): Promise<FundNavSchedulerStatus> {
  return getApiData<FundNavSchedulerStatus>('/fund/nav-scheduler/status');
}

export function fetchFundPositions(): Promise<FundPosition[]> {
  return getApiData<FundPosition[]>('/fund/positions');
}

export function fetchFundNavFreshness(
  staleAfterBusinessDays = 2,
  qdiiStaleAfterBusinessDays = 4,
): Promise<FundNavFreshness> {
  return getApiData<FundNavFreshness>(
    `/fund/holdings/nav-freshness?stale_after_business_days=${staleAfterBusinessDays}`
      + `&qdii_stale_after_business_days=${qdiiStaleAfterBusinessDays}`,
  );
}

export function syncHeldFundProfiles(): Promise<FundProfileSync> {
  return postApiData<FundProfileSync, Record<string, never>>(
    '/fund/holdings/sync-profiles',
    {},
  );
}

export function createFundPosition(payload: FundPositionCreate): Promise<FundPosition> {
  return postApiData<FundPosition, FundPositionCreate>('/fund/positions', payload);
}

export function fetchFundTransactions(limit = 100): Promise<FundTransaction[]> {
  return getApiData<FundTransaction[]>(`/fund/transactions?limit=${limit}`);
}

export function createFundTransaction(
  payload: FundTransactionCreate,
): Promise<FundTransaction> {
  return postApiData<FundTransaction, FundTransactionCreate>(
    '/fund/transactions',
    payload,
  );
}

export function fetchFundTransactionSummary(): Promise<FundTransactionSummary> {
  return getApiData<FundTransactionSummary>('/fund/transactions/summary');
}

export function fetchFundCashFlowPerformance(): Promise<FundCashFlowPerformance> {
  return getApiData<FundCashFlowPerformance>('/fund/performance/cash-flow');
}

export async function deleteFundTransaction(
  transactionId: number,
): Promise<{ deleted: boolean; id: number }> {
  const response = await apiClient.delete<ApiResponse<{ deleted: boolean; id: number }>>(
    `/fund/transactions/${transactionId}`,
  );
  return response.data.data;
}

export function fetchFundWatchlist(): Promise<FundWatchlistItem[]> {
  return getApiData<FundWatchlistItem[]>('/fund/watchlist');
}

export function createFundWatchlistItem(
  payload: FundWatchlistCreate,
): Promise<FundWatchlistItem> {
  return postApiData<FundWatchlistItem, FundWatchlistCreate>('/fund/watchlist', payload);
}

export function fetchFundNavRecords(limit = 50): Promise<FundNavRecord[]> {
  return getApiData<FundNavRecord[]>(`/fund/nav-records?limit=${limit}`);
}

export function createFundNavRecord(payload: FundNavRecordCreate): Promise<FundNavRecord> {
  return postApiData<FundNavRecord, FundNavRecordCreate>('/fund/nav-records', payload);
}

export function syncLatestFundNav(payload: FundNavSyncLatestRequest): Promise<FundNavRecord> {
  return postApiData<FundNavRecord, FundNavSyncLatestRequest>('/fund/nav-records/sync-latest', payload);
}

export function fetchFundNavHistory(fundCode: string, limit = 365): Promise<FundNavRecord[]> {
  const query = new URLSearchParams({
    fund_code: fundCode,
    limit: String(limit),
  });
  return getApiData<FundNavRecord[]>(`/fund/nav-records/history?${query.toString()}`);
}

export function fetchFundNavRisk(fundCode: string, limit = 365): Promise<FundNavRisk> {
  const query = new URLSearchParams({
    fund_code: fundCode,
    limit: String(limit),
  });
  return getApiData<FundNavRisk>(`/fund/nav-records/risk?${query.toString()}`);
}

export function syncFundNavHistory(
  payload: FundNavHistorySyncRequest,
): Promise<FundNavHistorySyncResult> {
  return postApiData<FundNavHistorySyncResult, FundNavHistorySyncRequest>(
    '/fund/nav-records/sync-history',
    payload,
    { timeout: 120000 },
  );
}

export function lookupLatestFundNav(payload: FundNavSyncLatestRequest): Promise<FundLatestNav> {
  return postApiData<FundLatestNav, FundNavSyncLatestRequest>('/fund/lookup/latest-nav', payload);
}

export function syncFundWatchlistNavs(): Promise<FundWatchlistNavSyncResult> {
  return postApiData<FundWatchlistNavSyncResult, Record<string, never>>(
    '/fund/watchlist/sync-nav',
    {},
    { timeout: 120000 },
  );
}

export async function deleteFundNavRecord(
  recordId: number,
): Promise<{ deleted: boolean; id: number }> {
  const response = await apiClient.delete<ApiResponse<{ deleted: boolean; id: number }>>(
    `/fund/nav-records/${recordId}`,
  );
  return response.data.data;
}

export async function updateFundWatchlistItem(
  itemId: number,
  payload: FundWatchlistCreate,
): Promise<FundWatchlistItem> {
  const response = await apiClient.put<ApiResponse<FundWatchlistItem>>(
    `/fund/watchlist/${itemId}`,
    payload,
  );
  return response.data.data;
}

export async function deleteFundWatchlistItem(
  itemId: number,
): Promise<{ deleted: boolean; id: number }> {
  const response = await apiClient.delete<ApiResponse<{ deleted: boolean; id: number }>>(
    `/fund/watchlist/${itemId}`,
  );
  return response.data.data;
}

export async function updateFundPosition(
  positionId: number,
  payload: FundPositionCreate,
): Promise<FundPosition> {
  const response = await apiClient.put<ApiResponse<FundPosition>>(
    `/fund/positions/${positionId}`,
    payload,
  );
  return response.data.data;
}

export async function deleteFundPosition(positionId: number): Promise<{ deleted: boolean; id: number }> {
  const response = await apiClient.delete<ApiResponse<{ deleted: boolean; id: number }>>(
    `/fund/positions/${positionId}`,
  );
  return response.data.data;
}

export function fetchFundHoldingSummary(): Promise<FundHoldingSummary> {
  return getApiData<FundHoldingSummary>('/fund/holdings/summary');
}

export function fetchFundAllocation(): Promise<FundAllocation> {
  return getApiData<FundAllocation>('/fund/holdings/allocation');
}

export function fetchFundHoldingRisk(limit = 365): Promise<FundHoldingRisk> {
  return getApiData<FundHoldingRisk>(`/fund/holdings/risk?limit=${limit}`);
}

export function fetchFundPortfolioPerformance(
  limit = 365,
): Promise<FundPortfolioPerformance> {
  return getApiData<FundPortfolioPerformance>(
    `/fund/holdings/performance?limit=${limit}`,
  );
}

export function fetchFundPortfolioBenchmark(
  benchmarkCode: string,
  limit = 365,
): Promise<FundPortfolioBenchmark> {
  const query = new URLSearchParams({
    benchmark_code: benchmarkCode,
    limit: String(limit),
  });
  return getApiData<FundPortfolioBenchmark>(
    `/fund/holdings/benchmark?${query.toString()}`,
  );
}

export function fetchFundHoldingCorrelation(
  limit = 365,
): Promise<FundHoldingCorrelation> {
  return getApiData<FundHoldingCorrelation>(
    `/fund/holdings/correlation?limit=${limit}`,
  );
}

export function fetchFundRiskContribution(
  limit = 365,
): Promise<FundRiskContribution> {
  return getApiData<FundRiskContribution>(
    `/fund/holdings/risk-contribution?limit=${limit}`,
  );
}

export function fetchFundLookthrough(
  staleAfterDays = 180,
): Promise<FundLookthrough> {
  return getApiData<FundLookthrough>(
    `/fund/holdings/lookthrough?stale_after_days=${staleAfterDays}`,
  );
}

export function syncFundLookthrough(): Promise<FundDisclosureSyncResult> {
  return postApiData<FundDisclosureSyncResult, Record<string, never>>(
    '/fund/holdings/lookthrough/sync',
    {},
    { timeout: 120000 },
  );
}

export function fetchFundTargetLinks(): Promise<FundTargetLink[]> {
  return getApiData<FundTargetLink[]>('/fund/holdings/lookthrough/target-links');
}

export function saveFundTargetLink(
  payload: FundTargetLinkInput,
): Promise<FundTargetLink> {
  return postApiData<FundTargetLink, FundTargetLinkInput>(
    '/fund/holdings/lookthrough/target-links',
    payload,
  );
}

export async function deleteFundTargetLink(
  parentFundCode: string,
): Promise<{ deleted: boolean; parent_fund_code: string }> {
  const response = await apiClient.delete<
    ApiResponse<{ deleted: boolean; parent_fund_code: string }>
  >(`/fund/holdings/lookthrough/target-links/${parentFundCode}`);
  return response.data.data;
}

export function syncFundHoldingHistory(limit = 365): Promise<FundHoldingHistorySyncResult> {
  return postApiData<FundHoldingHistorySyncResult, { limit: number }>(
    '/fund/holdings/sync-history',
    { limit },
    { timeout: 120000 },
  );
}

export function fetchFundWatchlistSummary(): Promise<FundWatchlistSummary> {
  return getApiData<FundWatchlistSummary>('/fund/watchlist/summary');
}

export function fetchFundNavSummary(): Promise<FundNavSummary> {
  return getApiData<FundNavSummary>('/fund/nav-records/summary');
}

export function fetchFundDailyReport(): Promise<FundDailyReport> {
  return getApiData<FundDailyReport>('/fund/reports/daily');
}

export function pushFundDailyReport(): Promise<FundDailyPushResult> {
  return postApiData<FundDailyPushResult, { channel: 'bark' }>(
    '/fund/reports/daily/push',
    { channel: 'bark' },
  );
}
