<template>
  <header class="topbar">
    <div>
      <div class="topbar-title">Home Analytics Platform</div>
      <div class="topbar-subtitle">PVE Docker target: 192.168.100.249</div>
    </div>
    <div class="topbar-status">
      <span class="status-dot" :class="{ online: system.health?.status === 'ok' }" />
      <span>{{ statusText }}</span>
      <span class="topbar-version">v{{ system.health?.version ?? '1.0.0' }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';

import { useSystemStore } from '@/stores/system';

const system = useSystemStore();
const statusText = computed(() => system.health?.status ?? (system.error ? 'offline' : 'checking'));

onMounted(() => {
  void system.fetchHealth();
});
</script>
