<template>
  <div>
    <section class="page-header lottery-header">
      <div>
        <h1 class="page-title">超级大乐透</h1>
        <div class="page-subtitle">规则、开奖同步状态与基础分析入口</div>
      </div>
      <div class="lottery-actions">
        <div class="lottery-tabs">
          <RouterLink to="/lottery/dlt">概览</RouterLink>
          <RouterLink to="/lottery/dlt/draws">历史开奖</RouterLink>
          <RouterLink to="/lottery/dlt/statistics">统计</RouterLink>
          <RouterLink to="/lottery/dlt/omissions">遗漏</RouterLink>
          <RouterLink to="/lottery/dlt/heatmap">热力图</RouterLink>
          <RouterLink to="/lottery/dlt/same-period">历史同期</RouterLink>
        </div>
        <el-button
          type="primary"
          :icon="Refresh"
          :loading="lottery.syncing"
          @click="handleSync"
        >
          立即同步
        </el-button>
      </div>
    </section>

    <DisclaimerAlert v-if="lottery.disclaimer" :text="lottery.disclaimer" />

    <el-alert
      v-if="lottery.syncError"
      class="sync-alert"
      type="warning"
      :closable="false"
      :title="lottery.syncError"
      show-icon
    />

    <div class="grid metrics overview-metrics">
      <MetricCard label="前区" :value="frontRule" :meta="frontMeta" />
      <MetricCard label="后区" :value="backRule" :meta="backMeta" />
      <MetricCard label="开奖数据" :value="drawTotal" meta="已入库期数" />
      <MetricCard label="同步状态" :value="syncStatusText" :meta="syncMeta" />
    </div>

    <section class="panel sync-panel">
      <div class="panel-header">
        <h2 class="panel-title">数据同步</h2>
        <span class="panel-meta">{{ schedulerSummary }}</span>
      </div>
      <div class="panel-body sync-grid">
        <div class="sync-block">
          <div class="sync-label">自动调度</div>
          <div class="sync-value">
            <el-tag :type="schedulerTagType" effect="dark">{{ schedulerStatusText }}</el-tag>
          </div>
          <div class="sync-meta">{{ schedulerMeta }}</div>
        </div>
        <div class="sync-block">
          <div class="sync-label">下次运行</div>
          <div class="sync-value compact-value">{{ nextRunLabel }}</div>
          <div class="sync-meta">{{ schedulerTimezone }}</div>
        </div>
        <div class="sync-block">
          <div class="sync-label">同步批量</div>
          <div class="sync-value">{{ syncPageSize }}</div>
          <div class="sync-meta">每次拉取期数</div>
        </div>
        <div class="sync-block">
          <div class="sync-label">最近任务</div>
          <div class="sync-value">{{ latestRunLabel }}</div>
          <div class="sync-meta">{{ latestRunMeta }}</div>
        </div>
        <div class="sync-block">
          <div class="sync-label">变更统计</div>
          <div class="sync-value">{{ syncChangeSummary }}</div>
          <div class="sync-meta">新增 / 更新 / 跳过</div>
        </div>
        <div class="sync-block">
          <div class="sync-label">最新期号</div>
          <div class="sync-value">{{ lottery.latestSyncRun?.latest_issue_no ?? '--' }}</div>
          <div class="sync-meta">{{ latestIssueSourceMeta }}</div>
        </div>
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
          <el-button
            type="primary"
            plain
            :loading="lottery.syncing"
            @click="handleBackfill"
          >
            历史回填
          </el-button>
        </div>
        <div class="backfill-summary">
          {{ backfillSummary }}
        </div>
      </div>
    </section>

    <section class="panel rule-panel">
      <div class="panel-header">
        <h2 class="panel-title">当前规则版本</h2>
        <a v-if="lottery.rule?.official_url" :href="lottery.rule.official_url" target="_blank">
          官方来源
        </a>
      </div>
      <div class="panel-body">
        <div v-if="lottery.rule" class="tier-grid">
          <div v-for="tier in lottery.rule.prize_tiers" :key="`${tier.tier}-${tier.description}`">
            <strong>{{ tier.tier_name }}</strong>
            <span>{{ tier.description }}</span>
          </div>
        </div>
        <EmptyState
          v-else
          title="规则未加载"
          description="后端启动后会自动写入当前规则种子数据。"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import {
  lotterySyncSourceDescription,
  lotterySyncSourceLabel,
} from '@/plugins/lottery/sourceLabels';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const backfillStartPage = ref(2);
const backfillPageCount = ref(5);
const backfillPageSize = ref(100);
const backfillForce = ref(false);

