<template>
  <div class="lottery-workbench">
    <section class="page-header lottery-header">
      <div>
        <h1 class="page-title">超级大乐透工作台</h1>
        <div class="page-subtitle">开奖、数据健康、统计信号和选号工具的统一入口</div>
      </div>
      <div class="lottery-actions">
        <RouterLink to="/lottery/dlt/draws" class="back-link">历史开奖</RouterLink>
        <RouterLink to="/lottery/dlt/data-health" class="back-link">数据健康</RouterLink>
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

    <section class="hero-grid">
      <div class="panel latest-draw-panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">最新开奖</h2>
            <span class="panel-meta">{{ latestDrawDate }}</span>
          </div>
          <RouterLink to="/lottery/dlt/draws" class="panel-link">查看全部</RouterLink>
        </div>
        <div class="panel-body latest-draw-body">
          <div v-if="latestDraw" class="latest-draw">
            <div class="issue-badge">第 {{ latestDraw.issue_no }} 期</div>
            <div class="draw-line">
              <span class="draw-label">前区</span>
              <LotteryBall
                v-for="number in latestDraw.front_numbers"
                :key="`front-${number}`"
                :value="number"
                area="front"
              />
            </div>
            <div class="draw-line">
              <span class="draw-label back-label">后区</span>
              <LotteryBall
                v-for="number in latestDraw.back_numbers"
                :key="`back-${number}`"
                :value="number"
                area="back"
              />
            </div>
            <div class="draw-extra">
              <span>销售额 {{ formatMoney(latestDraw.sales_amount) }}</span>
              <span>奖池 {{ formatMoney(latestDraw.pool_amount) }}</span>
            </div>
          </div>
          <EmptyState
            v-else
            title="暂无开奖数据"
            description="点击立即同步后会拉取大乐透开奖历史。"
          />
        </div>
      </div>

      <div class="panel countdown-panel">
        <div class="panel-header">
          <h2 class="panel-title">下期开奖</h2>
          <span class="panel-meta">周一 / 周三 / 周六 21:10</span>
        </div>
        <div class="panel-body countdown-body">
          <div class="countdown-value">{{ nextDrawCountdown }}</div>
          <div class="countdown-meta">{{ nextDrawDateTime }}</div>
          <div class="countdown-note">倒计时用于提醒开奖时间，不代表任何预测信号。</div>
        </div>
      </div>
    </section>

    <div class="grid metrics overview-metrics">
      <MetricCard label="开奖数据" :value="drawTotal" :meta="coverageStatus" :delay="60" />
      <MetricCard label="数据范围" :value="coverageYears" :meta="coverageYearSpan" :delay="120" />
      <MetricCard label="同步状态" :value="syncStatusText" :meta="syncMeta" :delay="180" />
      <MetricCard label="统计样本" :value="statisticsSampleSize" :meta="statisticsLatestIssue" :delay="240" />
    </div>

    <section class="panel signal-panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">统计信号</h2>
          <span class="panel-meta">基于最近 {{ lottery.statistics?.sample_size ?? 0 }} 期</span>
        </div>
        <RouterLink to="/lottery/dlt/statistics" class="panel-link">完整统计</RouterLink>
      </div>
      <div class="panel-body signal-grid">
        <NumberSignal title="前区热号" :items="frontHotNumbers" />
        <NumberSignal title="前区冷号" :items="frontColdNumbers" />
        <NumberSignal title="后区热号" :items="backHotNumbers" area="back" />
        <NumberSignal title="后区冷号" :items="backColdNumbers" area="back" />
      </div>
    </section>

    <section class="tool-grid">
      <RouterLink
        v-for="item in toolCards"
        :key="item.path"
        :to="item.path"
        class="tool-card panel"
      >
        <div class="tool-card-kicker">{{ item.kicker }}</div>
        <div class="tool-card-title">{{ item.title }}</div>
        <p>{{ item.description }}</p>
        <span>{{ item.action }}</span>
      </RouterLink>
    </section>

    <section class="panel data-range-panel">
      <div class="panel-header">
        <h2 class="panel-title">数据范围</h2>
        <span class="panel-meta">{{ coverageStatus }}</span>
      </div>
      <div class="panel-body data-range-grid">
        <InfoBlock label="最新期号" :value="coverageLatestIssue" :meta="coverageLatestDate" />
        <InfoBlock label="最早期号" :value="coverageEarliestIssue" :meta="coverageEarliestDate" />
        <InfoBlock label="覆盖年份" :value="coverageYears" :meta="coverageDescription" />
        <InfoBlock label="变更统计" :value="syncChangeSummary" meta="新增 / 更新 / 跳过" />
      </div>
    </section>

    <section class="panel sync-panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">同步与回填</h2>
          <span class="panel-meta">{{ schedulerSummary }}</span>
        </div>
        <RouterLink to="/lottery/dlt/data-health" class="panel-link">同步明细</RouterLink>
      </div>
      <div class="panel-body sync-grid">
        <InfoBlock label="自动调度" :value="schedulerStatusText" :meta="schedulerMeta" />
        <InfoBlock label="下次运行" :value="nextRunLabel" :meta="schedulerTimezone" />
        <InfoBlock label="同步批量" :value="syncPageSize" meta="每次拉取期数" />
        <InfoBlock label="最近任务" :value="latestRunLabel" :meta="latestRunMeta" />
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
        <div class="backfill-summary">{{ backfillSummary }}</div>
        <div v-if="backfillProgressText" class="backfill-progress">
          <span>{{ backfillProgressText }}</span>
          <el-tag v-if="backfillProgressTag" :type="backfillProgressTag" effect="dark">
            {{ backfillProgressStatus }}
          </el-tag>
        </div>
      </div>
    </section>

    <section class="panel rule-panel">
      <div class="panel-header">
        <h2 class="panel-title">规则速览</h2>
        <a v-if="lottery.rule?.official_url" :href="lottery.rule.official_url" target="_blank">
          官方来源
        </a>
      </div>
      <div class="panel-body rule-summary">
        <InfoBlock label="前区" :value="frontRule" :meta="frontMeta" />
        <InfoBlock label="后区" :value="backRule" :meta="backMeta" />
        <InfoBlock label="基本投注" :value="basePrice" meta="每注价格" />
        <InfoBlock label="追加投注" :value="addonPrice" :meta="addonMeta" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, type PropType } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import type { LotteryDraw, LotteryNumberFrequency } from '@/plugins/lottery/api';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import { lotterySyncSourceLabel } from '@/plugins/lottery/sourceLabels';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const now = ref(new Date());
