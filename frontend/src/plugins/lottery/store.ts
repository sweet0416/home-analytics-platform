import { defineStore } from 'pinia';

import {
  analyzeCombinationCoverage as analyzeCombinationCoverageRequest,
  analyzeDantuo as analyzeDantuoRequest,
  analyzeSensitivity as analyzeSensitivityRequest,
  backtestNumbers as backtestNumbersRequest,
  fetchBasicStatistics,
  fetchCoOccurrenceAnalysis,
  fetchCurrentRule,
  fetchDisclaimer,
  fetchDrawCoverage,
  fetchDraws,
  fetchLatestSyncRun,
  fetchNumberOmissionDetail,
  fetchOmissionStatistics,
  fetchRandomnessDiagnostics,
  fetchRecommendationAnalysis,
  fetchReplayContext,
  fetchReplayRun,
  fetchReplayRuns,
  fetchSamePeriodAnalysis,
  fetchSimulationAnalysis,
  fetchSyncRuns,
  fetchSyncStatus,
  runReplay as runReplayRequest,
  startBackfill,
  triggerDrawSync,
  type DrawPage,
  type LotteryBacktestAnalysis,
  type LotteryBacktestRequest,
  type LotteryCoOccurrenceAnalysis,
  type LotteryDantuoAnalysis,
  type LotteryDantuoRequest,
  type LotteryBackfillJob,
  type LotteryBackfillRequest,
  type LotteryBackfillRun,
  type LotteryBasicStatistics,
  type LotteryCombinationCoverageAnalysis,
  type LotteryCoverageRequest,
  type LotteryDrawCoverage,
  type LotteryNumberOmissionDetail,
  type LotteryOmissionStatistics,
  type LotteryRandomnessDiagnostics,
  type LotteryRecommendationAnalysis,
  type LotteryRecommendationWeights,
  type LotteryReplayContext,
  type LotteryReplayRequest,
  type LotteryReplayRun,
  type LotteryReplayRunSummary,
  type LotteryRule,
  type LotterySamePeriodAnalysis,
  type LotterySensitivityAnalysis,
  type LotterySensitivityRequest,
  type LotterySimulationAnalysis,
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
    coOccurrence: null as LotteryCoOccurrenceAnalysis | null,
    omissionStatistics: null as LotteryOmissionStatistics | null,
    randomnessDiagnostics: null as LotteryRandomnessDiagnostics | null,
    omissionDetail: null as LotteryNumberOmissionDetail | null,
    samePeriod: null as LotterySamePeriodAnalysis | null,
    recommendations: null as LotteryRecommendationAnalysis | null,
    replayContext: null as LotteryReplayContext | null,
    replayRun: null as LotteryReplayRun | null,
    replayRuns: [] as LotteryReplayRunSummary[],
    sensitivity: null as LotterySensitivityAnalysis | null,
    simulation: null as LotterySimulationAnalysis | null,
    combinationCoverage: null as LotteryCombinationCoverageAnalysis | null,
    dantuo: null as LotteryDantuoAnalysis | null,
    backtest: null as LotteryBacktestAnalysis | null,
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
    async loadCoOccurrence(
      area: 'front' | 'back' | 'cross' = 'front',
      limit = 500,
      top = 30,
    ): Promise<void> {
      this.coOccurrence = await fetchCoOccurrenceAnalysis(area, limit, top);
    },
    async loadOmissionStatistics(limit = 100): Promise<void> {
      this.omissionStatistics = await fetchOmissionStatistics(limit);
    },
    async loadRandomnessDiagnostics(limit = 500): Promise<void> {
      this.randomnessDiagnostics = await fetchRandomnessDiagnostics(limit);
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
    async loadRecommendations(
      issueNo?: string,
      sets = 5,
      samePeriodCount = 10,
      sampleLimit = 200,
      weights?: LotteryRecommendationWeights,
    ): Promise<void> {
      this.recommendations = await fetchRecommendationAnalysis(
        issueNo,
        sets,
        samePeriodCount,
        sampleLimit,
        weights,
      );
    },
    async loadReplayContext(targetIssueNo: string, sampleLimit = 500): Promise<void> {
      this.replayContext = await fetchReplayContext(targetIssueNo, sampleLimit);
    },
    async loadReplayRuns(limit = 20): Promise<void> {
      this.replayRuns = await fetchReplayRuns(limit);
    },
    async loadReplayRun(runId: number): Promise<void> {
      const replayRun = await fetchReplayRun(runId);
      this.replayRun = {
        ...replayRun,
        cutoff_issue_no: replayRun.cutoff_issue_no ?? '--',
        cutoff_draw_date: replayRun.cutoff_draw_date ?? '--',
        sample_size: replayRun.sample_size,
        same_period_count: replayRun.same_period_count,
      } as LotteryReplayRun;
    },
    async runReplay(payload: LotteryReplayRequest): Promise<void> {
      this.replayRun = await runReplayRequest(payload);
      await this.loadReplayRuns();
      const currentRange = this.replayContext?.available_range;
      this.replayContext = {
        target: payload.target_issue_no === this.replayContext?.target.issue_no
          ? this.replayContext.target
          : this.replayRun.target_draw,
        cutoff: null,
        sample_size: this.replayRun.sample_size,
        requested_sample_limit: payload.sample_limit,
        available_range: {
          earliest_issue_no: currentRange?.earliest_issue_no ?? null,
          latest_issue_no: this.replayRun.cutoff_issue_no,
          earliest_draw_date: currentRange?.earliest_draw_date ?? null,
          latest_draw_date: this.replayRun.cutoff_draw_date,
        },
        leakage_check: this.replayRun.leakage_check,
        warnings: this.replayRun.warnings,
        same_period_deviation: this.replayRun.same_period_deviation,
      };
    },
    async analyzeSensitivity(payload: LotterySensitivityRequest): Promise<void> {
      this.sensitivity = await analyzeSensitivityRequest(payload);
    },
    async loadSimulation(simulations = 10000, sets = 5, seed?: number): Promise<void> {
      this.simulation = await fetchSimulationAnalysis(simulations, sets, seed);
    },
    async analyzeCombinationCoverage(payload: LotteryCoverageRequest): Promise<void> {
      this.combinationCoverage = await analyzeCombinationCoverageRequest(payload);
    },
    async analyzeDantuo(payload: LotteryDantuoRequest): Promise<void> {
      this.dantuo = await analyzeDantuoRequest(payload);
    },
    async backtestNumbers(payload: LotteryBacktestRequest): Promise<void> {
      this.backtest = await backtestNumbersRequest(payload);
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