const frontRule = computed(() =>
  lottery.rule ? `${lottery.rule.front.min}-${lottery.rule.front.max}` : '--',
);
const backRule = computed(() =>
  lottery.rule ? `${lottery.rule.back.min}-${lottery.rule.back.max}` : '--',
);
const frontMeta = computed(() => `${lottery.rule?.front.count ?? 5} 个号码`);
const backMeta = computed(() => `${lottery.rule?.back.count ?? 2} 个号码`);
const drawTotal = computed(() => String(lottery.draws?.pagination.total ?? 0));
const syncStatusText = computed(() => {
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
const syncMeta = computed(() =>
  lottery.latestSyncRun?.finished_at
    ? formatDateTime(lottery.latestSyncRun.finished_at)
    : '等待首次同步',
);
const latestRunLabel = computed(() =>
  lottery.latestSyncRun ? `#${lottery.latestSyncRun.run_id}` : '--',
);
const latestRunMeta = computed(() => {
  if (!lottery.latestSyncRun) return '尚无同步记录';
  const source = lotterySyncSourceLabel(lottery.latestSyncRun.source);
  return `${source} · ${lottery.latestSyncRun.sync_type}`;
});
const latestIssueSourceMeta = computed(() =>
  lotterySyncSourceDescription(lottery.latestSyncRun?.source),
);
const syncChangeSummary = computed(() => {
  const run = lottery.latestSyncRun;
  if (!run) return '--';
  return `${run.inserted_count} / ${run.updated_count} / ${run.skipped_count}`;
});
const schedulerStatusText = computed(() => {
  if (!lottery.syncStatus) return '读取中';
  if (!lottery.syncStatus.enabled) return '已关闭';
  return lottery.syncStatus.running ? '运行中' : '未运行';
});
const schedulerTagType = computed((): 'success' | 'warning' | 'info' => {
  if (!lottery.syncStatus) return 'info';
  if (!lottery.syncStatus.enabled) return 'info';
  return lottery.syncStatus.running ? 'success' : 'warning';
});
const schedulerMeta = computed(() => {
  if (!lottery.syncStatus) return '等待后端状态';
  return `Cron ${lottery.syncStatus.cron}`;
});
const schedulerSummary = computed(() => {
  if (!lottery.syncStatus) return '自动同步状态加载中';
  return lottery.syncStatus.enabled
    ? `自动同步已启用 · ${lottery.syncStatus.cron}`
    : '自动同步已关闭';
});
const schedulerTimezone = computed(() => lottery.syncStatus?.timezone ?? 'Asia/Shanghai');
const syncPageSize = computed(() => String(lottery.syncStatus?.page_size ?? 100));
const nextRunLabel = computed(() =>
  lottery.syncStatus?.next_run_at ? formatDateTime(lottery.syncStatus.next_run_at) : '--',
);
const backfillSummary = computed(() => {
  const run = lottery.latestBackfillRun;
  if (!run) return '历史回填用于补齐更早年份数据，完成后历史同期会显示更多结果。';
  return [
    `状态 ${run.status}`,
    `执行 ${run.executed_pages}/${run.page_count} 页`,
    `新增 ${run.inserted_count}`,
    `更新 ${run.updated_count}`,
    `跳过 ${run.skipped_count}`,
  ].join(' · ');
});

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

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
}

onMounted(() => {
  void lottery.loadOverview();
});
</script>

<style scoped>
.lottery-header {
  align-items: center;
}

.lottery-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.overview-metrics {
  margin-top: 16px;
}

.lottery-tabs {
  display: flex;
  gap: 8px;
}

.lottery-tabs a {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 8px;
  color: var(--color-muted);
  padding: 8px 12px;
}

.lottery-tabs a.router-link-active {
  border-color: rgba(56, 189, 248, 0.5);
  color: var(--color-primary);
}

.sync-alert,
.sync-panel,
.rule-panel {
  margin-top: 16px;
}

.panel-header a,
.panel-meta {
  color: var(--color-primary);
  font-size: 13px;
}

.sync-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.backfill-box {
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 10px;
  margin-top: 14px;
  padding-top: 14px;
}

.backfill-controls {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.backfill-field {
  align-items: center;
  display: flex;
  gap: 8px;
}

.backfill-field span,
.backfill-summary {
  color: var(--color-muted);
  font-size: 12px;
}

.sync-block {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.sync-label {
  color: var(--color-muted);
  font-size: 12px;
}

.sync-value {
  margin-top: 8px;
  font-size: 20px;
  font-weight: 720;
}

.compact-value {
  font-size: 16px;
  line-height: 1.35;
}

.sync-meta {
  margin-top: 6px;
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.tier-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.tier-grid div {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.tier-grid strong {
  display: block;
  margin-bottom: 6px;
}

.tier-grid span {
  color: var(--color-muted);
  font-size: 13px;
}

@media (max-width: 860px) {
  .lottery-header,
  .lottery-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .sync-grid,
  .tier-grid {
    grid-template-columns: 1fr;
  }

  .backfill-controls,
  .backfill-field {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
