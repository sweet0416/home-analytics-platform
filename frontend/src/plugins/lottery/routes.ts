import type { RouteRecordRaw } from 'vue-router';

import BacktestView from './views/BacktestView.vue';
import CoOccurrenceView from './views/CoOccurrenceView.vue';
import CombinationCoverageView from './views/CombinationCoverageView.vue';
import DataHealthView from './views/DataHealthView.vue';
import DantuoView from './views/DantuoView.vue';
import DrawHistory from './views/DrawHistory.vue';
import HeatmapView from './views/HeatmapView.vue';
import LotteryOverview from './views/LotteryOverview.vue';
import OmissionView from './views/OmissionView.vue';
import RecommendationView from './views/RecommendationView.vue';
import RandomnessView from './views/RandomnessView.vue';
import ReplayView from './views/ReplayView.vue';
import SamePeriodView from './views/SamePeriodView.vue';
import SensitivityView from './views/SensitivityView.vue';
import SimulationView from './views/SimulationView.vue';
import StatisticsView from './views/StatisticsView.vue';

export const lotteryRoutes: RouteRecordRaw[] = [
  {
    path: 'lottery/dlt',
    name: 'lottery-dlt-overview',
    component: LotteryOverview,
  },
  {
    path: 'lottery/dlt/draws',
    name: 'lottery-dlt-draws',
    component: DrawHistory,
  },
  {
    path: 'lottery/dlt/statistics',
    name: 'lottery-dlt-statistics',
    component: StatisticsView,
  },
  {
    path: 'lottery/dlt/omissions',
    name: 'lottery-dlt-omissions',
    component: OmissionView,
  },
  {
    path: 'lottery/dlt/heatmap',
    name: 'lottery-dlt-heatmap',
    component: HeatmapView,
  },
  {
    path: 'lottery/dlt/same-period',
    name: 'lottery-dlt-same-period',
    component: SamePeriodView,
  },
  {
    path: 'lottery/dlt/co-occurrence',
    name: 'lottery-dlt-co-occurrence',
    component: CoOccurrenceView,
  },
  {
    path: 'lottery/dlt/recommendations',
    name: 'lottery-dlt-recommendations',
    component: RecommendationView,
  },
  {
    path: 'lottery/dlt/simulation',
    name: 'lottery-dlt-simulation',
    component: SimulationView,
  },
  {
    path: 'lottery/dlt/coverage',
    name: 'lottery-dlt-coverage',
    component: CombinationCoverageView,
  },
  {
    path: 'lottery/dlt/dantuo',
    name: 'lottery-dlt-dantuo',
    component: DantuoView,
  },
  {
    path: 'lottery/dlt/backtest',
    name: 'lottery-dlt-backtest',
    component: BacktestView,
  },
  {
    path: 'lottery/dlt/replay',
    name: 'lottery-dlt-replay',
    component: ReplayView,
  },
  {
    path: 'lottery/dlt/sensitivity',
    name: 'lottery-dlt-sensitivity',
    component: SensitivityView,
  },
  {
    path: 'lottery/dlt/randomness',
    name: 'lottery-dlt-randomness',
    component: RandomnessView,
  },
  {
    path: 'lottery/dlt/data-health',
    name: 'lottery-dlt-data-health',
    component: DataHealthView,
  },
];
