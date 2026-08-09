import { getApiData } from '@/api/client';

export interface PveStatus {
  plugin: string;
  version: string;
  enabled: boolean;
  configured: boolean;
  reachable: boolean;
  pve_version: string | null;
  error: string | null;
}

export interface PveResourceResponse {
  data: Record<string, unknown>[];
}

export function fetchPveStatus(): Promise<PveStatus> {
  return getApiData<PveStatus>('/pve/status');
}

export function fetchPveNodes(): Promise<PveResourceResponse> {
  return getApiData<PveResourceResponse>('/pve/nodes');
}

export function fetchPveGuests(): Promise<PveResourceResponse> {
  return getApiData<PveResourceResponse>('/pve/guests');
}

export function fetchPveStorage(): Promise<PveResourceResponse> {
  return getApiData<PveResourceResponse>('/pve/storage');
}

export function fetchPveTasks(): Promise<PveResourceResponse> {
  return getApiData<PveResourceResponse>('/pve/tasks');
}
