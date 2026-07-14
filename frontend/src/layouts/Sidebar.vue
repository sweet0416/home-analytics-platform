<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">H</div>
      <div>
        <div class="brand-title">HAP</div>
        <div class="brand-subtitle">Home Analytics</div>
      </div>
    </div>

    <nav class="nav-list">
      <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
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
</script>