const backfillStartPage = ref(2);
const backfillPageCount = ref(5);
const backfillPageSize = ref(100);
const backfillForce = ref(false);
let countdownTimer: number | undefined;
let backfillPollTimer: number | undefined;

const InfoBlock = defineComponent({
  name: 'InfoBlock',
  props: {
    label: { type: String, required: true },
    value: { type: String, required: true },
    meta: { type: String, required: true },
  },
  setup(props) {
    return () =>
      h('div', { class: 'info-block' }, [
        h('div', { class: 'info-label' }, props.label),
        h('div', { class: 'info-value' }, props.value),
        h('div', { class: 'info-meta' }, props.meta),
      ]);
  },
});

const NumberSignal = defineComponent({
  name: 'NumberSignal',
  props: {
    title: { type: String, required: true },
    items: { type: Array as PropType<LotteryNumberFrequency[]>, required: true },
    area: { type: String as PropType<'front' | 'back'>, default: 'front' },
  },
  setup(props) {
    return () =>
      h('div', { class: 'number-signal' }, [
        h('div', { class: 'signal-title' }, props.title),
        props.items.length
          ? h(
              'div',
              { class: 'signal-balls' },
              props.items.map((item) =>
                h('div', { class: 'signal-ball-wrap', key: `${props.area}-${item.number}` }, [
                  h(LotteryBall, { value: item.number, area: props.area }),
                  h('small', `x${item.count}`),
                ]),
              ),
            )
          : h('div', { class: 'signal-empty' }, '等待统计数据'),
      ]);
  },
});

