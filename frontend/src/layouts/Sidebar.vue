<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">
        <img :src="hapLogo" alt="HAP" class="brand-logo" />
      </div>
      <div class="brand-copy" aria-label="HAP Home Analytics">
        <div class="brand-title text-type shiny-text">
          <span>{{ typedBrandTitle }}</span>
          <span
            v-if="cursorLine === 'title'"
            class="text-type-cursor"
            aria-hidden="true"
          />
        </div>
        <div class="brand-subtitle text-type">
          <span>{{ typedBrandSubtitle }}</span>
          <span
            v-if="cursorLine === 'subtitle'"
            class="text-type-cursor"
            aria-hidden="true"
          />
        </div>
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
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
} from 'vue';
import { useRoute } from 'vue-router';

import hapLogo from '@/assets/brand/hap-horus-eye.png';

const BRAND_TITLE = 'HAP';
const BRAND_SUBTITLE = 'Home Analytics';
const TYPE_DELAY_MS = 78;
const DELETE_DELAY_MS = 34;
const LOOP_HOLD_MS = 2200;
const LOOP_RESTART_MS = 520;

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

const typedBrandTitle = ref('');
const typedBrandSubtitle = ref('');
const cursorLine = ref<'title' | 'subtitle'>('title');
let shouldStopTyping = false;

const wait = (durationMs: number): Promise<void> =>
  new Promise((resolve) => {
    window.setTimeout(resolve, durationMs);
  });

const typeText = async (
  target: typeof typedBrandTitle,
  value: string,
  delayMs: number,
): Promise<void> => {
  for (let index = 1; index <= value.length && !shouldStopTyping; index += 1) {
    target.value = value.slice(0, index);
    await wait(delayMs);
  }
};

const deleteText = async (
  target: typeof typedBrandTitle,
  delayMs: number,
): Promise<void> => {
  while (target.value.length > 0 && !shouldStopTyping) {
    target.value = target.value.slice(0, -1);
    await wait(delayMs);
  }
};

const runBrandTyping = async (): Promise<void> => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    typedBrandTitle.value = BRAND_TITLE;
    typedBrandSubtitle.value = BRAND_SUBTITLE;
    return;
  }

  while (!shouldStopTyping) {
    cursorLine.value = 'title';
    await typeText(typedBrandTitle, BRAND_TITLE, TYPE_DELAY_MS);
    await wait(180);
    cursorLine.value = 'subtitle';
    await typeText(typedBrandSubtitle, BRAND_SUBTITLE, TYPE_DELAY_MS);
    await wait(LOOP_HOLD_MS);
    await deleteText(typedBrandSubtitle, DELETE_DELAY_MS);
    cursorLine.value = 'title';
    await deleteText(typedBrandTitle, DELETE_DELAY_MS);
    await wait(LOOP_RESTART_MS);
  }
};

onMounted(() => {
  shouldStopTyping = false;
  void runBrandTyping();
});

onBeforeUnmount(() => {
  shouldStopTyping = true;
});
</script>
