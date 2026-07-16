import { defineStore } from 'pinia';

import {
  fetchBasicStatistics,
  fetchCurrentRule,
  fetchDisclaimer,
  fetchDrawCoverage,
  fetchDraws,
  fetchLatestSyncRun,
  fetchNumberOmissionDetail,
  fetchOmissionStatistics,
  fetchSamePeriodAnalysis,
  fetchSyncRuns,
  fetchSyncStatus,
  startBackfill,
  triggerDrawSync,
  type DrawPage,
  type LotteryBackfillJob,
  type LotteryBackfillRequest,
  type LotteryBackfillRun,
  type LotteryBasicStatistics,
  type LotteryDrawCoverage,
  type LotteryNumberOmissionDetail,
  type LotteryOmissionStatistics,
  type LotteryRule,
  type LotterySamePeriodAnalysis,
  type LotterySyncRun,
  type LotterySyncStatus,
  type SyncRunPage,
} from './api';

export const useLotteryStore = defineStore('lottery', {
  state: () => ({
    rule: null as LotteryRule | null,
    draws: null as DrawPage | null,
    drawCoverage: null as LotteryDrawCoverage | null,
    latestSyncRun: null as LotterySyncRun | null,
    syncStatus: null as LotterySyncStatus | null,
    syncRuns: null as SyncRunPage | null,
    statistics: null as LotteryBasicStatistics | null,
    omissionStatistics: null as LotteryOmissionStatistics | null,
    omissionDetail: null as LotteryNumberOmissionDetail | null,
    samePeriod: null as LotterySamePeriodAnalysis | null,
    latestBackfillRun: null as LotteryBackfillRun | null,
    latestBackfillJob: null as LotteryBackfillJob | null,
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
        const [rule, draws, coverage, disclaimer] = await Promise.all([
          fetchCurrentRule(),
          fetchDraws(),
          fetchDrawCoverage(),
          fetchDisclaimer(),
        ]);
        this.rule = rule;
        this.draws = draws;
        this.drawCoverage = coverage;
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
    async loadDrawCoverage(): Promise<void> {
      this.drawCoverage = await fetchDrawCoverage();
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
    async loadSamePeriod(issueNo?: string, count = 5): Promise<void> {
      this.samePeriod = await fetchSamePeriodAnalysis(issueNo, count);
    },
    async backfill(payload: LotteryBackfillRequest): Promise<void> {
      this.syncing = true;
      this.syncError = '';
      try {
        this.latestBackfillJob = await startBackfill(payload);
        await Promise.all([
          this.loadDraws(),
          this.loadDrawCoverage(),
          this.loadSyncState(),
          this.loadStatistics(),
          this.loadOmissionStatistics(),
          this.loadSamePeriod(),
        ]);
      } catch (error) {
        this.syncError = error instanceof Error ? error.message : 'Failed to backfill lottery draws';
      } finally {
        this.syncing = this.syncStatus?.running ?? false;
      }
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
          this.loadDrawCoverage(),
          this.loadSyncState(),
          this.loadStatistics(),
          this.loadOmissionStatistics(),
          this.loadSamePeriod(),
        ]);
      } catch (error) {
        this.syncError = error instanceof Error ? error.message : 'Failed to sync lottery draws';
      } finally {
        this.syncing = false;
      }
    },
  },
});
