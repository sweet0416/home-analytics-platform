<template>
  <div>
    <section class="page-header omission-header">
      <div>
        <h1 class="page-title">遗漏分析</h1>
        <div class="page-subtitle">当前遗漏、最大遗漏、平均遗漏与单号走势</div>
      </div>
      <div class="omission-actions">
        <el-radio-group v-model="selectedArea" size="small" @change="handleAreaChange">
          <el-radio-button label="front">前区</el-radio-button>
          <el-radio-button label="back">后区</el-radio-button>
        </el-radio-group>
        <el-button :icon="Refresh" :loading="lottery.loading" @click="reloadOmissions">
          刷新
        </el-button>
      </div>
    </section>

    <DltModuleNav />

    <div class="grid metrics omission-metrics">
      <MetricCard label="样本期数" :value="sampleSize" :meta="sampleMeta" />
      <MetricCard label="最新期号" :value="latestIssue" meta="遗漏样本最新一期" />
      <MetricCard label="当前最高遗漏" :value="topCurrentMissing" :meta="topCurrentMeta" />
      <MetricCard label="历史最高遗漏" :value="topMaxMissing" :meta="topMaxMeta" />
    </div>

    <section class="panel omission-panel">
      <div class="panel-header">
        <h2 class="panel-title">号码遗漏排行</h2>
        <span class="table-meta">{{ areaLabel }} · 按当前遗漏降序</span>
      </div>
      <div class="panel-body omission-grid">
        <div class="omission-table-wrap">
          <el-table
            v-if="activeRows.length"
            :data="activeRows"
            class="omission-table"
            highlight-current-row
            row-key="number"
            @row-click="selectNumber"
          >
            <el-table-column label="号码" width="92">
              <template #default="{ row }">
                <LotteryBall :area="row.area" :value="row.number" />
              </template>
            </el-table-column>
            <el-table-column prop="current_missing" label="当前遗漏" sortable width="120" />
            <el-table-column prop="max_missing" label="最大遗漏" sortable width="120" />
            <el-table-column prop="average_missing" label="平均遗漏" sortable width="120" />
            <el-table-column prop="appearances" label="出现次数" sortable width="120" />
            <el-table-column prop="last_seen_issue_no" label="上次出现">
              <template #default="{ row }">
                <span>{{ row.last_seen_issue_no ?? '样本内未出现' }}</span>
              </template>
            </el-table-column>
          </el-table>
          <EmptyState
            v-else
            title="暂无遗漏数据"
            description="请先同步大乐透历史开奖数据。"
          />
        </div>

        <aside class="detail-panel">
          <div class="detail-heading">
            <span>当前号码</span>
            <LotteryBall
              v-if="lottery.omissionDetail"
              :area="lottery.omissionDetail.area"
              :value="lottery.omissionDetail.number"
            />
          </div>
          <div v-if="lottery.omissionDetail" class="detail-stats">
            <div>
              <span>当前遗漏</span>
              <strong>{{ lottery.omissionDetail.current_missing }}</strong>
            </div>
            <div>
              <span>最大遗漏</span>
              <strong>{{ lottery.omissionDetail.max_missing }}</strong>
            </div>
            <div>
              <span>平均遗漏</span>
              <strong>{{ lottery.omissionDetail.average_missing }}</strong>
            </div>
            <div>
              <span>出现次数</span>
              <strong>{{ lottery.omissionDetail.appearances }}</strong>
            </div>
          </div>
          <div ref="detailChartRef" class="detail-chart" />
          <div v-if="lottery.omissionDetail" class="hit-list">
            <h3>最近命中</h3>
            <div
              v-for="item in lottery.omissionDetail.hit_issues.slice(0, 8)"
              :key="item.issue_no"
              class="hit-row"
            >
              <strong>{{ item.issue_no }}</strong>
              <span>{{ item.draw_date }}</span>
            </div>
          </div>
        </aside>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import type { ECharts, EChartsOption } from 'echarts';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { chartTheme } from '@/charts/useChartTheme';
import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import DltModuleNav from '@/plugins/lottery/components/DltModuleNav.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import type { LotteryNumberOmission } from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

type BallArea = 'front' | 'back';

const lottery = useLotteryStore();
const selectedArea = ref<BallArea>('front');
const detailChartRef = ref<HTMLDivElement | null>(null);
let detailChart: ECharts | null = null;

