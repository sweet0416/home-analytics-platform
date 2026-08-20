<template>
  <header class="topbar">
    <div>
      <div class="topbar-title shiny-text">Home Analytics Platform</div>
      <div class="topbar-subtitle">
        PVE Docker target: 192.168.100.249
        <span v-if="frontendBuild"> · {{ frontendBuild.git_commit }}</span>
      </div>
    </div>
    <div class="topbar-status" role="status" aria-live="polite">
      <span class="status-dot" :class="{ online: system.health?.status === 'ok' }" />
      <span>{{ statusText }}</span>
      <span class="topbar-version">v{{ system.health?.version ?? '1.0.0' }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { useSystemStore } from '@/stores/system';

const system = useSystemStore();
const frontendBuild = ref<{ git_commit: string; build_time: string } | null>(null);
const statusText = computed(() => system.health?.status ?? (system.error ? 'offline' : 'checking'));

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
