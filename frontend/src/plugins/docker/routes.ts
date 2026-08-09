import type { RouteRecordRaw } from 'vue-router';

import DockerView from './views/DockerView.vue';

export const dockerRoutes: RouteRecordRaw[] = [
  {
    path: 'docker',
    name: 'docker',
    component: DockerView,
  },
];
