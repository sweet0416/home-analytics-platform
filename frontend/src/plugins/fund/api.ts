import { getApiData } from '@/api/client';

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

export function fetchFundStatus(): Promise<FundStatus> {
  return getApiData<FundStatus>('/fund/status');
}
