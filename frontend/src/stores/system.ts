import { defineStore } from 'pinia';

import { getApiData } from '@/api/client';

export interface HealthStatus {
  status: string;
  version: string;
  database: string;
}

export const useSystemStore = defineStore('system', {
  state: () => ({
    health: null as HealthStatus | null,
    loading: false,
    error: '',
  }),
  actions: {
    async fetchHealth(): Promise<void> {
      this.loading = true;
      this.error = '';
      try {
        this.health = await getApiData<HealthStatus>('/system/health');
      } catch (error) {
        this.health = null;
        this.error = error instanceof Error ? error.message : 'Backend is not reachable';
      } finally {
        this.loading = false;
      }
    },
  },
});