const activeRows = computed(() => {
  const rows = selectedArea.value === 'front'
    ? lottery.omissionStatistics?.front ?? []
    : lottery.omissionStatistics?.back ?? [];
  return [...rows].sort(
    (left, right) =>
      right.current_missing - left.current_missing ||
      right.max_missing - left.max_missing ||
      left.number - right.number,
  );
});
const areaLabel = computed(() => (selectedArea.value === 'front' ? '前区' : '后区'));
const sampleSize = computed(() => String(lottery.omissionStatistics?.sample_size ?? 0));
const sampleMeta = computed(() => `请求最近 ${lottery.omissionStatistics?.requested_limit ?? 100} 期`);
const latestIssue = computed(() => lottery.omissionStatistics?.latest_issue_no ?? '--');
const topCurrent = computed(() => activeRows.value[0] ?? null);
const topMax = computed(() =>
  [...activeRows.value].sort(
    (left, right) => right.max_missing - left.max_missing || left.number - right.number,
  )[0] ?? null,
);
const topCurrentMissing = computed(() => String(topCurrent.value?.current_missing ?? 0));
const topCurrentMeta = computed(() =>
  topCurrent.value ? `${areaLabel.value} ${formatNumber(topCurrent.value.number)}` : '--',
);
const topMaxMissing = computed(() => String(topMax.value?.max_missing ?? 0));
const topMaxMeta = computed(() =>
  topMax.value ? `${areaLabel.value} ${formatNumber(topMax.value.number)}` : '--',
);

async function reloadOmissions(): Promise<void> {
  lottery.loading = true;
  try {
    await lottery.loadOmissionStatistics();
    await selectDefaultNumber();
  } finally {
    lottery.loading = false;
  }
}

async function handleAreaChange(): Promise<void> {
  await selectDefaultNumber();
}

async function selectDefaultNumber(): Promise<void> {
  const first = activeRows.value[0];
  if (!first) return;
  await selectNumber(first);
}

async function selectNumber(row: LotteryNumberOmission): Promise<void> {
  await lottery.loadOmissionDetail(row.area, row.number);
  await nextTick();
  renderDetailChart();
}

function renderDetailChart(): void {
  const detail = lottery.omissionDetail;
  if (!detailChartRef.value || !detail) return;
  detailChart ??= echarts.init(detailChartRef.value);
  const option: EChartsOption = {
    ...chartTheme,
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 20, top: 28, bottom: 36 },
    xAxis: {
      type: 'category',
      data: detail.trend.map((item) => item.issue_no),
      axisLabel: { color: '#94a3b8' },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } },
    },
    series: [
      {
        name: '遗漏值',
        type: 'line',
        smooth: true,
        data: detail.trend.map((item) => item.missing),
        markPoint: {
          data: detail.trend
            .filter((item) => item.is_hit)
            .map((item) => ({ name: '命中', coord: [item.issue_no, item.missing], value: 0 })),
          symbolSize: 34,
        },
      },
    ],
  };
  detailChart.setOption(option);
}

function resizeChart(): void {
  detailChart?.resize();
}

function formatNumber(value: number): string {
  return String(value).padStart(2, '0');
}

onMounted(() => {
  void reloadOmissions();
  window.addEventListener('resize', resizeChart);
});

watch(
  () => lottery.omissionDetail,
  () => {
    void nextTick(() => renderDetailChart());
  },
);

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart);
  detailChart?.dispose();
});
</script>

<style scoped>
.omission-header {
  align-items: center;
}

.omission-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 12px;
}

.table-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.omission-metrics,
.omission-panel {
  margin-top: 16px;
}

.omission-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 12px;
}

.omission-table-wrap,
.detail-panel {
  min-width: 0;
}

.detail-panel {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.detail-heading,
.hit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.detail-heading span,
.hit-row span {
  color: var(--color-muted);
  font-size: 12px;
}

.detail-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.detail-stats div {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 10px;
}

.detail-stats span {
  color: var(--color-muted);
  display: block;
  font-size: 12px;
}

.detail-stats strong {
  display: block;
  font-size: 20px;
  margin-top: 6px;
}

.detail-chart {
  height: 280px;
  margin-top: 12px;
  min-width: 0;
}

.hit-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.hit-list h3 {
  font-size: 14px;
  margin: 0;
}

.hit-row {
  border-top: 1px solid rgba(148, 163, 184, 0.1);
  padding-top: 8px;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.5);
  --el-table-text-color: var(--color-text);
  --el-table-header-text-color: var(--color-muted);
  --el-table-border-color: rgba(148, 163, 184, 0.14);
}

@media (max-width: 980px) {
  .omission-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .omission-header,
  .omission-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
