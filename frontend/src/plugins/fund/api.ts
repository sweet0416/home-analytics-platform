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

export interface FundPositionCreate {
  fund_code: string;
  fund_name: string;
  fund_type: string;
  account_name: string;
  shares: number;
  cost_price: number;
  total_cost?: number | null;
  current_nav?: number | null;
  opened_at?: string | null;
  tags: string;
  note: string;
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

export function fetchFundStatus(): Promise<FundStatus> {
  return getApiData<FundStatus>('/fund/status');
}

export function fetchFundPositions(): Promise<FundPosition[]> {
  return getApiData<FundPosition[]>('/fund/positions');
}

export function createFundPosition(payload: FundPositionCreate): Promise<FundPosition> {
  return postApiData<FundPosition, FundPositionCreate>('/fund/positions', payload);
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

export function fetchFundWatchlistSummary(): Promise<FundWatchlistSummary> {
  return getApiData<FundWatchlistSummary>('/fund/watchlist/summary');
}

export function fetchFundNavSummary(): Promise<FundNavSummary> {
  return getApiData<FundNavSummary>('/fund/nav-records/summary');
}
