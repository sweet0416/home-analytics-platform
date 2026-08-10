<template>
  <div>
    <RevealContent as="section" class="page-header" :delay="20">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <div class="page-subtitle">服务器、数据插件和任务状态的统一入口</div>
      </div>
    </RevealContent>

    <div class="grid metrics">
      <MetricCard label="API" :value="system.health?.status ?? '--'" meta="Backend health" :delay="80" />
      <MetricCard label="Database" :value="system.health?.database ?? '--'" meta="SQLite first" :delay="140" />
      <MetricCard label="Version" :value="system.health?.version ?? '--'" meta="Backend release" :delay="200" />
      <MetricCard label="Deploy" value="PVE Docker" meta="192.168.100.249" :delay="260" />
    </div>
    <el-alert v-if="infraAlerts.length" type="warning" :closable="false" show-icon :title="infraAlerts.join('；')" />

    <div class="dashboard-grid">
      <RevealContent as="section" class="panel" :delay="320">
        <div class="panel-header">
          <h2 class="panel-title">大乐透摘要</h2>
          <RouterLink to="/lottery/dlt" class="panel-link">打开</RouterLink>
        </div>
        <div class="panel-body">
          <div class="summary-row"><span>当前规则</span><strong>{{ lottery.rule?.rule_name ?? '未加载' }}</strong></div>
          <div class="summary-row"><span>最新期号</span><strong>{{ latestIssue }}</strong></div>
          <div class="summary-row"><span>开奖数据</span><strong>{{ lottery.draws?.pagination.total ?? 0 }}</strong></div>
          <div class="summary-row"><span>同步状态</span><strong>{{ syncStatus }}</strong></div>
        </div>
      </RevealContent>

      <RevealContent as="section" class="panel" :delay="380">
        <div class="panel-header"><h2 class="panel-title">基础设施</h2></div>
        <div class="panel-body infra-list">
          <div>
            <span>Docker</span>
            <span class="infra-actions">
              <strong :class="dockerStatusClass">{{ dockerSummary }}</strong>
              <RouterLink to="/docker" class="panel-link">查看</RouterLink>
            </span>
          </div>
          <div><span>PVE</span><span class="infra-actions"><strong :class="pveStatusClass">{{ pveSummary }}</strong><RouterLink to="/pve" class="panel-link">查看</RouterLink></span></div>
          <div><span>Scheduler</span><strong>{{ schedulerStatus }}</strong></div>
        </div>
      </RevealContent>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { fetchInfrastructureHealth, type InfrastructureHealth } from '@/api/system';
import RevealContent from '@/components/common/RevealContent.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import { useLotteryStore } from '@/plugins/lottery/store';
import { useSystemStore } from '@/stores/system';

const system = useSystemStore();
const lottery = useLotteryStore();
const infrastructureHealth = ref<InfrastructureHealth | null>(null);
const dockerStatus = computed(() => infrastructureHealth.value?.docker ?? null);
const pveStatus = computed(() => infrastructureHealth.value?.pve ?? null);

const latestIssue = computed(() => lottery.draws?.items[0]?.issue_no ?? '--');
const syncStatus = computed(() => {
  const status = lottery.latestSyncRun?.status;
  if (!status) return '未同步';
  const labels: Record<string, string> = {
    running: '同步中',
    success: '成功',
    partial_success: '部分成功',
    failed: '失败',
  };
  return labels[status] ?? status;
});
const schedulerStatus = computed(() => (lottery.latestSyncRun ? '已启用' : '等待首次运行'));
const dockerSummary = computed(() => {
  if (!dockerStatus.value?.configured) return '未配置';
  if (!dockerStatus.value.reachable) return '连接异常';
  return dockerStatus.value.problematic
    ? `${dockerStatus.value.problematic} 个异常`
    : `${dockerStatus.value.running}/${dockerStatus.value.containers} 运行中`;
});
const dockerStatusClass = computed(() => ({
  'is-online': Boolean(dockerStatus.value?.reachable && !dockerStatus.value.problematic),
  'is-warning': Boolean(dockerStatus.value?.configured && !dockerStatus.value?.reachable),
}));
const pveSummary = computed(() => {
  if (!pveStatus.value?.configured) return '未配置';
  return pveStatus.value.reachable ? '已连接' : '连接异常';
});
const pveStatusClass = computed(() => ({
  'is-online': Boolean(pveStatus.value?.reachable),
  'is-warning': Boolean(pveStatus.value?.configured && !pveStatus.value?.reachable),
}));
const infraAlerts = computed(() => infrastructureHealth.value?.alerts ?? []);

onMounted(() => {
  void system.fetchHealth();
  void lottery.loadOverview();
  void fetchInfrastructureHealth()
    .then((value) => { infrastructureHealth.value = value; })
    .catch(() => { infrastructureHealth.value = null; });
});
</script>

<style scoped>
.dashboard-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 16px; margin-top: 16px; }
.panel-link { color: var(--color-primary); font-size: 13px; }
.summary-row, .infra-list div { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(148, 163, 184, 0.12); padding: 11px 0; }
.summary-row:first-child, .infra-list div:first-child { padding-top: 0; }
.summary-row:last-child, .infra-list div:last-child { border-bottom: 0; padding-bottom: 0; }
.summary-row span, .infra-list span { color: var(--color-muted); }
.summary-row strong, .infra-list strong { text-align: right; }
.infra-actions { display: inline-flex; align-items: center; gap: 12px; }
.infra-actions strong.is-online { color: var(--color-success); }
.infra-actions strong.is-warning { color: var(--color-warning); }
@media (max-width: 900px) { .dashboard-grid { grid-template-columns: 1fr; } }
</style>
