import type { RouteRecordRaw } from 'vue-router';

import PveView from './views/PveView.vue';

export const pveRoutes: RouteRecordRaw[] = [
  {
    path: 'pve',
    name: 'pve',
    component: PveView,
  },
];