const toolCards = [
  {
    title: '选号推荐',
    kicker: 'Recommendation',
    description: '结合历史同期、冷热、遗漏和结构平衡生成 5 组候选号码。',
    action: '生成推荐',
    path: '/lottery/dlt/recommendations',
  },
  {
    title: '组合回测',
    kicker: 'Backtest',
    description: '把一组 5+2 放回历史开奖库，查看历史命中和固定奖回报。',
    action: '开始回测',
    path: '/lottery/dlt/backtest',
  },
  {
    title: '胆拖辅助',
    kicker: 'Dantuo',
    description: '管理定胆、拖码、杀号和成本，辅助构造复式/胆拖方案。',
    action: '配置方案',
    path: '/lottery/dlt/dantuo',
  },
  {
    title: '历史同期',
    kicker: 'Same Period',
    description: '按期号后三位对比往年同期开奖，观察重复号码和结构。',
    action: '查看同期',
    path: '/lottery/dlt/same-period',
  },
  {
    title: '模拟选号',
    kicker: 'Monte Carlo',
    description: '用随机模拟和理论概率快速生成候选组合，作为娱乐参考。',
    action: '运行模拟',
    path: '/lottery/dlt/simulation',
  },
  {
    title: '热力图',
    kicker: 'Heatmap',
    description: '查看号码近期出现密度、遗漏和热冷变化。',
    action: '打开热图',
    path: '/lottery/dlt/heatmap',
  },
];

