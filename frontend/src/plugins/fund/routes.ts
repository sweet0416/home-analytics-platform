import type { RouteRecordRaw } from 'vue-router';

import FundOverview from './views/FundOverview.vue';

export const fundRoutes: RouteRecordRaw[] = [
  {
    path: 'fund',
    name: 'fund-overview',
    component: FundOverview,
  },
];
