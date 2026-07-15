import { getApiData, postApiData } from '@/api/client';

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

export interface LotterySyncRequest {
  sync_type: 'manual' | 'backfill';
  page: number;
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

export function fetchCurrentRule(): Promise<LotteryRule> {
  return getApiData<LotteryRule>('/lottery/dlt/rules/current');
}

export function fetchDraws(page = 1, pageSize = 20): Promise<DrawPage> {
  return getApiData<DrawPage>(`/lottery/dlt/draws?page=${page}&page_size=${pageSize}`);
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

export function triggerDrawSync(payload: LotterySyncRequest): Promise<LotterySyncRun> {
  return postApiData<LotterySyncRun, LotterySyncRequest>('/lottery/dlt/sync', payload);
}