const latestDraw = computed<LotteryDraw | null>(() => lottery.draws?.items[0] ?? null);
const latestDrawDate = computed(() =>
  latestDraw.value ? `${latestDraw.value.draw_date} 开奖` : '等待同步',
);
const nextDrawAt = computed(() => calculateNextDltDraw(now.value));
const nextDrawDateTime = computed(() => formatDateTime(nextDrawAt.value.toISOString()));
const nextDrawCountdown = computed(() =>
  formatCountdown(nextDrawAt.value.getTime() - now.value.getTime()),
);
const frontRule = computed(() =>
  lottery.rule ? `${lottery.rule.front.min}-${lottery.rule.front.max}` : '--',
);
const backRule = computed(() =>
  lottery.rule ? `${lottery.rule.back.min}-${lottery.rule.back.max}` : '--',
);
const frontMeta = computed(() => `${lottery.rule?.front.count ?? 5} 个号码`);
const backMeta = computed(() => `${lottery.rule?.back.count ?? 2} 个号码`);
const basePrice = computed(() => (lottery.rule ? `${lottery.rule.base_price} 元` : '--'));
const addonPrice = computed(() => (lottery.rule ? `${lottery.rule.addon_price} 元` : '--'));
const addonMeta = computed(() => (lottery.rule?.addon_supported ? '支持追加' : '不支持追加'));
const drawTotal = computed(() => String(lottery.draws?.pagination.total ?? 0));
const coverageLatestIssue = computed(() => lottery.drawCoverage?.latest_issue_no ?? '--');
const coverageLatestDate = computed(() =>
  lottery.drawCoverage?.latest_draw_date ?? '等待同步',
);
const coverageEarliestIssue = computed(() => lottery.drawCoverage?.earliest_issue_no ?? '--');
const coverageEarliestDate = computed(() =>
  lottery.drawCoverage?.earliest_draw_date ?? '等待回填',
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
const coverageStatus = computed(() => lottery.drawCoverage?.status_label ?? '读取中');
const coverageDescription = computed(
  () => lottery.drawCoverage?.description ?? '正在读取数据库覆盖范围。',
);
const statisticsSampleSize = computed(() => String(lottery.statistics?.sample_size ?? 0));
const statisticsLatestIssue = computed(() =>
  lottery.statistics?.latest_issue_no ? `最新样本 ${lottery.statistics.latest_issue_no}` : '等待统计',
);
const frontHotNumbers = computed(() => lottery.statistics?.hot_numbers.front.slice(0, 6) ?? []);
const frontColdNumbers = computed(() => lottery.statistics?.cold_numbers.front.slice(0, 6) ?? []);
const backHotNumbers = computed(() => lottery.statistics?.hot_numbers.back.slice(0, 4) ?? []);
const backColdNumbers = computed(() => lottery.statistics?.cold_numbers.back.slice(0, 4) ?? []);
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
  if (!lottery.latestSyncRun) return '暂无同步记录';
  const source = lotterySyncSourceLabel(lottery.latestSyncRun.source);
  return `${source} · ${lottery.latestSyncRun.sync_type}`;
});
const syncChangeSummary = computed(() => {
  const run = lottery.latestSyncRun;
  if (!run) return '--';
  return `${run.inserted_count} / ${run.updated_count} / ${run.skipped_count}`;
});
const schedulerStatusText = computed(() => {
  if (!lottery.syncStatus) return '读取中';
  if (!lottery.syncStatus.enabled) return '已关闭';
  return lottery.syncStatus.running ? '运行中' : '待命';
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
const latestBackfillTask = computed(
  () => lottery.syncRuns?.items.find((run) => run.sync_type === 'backfill') ?? null,
);
const backfillSummary = computed(() => {
  const run = lottery.latestBackfillRun;
  if (lottery.latestBackfillJob) return lottery.latestBackfillJob.message;
  if (!run) return '历史回填用于补齐更早年份数据，完成后同期分析和统计样本会更完整。';
  return [
    `状态 ${run.status}`,
    `执行 ${run.executed_pages}/${run.page_count} 页`,
    `新增 ${run.inserted_count}`,
    `更新 ${run.updated_count}`,
    `跳过 ${run.skipped_count}`,
  ].join(' · ');
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
  if (status === 'running') return '运行中';
  if (status === 'success') return '成功';
  if (status === 'partial_success') return '部分成功';
  if (status === 'failed') return '失败';
  return status ?? '';
});
const backfillProgressTag = computed((): 'success' | 'warning' | 'danger' | 'info' | '' => {
  const status = latestBackfillTask.value?.status;
  if (!status && lottery.latestBackfillJob) return 'info';
  if (status === 'success') return 'success';
  if (status === 'partial_success' || status === 'running') return 'warning';
  if (status === 'failed') return 'danger';
  return '';
});

function formatMoney(value: string | null): string {
  if (!value) return '--';
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}

function formatDateTime(value: string | null): string {
  if (!value) return '--';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function calculateNextDltDraw(current: Date): Date {
  const drawWeekdays = [1, 3, 6];
  const drawHour = 21;
  const drawMinute = 10;

  for (let offset = 0; offset <= 7; offset += 1) {
    const candidate = new Date(current);
    candidate.setDate(current.getDate() + offset);
    candidate.setHours(drawHour, drawMinute, 0, 0);
    if (drawWeekdays.includes(candidate.getDay()) && candidate.getTime() > current.getTime()) {
      return candidate;
    }
  }

  const fallback = new Date(current);
  fallback.setDate(current.getDate() + 1);
  fallback.setHours(drawHour, drawMinute, 0, 0);
  return fallback;
}

function formatCountdown(milliseconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const clock = [hours, minutes, seconds].map((item) => String(item).padStart(2, '0')).join(':');
  return days > 0 ? `${days}天 ${clock}` : clock;
}

async function handleSync(): Promise<void> {
  await lottery.syncNow();
  await lottery.loadStatistics();
}

async function handleBackfill(): Promise<void> {
  await lottery.backfill({
    start_page: backfillStartPage.value,
    page_count: backfillPageCount.value,
    page_size: backfillPageSize.value,
    force: backfillForce.value,
  });
  startBackfillPolling();
}

async function loadWorkbench(): Promise<void> {
  await lottery.loadOverview();
  await lottery.loadStatistics();
}

onMounted(() => {
  void loadWorkbench();
  countdownTimer = window.setInterval(() => {
    now.value = new Date();
  }, 1000);
});

onBeforeUnmount(() => {
  if (countdownTimer !== undefined) {
    window.clearInterval(countdownTimer);
  }
  stopBackfillPolling();
});

function startBackfillPolling(): void {
  stopBackfillPolling();
  backfillPollTimer = window.setInterval(() => {
    void refreshBackfillProgress();
  }, 3000);
  void refreshBackfillProgress();
}

function stopBackfillPolling(): void {
  if (backfillPollTimer !== undefined) {
    window.clearInterval(backfillPollTimer);
    backfillPollTimer = undefined;
  }
}

async function refreshBackfillProgress(): Promise<void> {
  await Promise.all([lottery.loadSyncState(), lottery.loadDraws(), lottery.loadDrawCoverage()]);
  const runningBackfill = lottery.syncRuns?.items.some(
    (run) => run.sync_type === 'backfill' && run.status === 'running',
  );
  lottery.syncing = Boolean(runningBackfill);
  if (!runningBackfill) {
    stopBackfillPolling();
    await lottery.loadStatistics();
  }
}
</script>

<style scoped>
.lottery-workbench {
  display: grid;
  gap: 16px;
}

.lottery-header {
  align-items: center;
}

.lottery-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.back-link,
.panel-link,
.panel-header a,
.panel-meta {
  color: var(--color-primary);
  font-size: 13px;
}

.back-link {
  border: 1px solid rgba(56, 189, 248, 0.24);
  border-radius: 8px;
  color: var(--color-muted);
  padding: 8px 12px;
}

.back-link:hover,
.panel-link:hover {
  color: var(--color-text);
}

.sync-alert {
  margin-top: -4px;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
  gap: 16px;
}

.latest-draw-panel,
.countdown-panel {
  min-height: 220px;
}

.latest-draw-body,
.countdown-body {
  height: calc(100% - 49px);
}

.latest-draw {
  display: grid;
  gap: 14px;
}

.issue-badge {
  width: fit-content;
  border: 1px solid rgba(56, 189, 248, 0.28);
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.1);
  color: #bae6fd;
  font-size: 13px;
  font-weight: 700;
  padding: 7px 10px;
}

.draw-line {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.draw-label {
  color: var(--color-muted);
  font-size: 12px;
  min-width: 34px;
}

.back-label {
  color: #fbbf24;
}

.draw-extra {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--color-muted);
  font-size: 12px;
}

.countdown-body {
  display: grid;
  align-content: center;
  gap: 10px;
}

.countdown-value {
  color: #d8f7ff;
  font-variant-numeric: tabular-nums;
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
  text-shadow: 0 0 24px rgba(56, 189, 248, 0.24);
}

.countdown-meta,
.countdown-note {
  color: var(--color-muted);
  font-size: 13px;
}

.overview-metrics {
  margin-top: 0;
}

.signal-grid,
.data-range-grid,
.sync-grid,
.rule-summary {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.number-signal,
.info-block {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  min-width: 0;
  padding: 12px;
}

.signal-title,
.info-label {
  color: var(--color-muted);
  font-size: 12px;
}

.signal-balls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.signal-ball-wrap {
  align-items: center;
  display: grid;
  gap: 4px;
  justify-items: center;
}

.signal-ball-wrap small,
.signal-empty,
.info-meta {
  color: var(--color-muted);
  font-size: 12px;
}

.signal-empty {
  margin-top: 10px;
}

.info-value {
  margin-top: 8px;
  overflow-wrap: anywhere;
  font-size: 20px;
  font-weight: 720;
}

.info-meta {
  line-height: 1.45;
  margin-top: 6px;
}

.tool-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.tool-card {
  display: grid;
  gap: 8px;
  padding: 14px;
  transition:
    border-color 160ms ease,
    transform 160ms ease,
    background 160ms ease;
}

.tool-card:hover {
  border-color: rgba(56, 189, 248, 0.42);
  background: rgba(56, 189, 248, 0.06);
  transform: translateY(-2px);
}

.tool-card-kicker {
  color: #7dd3fc;
  font-size: 11px;
  font-weight: 760;
  text-transform: uppercase;
}

.tool-card-title {
  font-size: 16px;
  font-weight: 760;
}

.tool-card p {
  margin: 0;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.55;
}

.tool-card span {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 700;
}

.backfill-box {
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 10px;
  margin-top: 14px;
  padding: 14px 16px 16px;
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
.backfill-summary,
.backfill-progress {
  color: var(--color-muted);
  font-size: 12px;
}

.backfill-progress {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 1120px) {
  .hero-grid,
  .tool-grid {
    grid-template-columns: 1fr 1fr;
  }

  .signal-grid,
  .data-range-grid,
  .sync-grid,
  .rule-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .lottery-header,
  .lottery-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .hero-grid,
  .tool-grid,
  .signal-grid,
  .data-range-grid,
  .sync-grid,
  .rule-summary {
    grid-template-columns: 1fr;
  }

  .countdown-value {
    font-size: 30px;
  }

  .backfill-controls,
  .backfill-field {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
