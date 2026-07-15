import { defineStore } from 'pinia';

import {
  fetchBasicStatistics,
  fetchCurrentRule,
  fetchDisclaimer,
  fetchDraws,
  fetchLatestSyncRun,
  fetchNumberOmissionDetail,
  fetchOmissionStatistics,
  fetchSyncRuns,
  fetchSyncStatus,
  triggerDrawSync,
  type DrawPage,
  type LotteryBasicStatistics,
  type LotteryNumberOmissionDetail,
  type LotteryOmissionStatistics,
  type LotteryRule,
  type LotterySyncRun,
  type LotterySyncStatus,
  type SyncRunPage,
} from './api';

export const useLotteryStore = defineStore('lottery', {
  state: () => ({
    rule: null as LotteryRule | null,
    draws: null as DrawPage | null,
    latestSyncRun: null as LotterySyncRun | null,
    syncStatus: null as LotterySyncStatus | null,
    syncRuns: null as SyncRunPage | null,
    statistics: null as LotteryBasicStatistics | null,
    omissionStatistics: null as LotteryOmissionStatistics | null,
    omissionDetail: null as LotteryNumberOmissionDetail | null,
    disclaimer: '',
    loading: false,
    syncing: false,
    error: '',
    syncError: '',
  }),
  actions: {
    async loadOverview(): Promise<void> {
      this.loading = true;
      this.error = '';
      try {
        const [rule, draws, disclaimer] = await Promise.all([
          fetchCurrentRule(),
          fetchDraws(),
          fetchDisclaimer(),
        ]);
        this.rule = rule;
        this.draws = draws;
        this.disclaimer = disclaimer.disclaimer;
        await this.loadSyncState();
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to load lottery data';
      } finally {
        this.loading = false;
      }
    },
    async loadDraws(page = 1, pageSize = 20): Promise<void> {
      this.draws = await fetchDraws(page, pageSize);
    },
    async loadSyncState(): Promise<void> {
      this.syncError = '';
      try {
        const [status, runs, latest] = await Promise.allSettled([
          fetchSyncStatus(),
          fetchSyncRuns(),
          fetchLatestSyncRun(),
        ]);
        if (status.status === 'fulfilled') {
          this.syncStatus = status.value;
          this.latestSyncRun = status.value.latest_run;
        }
        if (runs.status === 'fulfilled') {
          this.syncRuns = runs.value;
        }
        if (!this.latestSyncRun && latest.status === 'fulfilled') {
          this.latestSyncRun = latest.value;
        }
      } catch (error) {
        this.syncError = error instanceof Error ? error.message : 'Failed to load sync status';
      }
    },
    async loadStatistics(limit = 100): Promise<void> {
      this.statistics = await fetchBasicStatistics(limit);
    },
    async loadOmissionStatistics(limit = 100): Promise<void> {
      this.omissionStatistics = await fetchOmissionStatistics(limit);
    },
    async loadOmissionDetail(
      area: 'front' | 'back',
      number: number,
      limit = 200,
    ): Promise<void> {
      this.omissionDetail = await fetchNumberOmissionDetail(area, number, limit);
    },
    async syncNow(): Promise<void> {
      this.syncing = true;
      this.syncError = '';
      try {
        this.latestSyncRun = await triggerDrawSync({
          sync_type: 'manual',
          page: 1,
          page_size: 100,
          force: false,
        });
        await Promise.all([
          this.loadDraws(),
          this.loadSyncState(),
          this.loadStatistics(),
          this.loadOmissionStatistics(),
        ]);
      } catch (error) {
        this.syncError = error instanceof Error ? error.message : 'Failed to sync lottery draws';
      } finally {
        this.syncing = false;
      }
    },
  },
});
