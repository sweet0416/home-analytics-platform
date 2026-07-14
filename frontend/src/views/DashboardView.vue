<template>
  <div>
    <section class="page-header">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <div class="page-subtitle">服务器、数据插件和任务状态的统一入口</div>
      </div>
    </section>

    <div class="grid metrics">
      <MetricCard label="API" :value="system.health?.status ?? '--'" meta="Backend health" />
      <MetricCard label="Database" :value="system.health?.database ?? '--'" meta="SQLite first" />
      <MetricCard label="Version" :value="system.health?.version ?? '--'" meta="Backend release" />
      <MetricCard label="Deploy" value="PVE Docker" meta="192.168.100.249" />
    </div>

    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-header">
          <h2 class="panel-title">大乐透摘要</h2>
          <RouterLink to="/lottery/dlt" class="panel-link">打开</RouterLink>
        </div>
        <div class="panel-body">
          <div class="summary-row">
            <span>当前规则</span>
            <strong>{{ lottery.rule?.rule_name ?? '未加载' }}</strong>
          </div>
          <div class="summary-row">
            <span>最新期号</span>
            <strong>{{ latestIssue }}</strong>
          </div>
          <div class="summary-row">
            <span>开奖数据</span>
            <strong>{{ lottery.draws?.pagination.total ?? 0 }}</strong>
          </div>
          <div class="summary-row">
            <span>同步状态</span>
            <strong>{{ syncStatus }}</strong>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h2 class="panel-title">基础设施</h2>
        </div>
        <div class="panel-body infra-list">
          <div><span>Docker</span><strong>预留</strong></div>
          <div><span>PVE</span><strong>预留</strong></div>
          <div><span>Scheduler</span><strong>{{ schedulerStatus }}</strong></div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';

import MetricCard from '@/components/metric/MetricCard.vue';
import { useLotteryStore } from '@/plugins/lottery/store';
import { useSystemStore } from '@/stores/system';

const system = useSystemStore();
const lottery = useLotteryStore();

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

onMounted(() => {
  void system.fetchHealth();
  void lottery.loadOverview();
});
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 16px;
  margin-top: 16px;
}

.panel-link {
  color: var(--color-primary);
  font-size: 13px;
}

.summary-row,
.infra-list div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  padding: 11px 0;
}

.summary-row:first-child,
.infra-list div:first-child {
  padding-top: 0;
}

.summary-row:last-child,
.infra-list div:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.summary-row span,
.infra-list span {
  color: var(--color-muted);
}

.summary-row strong,
.infra-list strong {
  text-align: right;
}

@media (max-width: 900px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
