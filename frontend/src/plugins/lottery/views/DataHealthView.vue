<template>
  <div>
    <section class="page-header data-health-header">
      <div>
        <h1 class="page-title">数据健康</h1>
        <div class="page-subtitle">集中查看大乐透数据范围、同步任务、回填进度和异常状态</div>
      </div>
      <div class="health-actions">
        <el-button type="primary" :icon="Refresh" :loading="lottery.syncing" @click="handleSync">
          立即同步
        </el-button>
      </div>
    </section>

    <DltModuleNav />

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
        <h2 class="panel-title">制度与数据阶段</h2>
        <div class="stage-actions">
          <span class="panel-meta">{{ stageQualityDescription }}</span>
          <el-button
            v-if="canRepairRuleBindings"
            size="small"
            type="primary"
            plain
            :loading="repairingStages"
            @click="handleRepairRuleBindings"
          >
            修复规则绑定
          </el-button>
        </div>
      </div>
      <div class="stage-layout">
        <article
          v-for="stage in lottery.dataStageReport?.stages ?? []"
          :key="stage.stage_code"
          class="stage-card"
        >
          <div class="stage-card-head">
            <strong>{{ stage.stage_name }}</strong>
            <el-tag effect="dark" :type="stageQualityTagType(stage.data_quality_level)">
              {{ stageQualityLabel }}
            </el-tag>
          </div>
          <div class="stage-meta">
            <span>{{ stage.earliest_issue_no }} - {{ stage.latest_issue_no }}</span>
            <span>{{ stage.earliest_draw_date }} / {{ stage.latest_draw_date }}</span>
            <span>{{ stage.draw_count }} 期 · {{ stage.data_source }}</span>
          </div>
          <p>{{ stage.description }}</p>
        </article>
        <div class="stage-side">
          <div class="stage-quality">
            <strong>{{ stageQualityLabel }}</strong>
            <span>{{ stageQualityDescription }}</span>
            <div class="quality-bars">
              <div v-for="item in qualityBars" :key="item.label" class="quality-row">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </div>
          <div class="source-list">
            <strong>来源占比</strong>
            <span
              v-for="source in lottery.dataStageReport?.source_summary ?? []"
              :key="source.source"
            >
              {{ source.source }} · {{ source.count }} 期 · {{ formatPercent(source.share) }}
            </span>
          </div>
        </div>
      </div>
      <div v-if="stageWarnings.length" class="stage-warnings">
        <el-tag
          v-for="warning in stageWarnings"
          :key="warning"
          effect="plain"
          type="warning"
        >
          {{ warning }}
        </el-tag>
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
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="sync-detail">
              <div class="sync-detail-header">
                <strong>同步明细</strong>
                <span>{{ syncDetailSummary(row) }}</span>
              </div>
              <div v-if="row.details?.length" class="sync-detail-grid">
                <div
                  v-for="group in syncDetailGroups(row)"
                  :key="group.action"
                  class="sync-detail-card"
                >
                  <div class="sync-detail-card-title">
                    <el-tag
                      :class="`sync-action-tag sync-action-${group.action}`"
                      :type="syncActionTagType(group.action)"
                      effect="dark"
                      size="small"
                    >
                      {{ syncActionLabel(group.action) }}
                    </el-tag>
                    <span>{{ group.items.length }} 期</span>
                  </div>
                  <div class="sync-issue-list">
                    <span
                      v-for="item in group.items"
                      :key="`${group.action}-${item.issue_no}`"
                      class="sync-issue-chip"
                    >
                      {{ item.issue_no }}
                      <small>{{ item.draw_date }}</small>
                    </span>
                  </div>
                </div>
              </div>
              <EmptyState
                v-else
                title="这条旧同步记录没有保存期号明细"
                description="从同步明细功能上线之后执行的同步或回填，会记录具体新增、更新和跳过的期号。"
              />
            </div>
          </template>
        </el-table-column>
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
            <div class="sync-counts">
              <el-tag size="small" type="success" effect="plain">
                新 {{ row.inserted_count }}
              </el-tag>
              <el-tag size="small" type="warning" effect="plain">
                更 {{ row.updated_count }}
              </el-tag>
              <el-tag size="small" type="info" effect="plain">
                跳 {{ row.skipped_count }}
              </el-tag>
            </div>
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
import { ElMessage } from 'element-plus';
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import type { LotterySyncRun, LotterySyncRunDetail } from '@/plugins/lottery/api';
import DltModuleNav from '@/plugins/lottery/components/DltModuleNav.vue';
import { lotterySyncSourceLabel } from '@/plugins/lottery/sourceLabels';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const backfillStartPage = ref(2);
const backfillPageCount = ref(5);
const backfillPageSize = ref(100);
const backfillForce = ref(false);
const repairingStages = ref(false);
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
const stageQualityLabel = computed(() => lottery.dataStageReport?.quality.label ?? '读取中');
const stageQualityDescription = computed(
  () => lottery.dataStageReport?.quality.description ?? '正在检查规则版本、来源和字段完整度。',
);
const stageWarnings = computed(() => lottery.dataStageReport?.warnings ?? []);
const canRepairRuleBindings = computed(
  () => (lottery.dataStageReport?.quality.rule_bound_rate ?? 1) < 1,
);
const qualityBars = computed(() => {
  const quality = lottery.dataStageReport?.quality;
  return [
    { label: '销量字段', value: formatPercent(quality?.sales_present_rate ?? 0) },
    { label: '奖池字段', value: formatPercent(quality?.pool_present_rate ?? 0) },
    { label: '规则绑定', value: formatPercent(quality?.rule_bound_rate ?? 0) },
  ];
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

async function handleRepairRuleBindings(): Promise<void> {
  repairingStages.value = true;
  try {
    const repairedCount = await lottery.repairDataStageBindings();
    ElMessage.success(`已修复 ${repairedCount} 期规则绑定`);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '规则绑定修复失败');
  } finally {
    repairingStages.value = false;
  }
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
  await Promise.all([
    lottery.loadSyncState(),
    lottery.loadDraws(),
    lottery.loadDrawCoverage(),
    lottery.loadDataStageReport(),
  ]);
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

function stageQualityTagType(level: string): 'success' | 'warning' | 'danger' | 'info' {
  if (level === 'good') return 'success';
  if (level === 'partial' || level === 'limited') return 'warning';
  if (level === 'empty') return 'info';
  return 'info';
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function syncActionLabel(action: string): string {
  const labels: Record<string, string> = {
    inserted: '新增',
    updated: '更新',
    skipped: '跳过',
    failed: '失败',
  };
  return labels[action] ?? action;
}

function syncActionTagType(action: string): 'success' | 'warning' | 'danger' | 'info' {
  if (action === 'inserted') return 'success';
  if (action === 'updated') return 'warning';
  if (action === 'failed') return 'danger';
  return 'info';
}

function syncDetailSummary(row: LotterySyncRun): string {
  if (!row.details?.length) return '无期号明细';
  return `共 ${row.details.length} 期，新增 ${row.inserted_count}，更新 ${row.updated_count}，跳过 ${row.skipped_count}`;
}

function syncDetailGroups(row: LotterySyncRun): Array<{
  action: string;
  items: LotterySyncRunDetail[];
}> {
  const order = ['inserted', 'updated', 'skipped', 'failed'];
  return order
    .map((action) => ({
      action,
      items: row.details.filter((item) => item.action === action),
    }))
    .filter((group) => group.items.length > 0);
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

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.stage-actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
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

.stage-layout {
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.6fr);
}

.stage-card,
.stage-quality,
.source-list {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 14px;
}

.stage-card-head {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.stage-card p,
.stage-meta,
.stage-quality span,
.source-list span {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.stage-card p {
  margin: 0;
}

.stage-meta,
.stage-side,
.source-list,
.quality-bars {
  display: grid;
  gap: 8px;
}

.quality-row {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.quality-row span {
  color: var(--color-muted);
  font-size: 12px;
}

.quality-row strong {
  color: var(--color-text);
  font-size: 13px;
}

.stage-warnings {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
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

.sync-counts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sync-detail {
  background: rgba(15, 23, 42, 0.36);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  margin: 4px 0;
  padding: 14px;
}

.sync-detail-header {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: space-between;
}

.sync-detail-header span {
  color: var(--color-muted);
  font-size: 13px;
}

.sync-detail-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.sync-detail-card {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 12px;
}

.sync-detail-card-title {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.sync-detail-card-title span {
  color: var(--color-muted);
  font-size: 12px;
}

.sync-action-tag {
  border-radius: 6px;
  font-weight: 700;
}

:deep(.sync-action-skipped) {
  background: rgba(56, 189, 248, 0.16);
  border-color: rgba(56, 189, 248, 0.48);
  color: #bae6fd !important;
}

.sync-issue-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sync-issue-chip {
  background: rgba(8, 47, 73, 0.32);
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-radius: 8px;
  color: #e0f2fe;
  display: grid;
  font-size: 12px;
  gap: 2px;
  min-width: 74px;
  padding: 7px 8px;
}

.sync-issue-chip small {
  color: #93c5fd;
  font-size: 11px;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.5);
  --el-table-text-color: var(--color-text);
  --el-table-header-text-color: var(--color-muted);
  --el-table-border-color: rgba(148, 163, 184, 0.14);
  --el-table-current-row-bg-color: rgba(56, 189, 248, 0.1);
  --el-table-expanded-cell-bg-color: rgba(2, 6, 23, 0.22);
  --el-table-row-hover-bg-color: rgba(56, 189, 248, 0.08);
}

:deep(.el-table__body tr.current-row > td.el-table__cell),
:deep(.el-table__body tr.hover-row > td.el-table__cell),
:deep(.el-table__body tr:hover > td.el-table__cell) {
  background-color: rgba(56, 189, 248, 0.08);
}

:deep(.el-table__body tr.expanded > td.el-table__cell) {
  background-color: rgba(56, 189, 248, 0.1);
}

:deep(.el-table__expanded-cell) {
  background-color: rgba(2, 6, 23, 0.22);
  box-shadow: inset 0 1px 0 rgba(148, 163, 184, 0.1);
}

:deep(.el-table__expand-icon) {
  color: var(--color-muted);
}

:deep(.el-table__expand-icon--expanded) {
  color: var(--color-primary);
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
  .sync-grid,
  .sync-detail-grid,
  .stage-layout {
    grid-template-columns: 1fr;
  }
}
</style>
