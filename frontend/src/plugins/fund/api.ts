import { getApiData, postApiData } from '@/api/client';

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

export function fetchFundStatus(): Promise<FundStatus> {
  return getApiData<FundStatus>('/fund/status');
}

export function fetchFundPositions(): Promise<FundPosition[]> {
  return getApiData<FundPosition[]>('/fund/positions');
}

export function createFundPosition(payload: FundPositionCreate): Promise<FundPosition> {
  return postApiData<FundPosition, FundPositionCreate>('/fund/positions', payload);
}

export function fetchFundHoldingSummary(): Promise<FundHoldingSummary> {
  return getApiData<FundHoldingSummary>('/fund/holdings/summary');
}
