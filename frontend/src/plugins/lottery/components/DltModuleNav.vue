<template>
  <nav ref="navRef" class="dlt-module-nav" aria-label="大乐透功能导航">
    <RouterLink
      v-for="item in moduleNavItems"
      :key="item.path"
      :to="item.path"
      class="dlt-module-nav-link"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

const moduleNavItems = [
  { label: '概览', path: '/lottery/dlt' },
  { label: '历史开奖', path: '/lottery/dlt/draws' },
  { label: '统计分析', path: '/lottery/dlt/statistics' },
  { label: '遗漏统计', path: '/lottery/dlt/omissions' },
  { label: '热力图', path: '/lottery/dlt/heatmap' },
  { label: '历史同期', path: '/lottery/dlt/same-period' },
  { label: '选号推荐', path: '/lottery/dlt/recommendations' },
  { label: '模拟选号', path: '/lottery/dlt/simulation' },
  { label: '定胆胆拖', path: '/lottery/dlt/dantuo' },
  { label: '组合回测', path: '/lottery/dlt/backtest' },
  { label: '历史回放', path: '/lottery/dlt/replay' },
  { label: '数据健康', path: '/lottery/dlt/data-health' },
];

const route = useRoute();
const navRef = ref<HTMLElement | null>(null);

function scrollActiveLinkIntoView(): void {
  const nav = navRef.value;
  if (!nav || nav.scrollWidth <= nav.clientWidth) return;

  const activeLink = nav.querySelector<HTMLElement>('.router-link-exact-active');
  activeLink?.scrollIntoView({
    behavior: 'smooth',
    block: 'nearest',
    inline: 'center',
  });
}

onMounted(() => {
  void nextTick(scrollActiveLinkIntoView);
});

watch(
  () => route.fullPath,
  () => {
    void nextTick(scrollActiveLinkIntoView);
  },
);
</script>

<style scoped>
.dlt-module-nav {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.84);
  box-shadow: 0 14px 32px rgba(2, 6, 23, 0.2);
  backdrop-filter: blur(14px);
  margin-bottom: 16px;
  padding: 10px;
}

.dlt-module-nav-link {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 8px;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1;
  padding: 9px 11px;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
  white-space: nowrap;
}

.dlt-module-nav-link:hover,
.dlt-module-nav-link.router-link-exact-active {
  border-color: rgba(56, 189, 248, 0.42);
  background: rgba(56, 189, 248, 0.1);
  color: var(--color-text);
}

.dlt-module-nav-link.router-link-exact-active {
  color: var(--color-primary);
}

@media (max-width: 760px) {
  .dlt-module-nav {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 12px;
    scroll-padding-inline: 40px;
    scrollbar-width: thin;
    mask-image: linear-gradient(
      90deg,
      transparent 0,
      #000 22px,
      #000 calc(100% - 22px),
      transparent 100%
    );
  }

  .dlt-module-nav-link {
    flex: 0 0 auto;
  }
}
</style>
