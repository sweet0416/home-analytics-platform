<template>
  <aside class="sidebar">
    <RouterLink to="/" class="brand" aria-label="HAP 首页">
      <span class="brand-wordmark">HAP<span aria-hidden="true">.</span></span>
      <span class="brand-subtitle">Home Intelligence</span>
    </RouterLink>
    <nav ref="navList" aria-label="Primary navigation" class="nav-list">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ 'is-active': isActiveNavItem(item.path) }"
        :aria-label="item.label"
        :aria-current="isActiveNavItem(item.path) ? 'page' : undefined"
      >
        <component :is="item.icon" class="nav-icon" aria-hidden="true" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
    <span class="nav-scroll-hint" aria-hidden="true">Swipe to explore →</span>
    <p class="sidebar-footnote">A private space for your home systems.</p>
  </aside>
</template>

<script setup lang="ts">
import {
  Box, Coin, DataAnalysis, DataBoard, Document, MagicStick,
  Monitor, Operation, Setting, TrendCharts,
} from '@element-plus/icons-vue';
import { nextTick, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

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
const navList = ref<HTMLElement | null>(null);
const isActiveNavItem = (path: string): boolean =>
  path === '/' ? route.path === '/' : route.path.startsWith(path);

watch(() => route.path, async () => {
  await nextTick();
  if (!window.matchMedia('(max-width: 640px)').matches) return;
  const current = navList.value?.querySelector<HTMLElement>('[aria-current="page"]');
  if (current && navList.value) {
    navList.value.scrollLeft = current.offsetLeft - navList.value.offsetLeft - 16;
  }
}, { immediate: true });
</script>
