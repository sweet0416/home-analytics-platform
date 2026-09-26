<template>
  <div class="home-overview">
    <header class="home-intro">
      <div>
        <h1 class="page-title">Home overview</h1>
        <p class="page-subtitle">Your systems and data, in one private place.</p>
      </div>
      <span class="home-system-state" :class="{ 'is-online': system.health?.status === 'ok' }">
        <span class="status-dot" :class="{ online: system.health?.status === 'ok' }" aria-hidden="true" />
        {{ system.health?.status === 'ok' ? 'System available' : system.error ? 'Connection unavailable' : 'Checking system' }}
      </span>
    </header>

    <section class="home-highlight" aria-label="System overview">
      <div class="home-highlight-copy">
        <h2>Everything in view.</h2>
        <p>Track the services and records you already use. Open a module for the full picture.</p>
      </div>
      <div class="home-highlight-readouts">
        <div><span>API</span><strong>{{ system.health?.status ?? '—' }}</strong></div>
        <div><span>Database</span><strong>{{ system.health?.database ?? '—' }}</strong></div>
        <div><span>Backend</span><strong>v{{ system.health?.version ?? '—' }}</strong></div>
      </div>
    </section>

    <el-alert v-if="infraAlerts.length" type="warning" :closable="false" show-icon :title="infraAlerts.join('；')" />

    <div class="home-section-heading">
      <h2>At a glance</h2>
      <span>Live from your configured services</span>
    </div>
    <section class="home-metrics" aria-label="Current metrics">
      <article class="home-metric">
        <span class="home-metric-label">Latest draw</span>
        <strong>{{ latestIssue }}</strong>
        <span>{{ drawDetail }}</span>
      </article>
      <article class="home-metric">
        <span class="home-metric-label">Draw sync</span>
        <strong>{{ syncStatus }}</strong>
        <span>Latest lottery update</span>
      </article>
      <article class="home-metric">
        <span class="home-metric-label">Docker</span>
        <strong>{{ dockerSummary }}</strong>
        <span>Configured infrastructure</span>
      </article>
      <article class="home-metric">
        <span class="home-metric-label">PVE</span>
        <strong>{{ pveSummary }}</strong>
        <span>Configured infrastructure</span>
      </article>
    </section>

    <div class="home-section-heading">
      <h2>Explore your system</h2>
      <span>Choose a workspace</span>
    </div>
    <nav class="home-modules" aria-label="Product modules">
      <RouterLink to="/fund" class="home-module home-module--fund">
        <span class="home-module-icon"><Coin aria-hidden="true" /></span>
        <strong>Fund</strong><span>Holdings, NAV and performance</span><ArrowRight aria-hidden="true" class="home-module-arrow" />
      </RouterLink>
      <RouterLink to="/lottery/dlt" class="home-module home-module--lottery">
        <span class="home-module-icon"><DataAnalysis aria-hidden="true" /></span>
        <strong>Lottery</strong><span>Draws, signals and data health</span><ArrowRight aria-hidden="true" class="home-module-arrow" />
      </RouterLink>
      <RouterLink to="/reports" class="home-module home-module--reports">
        <span class="home-module-icon"><Document aria-hidden="true" /></span>
        <strong>Reports</strong><span>Daily fund reporting</span><ArrowRight aria-hidden="true" class="home-module-arrow" />
      </RouterLink>
      <RouterLink to="/settings" class="home-module home-module--settings">
        <span class="home-module-icon"><Setting aria-hidden="true" /></span>
        <strong>Settings</strong><span>Backups and notifications</span><ArrowRight aria-hidden="true" class="home-module-arrow" />
      </RouterLink>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ArrowRight, Coin, DataAnalysis, Document, Setting } from '@element-plus/icons-vue';
import { computed, onMounted, ref } from 'vue';

import { fetchInfrastructureHealth, type InfrastructureHealth } from '@/api/system';
import { useLotteryStore } from '@/plugins/lottery/store';
import { useSystemStore } from '@/stores/system';

const system = useSystemStore();
const lottery = useLotteryStore();
const infrastructureHealth = ref<InfrastructureHealth | null>(null);
const infrastructureLoading = ref(true);
const infrastructureError = ref(false);
const dockerStatus = computed(() => infrastructureHealth.value?.docker ?? null);
const pveStatus = computed(() => infrastructureHealth.value?.pve ?? null);
const latestIssue = computed(() => lottery.error ? 'Unavailable' : lottery.loading ? 'Loading' : lottery.draws?.items[0]?.issue_no ?? '—');
const drawDetail = computed(() => lottery.error ? 'Could not load draw data' : lottery.draws ? `${lottery.draws.pagination.total} draws on record` : 'Waiting for lottery data');
const syncStatus = computed(() => {
  if (lottery.error) return 'Unavailable';
  if (lottery.loading) return 'Loading';
  if (!lottery.syncStatus) return 'Status unavailable';
  const status = lottery.latestSyncRun?.status;
  if (!status) return 'No run yet';
  const labels: Record<string, string> = {
    running: 'Running', success: 'Up to date', partial_success: 'Partial', failed: 'Failed',
  };
  return labels[status] ?? status;
});
const dockerSummary = computed(() => {
  if (infrastructureLoading.value) return 'Loading';
  if (infrastructureError.value || !infrastructureHealth.value) return 'Unavailable';
  if (!dockerStatus.value?.configured) return 'Not configured';
  if (!dockerStatus.value.reachable) return 'Unavailable';
  return dockerStatus.value.problematic
    ? `${dockerStatus.value.problematic} need attention`
    : `${dockerStatus.value.running}/${dockerStatus.value.containers} running`;
});
const pveSummary = computed(() => {
  if (infrastructureLoading.value) return 'Loading';
  if (infrastructureError.value || !infrastructureHealth.value) return 'Unavailable';
  if (!pveStatus.value?.configured) return 'Not configured';
  return pveStatus.value.reachable ? 'Connected' : 'Unavailable';
});
const infraAlerts = computed(() => infrastructureHealth.value?.alerts ?? []);

onMounted(() => {
  void system.fetchHealth();
  void lottery.loadOverview();
  void fetchInfrastructureHealth()
    .then((value) => { infrastructureHealth.value = value; })
    .catch(() => { infrastructureError.value = true; })
    .finally(() => { infrastructureLoading.value = false; });
});
</script>
