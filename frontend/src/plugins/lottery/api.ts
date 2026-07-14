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

export function triggerDrawSync(payload: LotterySyncRequest): Promise<LotterySyncRun> {
  return postApiData<LotterySyncRun, LotterySyncRequest>('/lottery/dlt/sync', payload);
}
