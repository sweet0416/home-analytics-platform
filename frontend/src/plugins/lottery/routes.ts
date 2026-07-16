import type { RouteRecordRaw } from 'vue-router';

import DrawHistory from './views/DrawHistory.vue';
import HeatmapView from './views/HeatmapView.vue';
import LotteryOverview from './views/LotteryOverview.vue';
import OmissionView from './views/OmissionView.vue';
import RecommendationView from './views/RecommendationView.vue';
import SamePeriodView from './views/SamePeriodView.vue';
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
    path: 'lottery/dlt/recommendations',
    name: 'lottery-dlt-recommendations',
    component: RecommendationView,
  },
];
