import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

import MainLayout from '@/layouts/MainLayout.vue';
import DashboardView from '@/views/DashboardView.vue';
import PlaceholderView from '@/views/PlaceholderView.vue';
import ReportsView from '@/views/ReportsView.vue';
import SettingsView from '@/views/SettingsView.vue';
import { lotteryRoutes } from '@/plugins/lottery/routes';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'dashboard',
        component: DashboardView,
      },
      ...lotteryRoutes,
      {
        path: 'fund',
        name: 'fund-placeholder',
        component: PlaceholderView,
        meta: { title: 'Fund', subtitle: 'ETF、QDII、资产配置和收益分析模块' },
      },
      {
        path: 'stocks',
        name: 'stocks-placeholder',
        component: PlaceholderView,
        meta: { title: 'Stocks', subtitle: '股票行情、持仓与走势图模块' },
      },
      {
        path: 'docker',
        name: 'docker-placeholder',
        component: PlaceholderView,
        meta: { title: 'Docker', subtitle: 'PVE 主机 Docker 容器监控模块' },
      },
      {
        path: 'pve',
        name: 'pve-placeholder',
        component: PlaceholderView,
        meta: { title: 'PVE', subtitle: 'Proxmox VE 节点、VM、LXC 与存储监控模块' },
      },
      {
        path: 'ai-lab',
        name: 'ai-lab-placeholder',
        component: PlaceholderView,
        meta: { title: 'AI Lab', subtitle: '本地 AI 实验与自动化能力模块' },
      },
      {
        path: 'automation',
        name: 'automation-placeholder',
        component: PlaceholderView,
        meta: { title: 'Automation', subtitle: '自动更新、日报、备份与定时任务模块' },
      },
      {
        path: 'reports',
        name: 'reports',
        component: ReportsView,
      },
      {
        path: 'settings',
        name: 'settings',
        component: SettingsView,
      },
    ],
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
