import type { RouteRecordRaw } from 'vue-router';

import DrawHistory from './views/DrawHistory.vue';
import LotteryOverview from './views/LotteryOverview.vue';
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
];

