<template>
  <div>
    <section class="page-header data-health-header">
      <div>
        <h1 class="page-title">数据健康</h1>
        <div class="page-subtitle">集中查看大乐透数据范围、同步任务、回填进度和异常状态</div>
      </div>
      <div class="health-actions">
        <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
        <el-button type="primary" :icon="Refresh" :loading="lottery.syncing" @click="handleSync">
          立即同步
        </el-button>
      </div>
    </section>

    <el-alert
      v-if="lottery.syncError"
      class="health-alert"
      type="warning"
      :closable="false"
      :title="lottery.syncError"
      show-icon
    />

    <div class="grid metrics health-metrics">
      <MetricCard label="入库期数" :value="drawTotal" :meta="coverageStatus" />
      <MetricCard label="数据范围" :value="coverageRange" :meta="coverageDates" />
      <MetricCard label="同步状态" :value="syncStatusText" :meta="syncMeta" />
      <MetricCard label="下次自动同步" :value="nextRunLabel" :meta="schedulerMeta" />
    </div>

    <section class="panel health-panel">
      <div class="panel-header">
        <h2 class="panel-title">数据范围</h2>
        <span class="panel-meta">{{ coverageDescription }}</span>
      </div>
      <div class="health-grid">
        <InfoBlock label="最新期号" :value="coverageLatestIssue" :meta="coverageLatestDate" />
        <InfoBlock label="最早期号" :value="coverageEarliestIssue" :meta="coverageEarliestDate" />
        <InfoBlock label="覆盖年份" :value="coverageYears" :meta="coverageYearSpan" />
        <InfoBlock label="数据判断" :value="coverageStatus" :meta="coverageDescription" compact />
      </div>
    </section>

    <section class="panel health-panel">
      <div class="panel-header">
        <h2 class="panel-title">同步与回填</h2>
        <span class="panel-meta">{{ schedulerSummary }}</span>
      </div>
      <div class="health-grid sync-grid">
        <InfoBlock label="自动调度" :value="schedulerStatusText" :meta="schedulerMeta" />
        <InfoBlock label="同步批量" :value="syncPageSize" meta="每次拉取期数" />
        <InfoBlock label="最近任务" :value="latestRunLabel" :meta="latestRunMeta" />
        <InfoBlock label="变更统计" :value="syncChangeSummary" meta="新增 / 更新 / 跳过" />
      </div>

      <div class="backfill-box">
        <div class="backfill-controls">
          <div class="backfill-field">
            <span>起始页</span>
            <el-input-number v-model="backfillStartPage" :min="1" :max="200" size="small" />
          </div>
          <div class="backfill-field">
            <span>页数</span>
            <el-input-number v-model="backfillPageCount" :min="1" :max="20" size="small" />
          </div>
          <div class="backfill-field">
            <span>每页</span>
            <el-input-number
              v-model="backfillPageSize"
              :min="20"
              :max="500"
              :step="20"
              size="small"
            />
          </div>
          <el-checkbox v-model="backfillForce">覆盖更新</el-checkbox>
          <el-button type="primary" plain :loading="lottery.syncing" @click="handleBackfill">
            后台回填
          </el-button>
        </div>
        <div class="backfill-summary">{{ backfillSummary }}</div>
        <div v-if="backfillProgressText" class="backfill-progress">
          <span>{{ backfillProgressText }}</span>
          <el-tag v-if="backfillProgressTag" :type="backfillProgressTag" effect="dark">
            {{ backfillProgressStatus }}
          </el-tag>
        </div>
      </div>
    </section>

    <section class="panel health-panel">
      <div class="panel-header">
        <h2 class="panel-title">同步历史</h2>
        <span class="panel-meta">最近 {{ lottery.syncRuns?.items.length ?? 0 }} 次</span>
      </div>
      <el-table v-if="lottery.syncRuns?.items.length" :data="lottery.syncRuns.items">
        <el-table-column prop="run_id" label="任务" width="90" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="syncTagType(row.status)" effect="dark">
              {{ syncStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sync_type" label="类型" width="110" />
        <el-table-column label="数据源" min-width="170">
          <template #default="{ row }">{{ lotterySyncSourceLabel(row.source) }}</template>
        </el-table-column>
        <el-table-column label="完成时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.finished_at) }}</template>
        </el-table-column>
        <el-table-column prop="latest_issue_no" label="最新期号" width="120" />
        <el-table-column label="新增/更新/跳过" width="150">
          <template #default="{ row }">
            {{ row.inserted_count }}/{{ row.updated_count }}/{{ row.skipped_count }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误" min-width="180" />
      </el-table>
      <EmptyState
        v-else
        title="暂无同步记录"
        description="手动同步、自动同步或后台回填执行后会在这里记录任务结果。"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import { lotterySyncSourceLabel } from '@/plugins/lottery/sourceLabels';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const backfillStartPage = ref(2);
const backfillPageCount = ref(5);
const backfillPageSize = ref(100);
const backfillForce = ref(false);
let pollTimer: number | undefined;

const drawTotal = computed(() => String(lottery.draws?.pagination.total ?? 0));
const coverageLatestIssue = computed(() => lottery.drawCoverage?.latest_issue_no ?? '--');
const coverageLatestDate = computed(() => lottery.drawCoverage?.latest_draw_date ?? '等待同步');
const coverageEarliestIssue = computed(() => lottery.drawCoverage?.earliest_issue_no ?? '--');
const coverageEarliestDate = computed(() => lottery.drawCoverage?.earliest_draw_date ?? '等待回填');
const coverageRange = computed(() => `${coverageEarliestIssue.value} - ${coverageLatestIssue.value}`);
const coverageDates = computed(() => `${coverageEarliestDate.value} / ${coverageLatestDate.value}`);
const coverageStatus = computed(() => lottery.drawCoverage?.status_label ?? '读取中');
const coverageDescription = computed(
  () => lottery.drawCoverage?.description ?? '正在读取数据库覆盖范围。',
);
const coverageYears = computed(() => {
  const coverage = lottery.drawCoverage;
  if (!coverage?.start_year || !coverage.end_year) return '--';
  return `${coverage.start_year} - ${coverage.end_year}`;
});
const coverageYearSpan = computed(() => {
  const span = lottery.drawCoverage?.year_span ?? 0;
  return span > 0 ? `约 ${span} 年数据` : '暂无覆盖年份';
});
const syncStatusText = computed(() => syncStatusLabel(lottery.latestSyncRun?.status ?? 'none'));
const syncMeta = computed(() =>
  lottery.latestSyncRun?.finished_at ? formatDateTime(lottery.latestSyncRun.finished_at) : '等待首次同步',
);
const schedulerSummary = computed(() => {
  if (!lottery.syncStatus) return '自动同步状态加载中';
  return lottery.syncStatus.enabled
    ? `自动同步已启用 · ${lottery.syncStatus.cron}`
    : '自动同步已关闭';
});
const schedulerStatusText = computed(() => {
  if (!lottery.syncStatus) return '读取中';
  if (!lottery.syncStatus.enabled) return '已关闭';
  return lottery.syncStatus.running ? '运行中' : '未运行';
});
const schedulerMeta = computed(() => {
  if (!lottery.syncStatus) return '等待后端状态';
  return `${lottery.syncStatus.timezone} · Cron ${lottery.syncStatus.cron}`;
});
const syncPageSize = computed(() => String(lottery.syncStatus?.page_size ?? 100));
const nextRunLabel = computed(() =>
  lottery.syncStatus?.next_run_at ? formatDateTime(lottery.syncStatus.next_run_at) : '--',
);
const latestRunLabel = computed(() =>
  lottery.latestSyncRun ? `#${lottery.latestSyncRun.run_id}` : '--',
);
const latestRunMeta = computed(() => {
  if (!lottery.latestSyncRun) return '尚无同步记录';
  return `${lotterySyncSourceLabel(lottery.latestSyncRun.source)} · ${lottery.latestSyncRun.sync_type}`;
});
const syncChangeSummary = computed(() => {
  const run = lottery.latestSyncRun;
  if (!run) return '--';
  return `${run.inserted_count} / ${run.updated_count} / ${run.skipped_count}`;
});
const latestBackfillTask = computed(
  () => lottery.syncRuns?.items.find((run) => run.sync_type === 'backfill') ?? null,
);
const backfillSummary = computed(() => {
  if (lottery.latestBackfillJob) return lottery.latestBackfillJob.message;
  return '后台回填用于补齐更早年份数据，任务开始后可留在本页查看进度。';
});
const backfillProgressText = computed(() => {
  const task = latestBackfillTask.value;
  if (!task && lottery.latestBackfillJob) {
    return `后台任务已排队：从第 ${lottery.latestBackfillJob.start_page} 页开始，计划执行 ${lottery.latestBackfillJob.page_count} 页。`;
  }
  if (!task) return '';
  const page = task.requested_page ? `第 ${task.requested_page} 页` : '回填页';
  return `最近回填任务 #${task.run_id} · ${page} · 新增 ${task.inserted_count} / 更新 ${task.updated_count} / 跳过 ${task.skipped_count}`;
});
const backfillProgressStatus = computed(() => {
  const status = latestBackfillTask.value?.status;
  if (!status && lottery.latestBackfillJob) return '已排队';
  return syncStatusLabel(status ?? '');
});
const backfillProgressTag = computed((): 'success' | 'warning' | 'danger' | 'info' | '' =>
  syncTagType(latestBackfillTask.value?.status ?? (lottery.latestBackfillJob ? 'queued' : '')),
);

async function handleSync(): Promise<void> {
  await lottery.syncNow();
}

async function handleBackfill(): Promise<void> {
  await lottery.backfill({
    start_page: backfillStartPage.value,
    page_count: backfillPageCount.value,
    page_size: backfillPageSize.value,
    force: backfillForce.value,
  });
  startPolling();
}

function startPolling(): void {
  stopPolling();
  pollTimer = window.setInterval(() => {
    void refreshProgress();
  }, 3000);
  void refreshProgress();
}

function stopPolling(): void {
  if (pollTimer !== undefined) {
    window.clearInterval(pollTimer);
    pollTimer = undefined;
  }
}

async function refreshProgress(): Promise<void> {
  await Promise.all([lottery.loadSyncState(), lottery.loadDraws(), lottery.loadDrawCoverage()]);
  const running = lottery.syncRuns?.items.some(
    (run) => run.sync_type === 'backfill' && run.status === 'running',
  );
  lottery.syncing = Boolean(running);
  if (!running) stopPolling();
}

function formatDateTime(value: string | null): string {
  if (!value) return '--';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function syncStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    none: '未同步',
    queued: '已排队',
    running: '同步中',
    success: '成功',
    partial_success: '部分成功',
    failed: '失败',
  };
  return labels[status] ?? status;
}

function syncTagType(status: string): 'success' | 'warning' | 'danger' | 'info' | '' {
  if (status === 'success') return 'success';
  if (status === 'partial_success' || status === 'running') return 'warning';
  if (status === 'failed') return 'danger';
  if (status === 'queued') return 'info';
  return status ? 'info' : '';
}

onMounted(() => {
  void lottery.loadOverview();
});

onBeforeUnmount(() => {
  stopPolling();
});

const InfoBlock = defineComponent({
  props: {
    label: {
      type: String,
      required: true,
    },
    value: {
      type: String,
      required: true,
    },
    meta: {
      type: String,
      required: true,
    },
    compact: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    return () =>
      h('div', { class: 'info-block' }, [
        h('div', { class: 'info-label' }, props.label),
        h('div', { class: ['info-value', props.compact ? 'compact-value' : ''] }, props.value),
        h('div', { class: 'info-meta' }, props.meta),
      ]);
  },
});
</script>

<style scoped>
.data-health-header,
.health-actions {
  align-items: center;
}

.health-actions {
  display: flex;
  flex-shrink: 0;
  gap: 12px;
}

.back-link,
.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.health-alert,
.health-metrics,
.health-panel {
  margin-top: 16px;
}

.health-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.sync-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.info-block {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.info-label,
.info-meta,
.backfill-field span,
.backfill-summary,
.backfill-progress {
  color: var(--color-muted);
  font-size: 12px;
}

.info-value {
  font-size: 20px;
  font-weight: 720;
  line-height: 1.3;
  margin-top: 8px;
}

.compact-value {
  font-size: 16px;
}

.info-meta {
  line-height: 1.45;
  margin-top: 6px;
  overflow-wrap: anywhere;
}

.backfill-box {
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 10px;
  margin-top: 14px;
  padding-top: 14px;
}

.backfill-controls,
.backfill-field,
.backfill-progress {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.backfill-field {
  gap: 8px;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.5);
  --el-table-text-color: var(--color-text);
  --el-table-header-text-color: var(--color-muted);
  --el-table-border-color: rgba(148, 163, 184, 0.14);
}

@media (max-width: 920px) {
  .data-health-header,
  .health-actions,
  .backfill-controls,
  .backfill-field {
    align-items: stretch;
    flex-direction: column;
  }

  .health-grid,
  .sync-grid {
    grid-template-columns: 1fr;
  }
}
</style>
