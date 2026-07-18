<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">
        <img :src="hapLogo" alt="HAP" class="brand-logo" />
      </div>
      <div>
        <div class="brand-title shiny-text">HAP</div>
        <div class="brand-subtitle">Home Analytics</div>
      </div>
    </div>

    <nav
      class="nav-list"
      :style="{ '--active-index': String(activeIndex) }"
    >
      <span class="nav-active-line" aria-hidden="true" />
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ 'is-active': isActiveNavItem(item.path) }"
      >
        <component :is="item.icon" class="nav-icon" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import {
  Box,
  Coin,
  DataAnalysis,
  DataBoard,
  Document,
  MagicStick,
  Monitor,
  Operation,
  Setting,
  TrendCharts,
} from '@element-plus/icons-vue';
import { computed } from 'vue';
import { useRoute } from 'vue-router';

import hapLogo from '@/assets/brand/hap-horus-eye.png';

const navItems = [
  { path: '/', label: 'Dashboard', icon: DataBoard },
  { path: '/lottery/dlt', label: 'Lottery', icon: DataAnalysis },
  { path: '/fund', label: 'Fund', icon: Coin },
  { path: '/stocks', label: 'Stocks', icon: TrendCharts },
  { path: '/docker', label: 'Docker', icon: Box },
  { path: '/pve', label: 'PVE', icon: Monitor },
  { path: '/ai-lab', label: 'AI Lab', icon: MagicStick },
  { path: '/automation', label: 'Automation', icon: Operation },
  { path: '/reports', label: 'Reports', icon: Document },
  { path: '/settings', label: 'Settings', icon: Setting },
];

const route = useRoute();
const activeIndex = computed(() => {
  const index = navItems.findIndex((item) =>
    item.path === '/' ? route.path === '/' : route.path.startsWith(item.path),
  );
  return Math.max(index, 0);
});

const isActiveNavItem = (path: string): boolean =>
  path === '/' ? route.path === '/' : route.path.startsWith(path);
</script>
