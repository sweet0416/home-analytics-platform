<template>
  <header class="topbar">
    <div class="topbar-context">
      <span class="topbar-title">{{ pageTitle }}</span>
      <span class="topbar-subtitle">Private home intelligence</span>
    </div>
    <div class="topbar-status" role="status" aria-live="polite">
      <span class="status-dot" :class="{ online: system.health?.status === 'ok' }" aria-hidden="true" />
      <span>{{ statusText }}</span>
      <span v-if="frontendBuild" class="topbar-version" :title="frontendBuild.git_commit">
        {{ frontendBuild.git_commit.slice(0, 7) }}
      </span>
      <el-button text size="small" class="topbar-logout" @click="logout">退出</el-button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { useRoute, useRouter } from 'vue-router';

import { postApiData, setCsrfToken } from '@/api/client';
import { useSystemStore } from '@/stores/system';

const system = useSystemStore();
const route = useRoute();
const router = useRouter();
const frontendBuild = ref<{ git_commit: string; build_time: string } | null>(null);
const statusText = computed(() => system.health?.status === 'ok' ? 'System online' : system.error ? 'Connection unavailable' : 'Checking');
const pageTitle = computed(() => {
  if (route.path === '/') return 'Overview';
  if (route.path.startsWith('/fund')) return 'Fund';
  if (route.path.startsWith('/lottery')) return 'Lottery';
  const titles: Record<string, string> = {
    '/reports': 'Reports', '/settings': 'Settings', '/docker': 'Docker',
    '/pve': 'PVE', '/pve-legacy': 'PVE', '/stocks': 'Stocks', '/ai-lab': 'AI Lab', '/automation': 'Automation',
  };
  return titles[route.path] ?? 'HAP';
});

async function logout(): Promise<void> {
  try {
    await postApiData<{ logged_out: boolean }, Record<string, never>>('/auth/logout', {});
    setCsrfToken('');
    await router.replace('/login');
  } catch {
    ElMessage.error('退出失败，请重试。');
  }
}

onMounted(async () => {
  void system.fetchHealth();
  try {
    const response = await fetch('/build-info.json', { cache: 'no-store' });
    if (response.ok) frontendBuild.value = await response.json();
  } catch {
    frontendBuild.value = null;
  }
});
</script>
