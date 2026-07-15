<template>
  <div>
    <section class="page-header heatmap-header">
      <div>
        <h1 class="page-title">号码热力图</h1>
        <div class="page-subtitle">频次、遗漏与冷热强度矩阵</div>
      </div>
      <div class="heatmap-actions">
        <RouterLink to="/lottery/dlt/statistics" class="back-link">返回统计</RouterLink>
        <RouterLink to="/lottery/dlt/same-period" class="back-link">历史同期</RouterLink>
        <el-radio-group v-model="selectedArea" size="small" @change="handleAreaChange">
          <el-radio-button label="front">前区</el-radio-button>
          <el-radio-button label="back">后区</el-radio-button>
        </el-radio-group>
        <el-segmented v-model="selectedMetric" :options="metricOptions" size="small" />
        <el-button :icon="Refresh" :loading="lottery.loading" @click="reloadHeatmap">
          刷新
        </el-button>
      </div>
    </section>

    <div class="grid metrics heatmap-metrics">
      <MetricCard label="样本期数" :value="sampleSize" :meta="sampleMeta" />
      <MetricCard label="最高频次" :value="topFrequencyValue" :meta="topFrequencyMeta" />
      <MetricCard label="最高遗漏" :value="topMissingValue" :meta="topMissingMeta" />
      <MetricCard label="当前视图" :value="metricLabel" :meta="areaLabel" />
    </div>

    <section class="panel heatmap-panel">
      <div class="panel-header">
        <h2 class="panel-title">{{ areaLabel }}矩阵</h2>
        <span class="table-meta">{{ metricDescription }}</span>
      </div>
      <div class="panel-body heatmap-layout">
        <div class="matrix-wrap">
          <div class="heatmap-grid" :class="selectedArea">
            <button
              v-for="cell in heatmapCells"
              :key="`${cell.area}-${cell.number}`"
              class="heatmap-cell"
              :class="{ active: isActiveCell(cell) }"
              :style="{ '--heat': cell.opacity, '--accent': cell.color }"
              type="button"
              @click="selectCell(cell)"
            >
              <span class="cell-number">{{ formatNumber(cell.number) }}</span>
              <strong>{{ cell.value }}</strong>
              <small>{{ cell.caption }}</small>
            </button>
          </div>
          <div class="legend-row">
            <span>低</span>
            <div class="legend-bar" />
            <span>高</span>
          </div>
        </div>

        <aside class="heatmap-detail">
          <div class="detail-heading">
            <span>联动详情</span>
            <LotteryBall
              v-if="lottery.omissionDetail"
              :area="lottery.omissionDetail.area"
              :value="lottery.omissionDetail.number"
            />
          </div>
          <div v-if="selectedCell" class="detail-stats">
            <div>
              <span>出现次数</span>
              <strong>{{ selectedCell.count }}</strong>
            </div>
            <div>
              <span>当前遗漏</span>
              <strong>{{ selectedCell.missing }}</strong>
            </div>
            <div>
              <span>最大遗漏</span>
              <strong>{{ lottery.omissionDetail?.max_missing ?? '--' }}</strong>
            </div>
            <div>
              <span>平均遗漏</span>
              <strong>{{ lottery.omissionDetail?.average_missing ?? '--' }}</strong>
            </div>
          </div>
          <div ref="detailChartRef" class="detail-chart" />
          <div v-if="lottery.omissionDetail" class="hit-list">
            <h3>最近命中</h3>
            <div
              v-for="item in lottery.omissionDetail.hit_issues.slice(0, 6)"
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
import MetricCard from '@/components/metric/MetricCard.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import { useLotteryStore } from '@/plugins/lottery/store';

type BallArea = 'front' | 'back';
type HeatMetric = 'frequency' | 'missing' | 'temperature';

interface HeatmapCell {
  area: BallArea;
  number: number;
  count: number;
  missing: number;
  value: number;
  caption: string;
  opacity: string;
  color: string;
}

const lottery = useLotteryStore();
const selectedArea = ref<BallArea>('front');
const selectedMetric = ref<HeatMetric>('temperature');
const selectedCell = ref<HeatmapCell | null>(null);
const detailChartRef = ref<HTMLDivElement | null>(null);
let detailChart: ECharts | null = null;

const metricOptions = [
  { label: '冷热', value: 'temperature' },
  { label: '频次', value: 'frequency' },
  { label: '遗漏', value: 'missing' },
];

const areaLabel = computed(() => (selectedArea.value === 'front' ? '前区' : '后区'));
const sampleSize = computed(() => String(lottery.statistics?.sample_size ?? 0));
const sampleMeta = computed(() => `请求最近 ${lottery.statistics?.requested_limit ?? 100} 期`);
const metricLabel = computed(() => {
  const labels: Record<HeatMetric, string> = {
    frequency: '频次',
    missing: '遗漏',
    temperature: '冷热',
  };
  return labels[selectedMetric.value];
});
const metricDescription = computed(() => {
  const labels: Record<HeatMetric, string> = {
    frequency: '颜色越亮表示最近样本中出现次数越高',
    missing: '颜色越亮表示当前连续遗漏越高',
    temperature: '综合频次与遗漏，偏热号码更亮',
  };
  return labels[selectedMetric.value];
});

const frequencyRows = computed(() =>
  selectedArea.value === 'front'
    ? lottery.statistics?.front_frequency ?? []
    : lottery.statistics?.back_frequency ?? [],
);
const omissionRows = computed(() =>
  selectedArea.value === 'front'
    ? lottery.omissionStatistics?.front ?? []
    : lottery.omissionStatistics?.back ?? [],
);
const topFrequency = computed(() =>
  [...frequencyRows.value].sort((left, right) => right.count - left.count || left.number - right.number)[0] ?? null,
);
const topMissing = computed(() =>
  [...omissionRows.value].sort(
    (left, right) => right.current_missing - left.current_missing || left.number - right.number,
  )[0] ?? null,
);
const topFrequencyValue = computed(() => String(topFrequency.value?.count ?? 0));
const topFrequencyMeta = computed(() =>
  topFrequency.value ? `${areaLabel.value} ${formatNumber(topFrequency.value.number)}` : '--',
);
const topMissingValue = computed(() => String(topMissing.value?.current_missing ?? 0));
const topMissingMeta = computed(() =>
  topMissing.value ? `${areaLabel.value} ${formatNumber(topMissing.value.number)}` : '--',
);
const heatmapCells = computed(() => {
  const maxCount = Math.max(...frequencyRows.value.map((item) => item.count), 1);
  const maxMissing = Math.max(...omissionRows.value.map((item) => item.current_missing), 1);
  return frequencyRows.value.map((frequency) => {
    const omission = omissionRows.value.find((item) => item.number === frequency.number);
    const missing = omission?.current_missing ?? frequency.missing;
    const temperature = frequency.count / maxCount - missing / maxMissing * 0.45;
    const rawValue = selectedMetric.value === 'frequency'
      ? frequency.count
      : selectedMetric.value === 'missing'
        ? missing
        : Math.round((temperature + 0.45) * 100);
    const maxValue = selectedMetric.value === 'frequency'
      ? maxCount
      : selectedMetric.value === 'missing'
        ? maxMissing
        : 145;
    const intensity = Math.max(0.12, Math.min(1, rawValue / maxValue));
    return {
      area: selectedArea.value,
      number: frequency.number,
      count: frequency.count,
      missing,
      value: rawValue,
      caption: selectedMetric.value === 'frequency'
        ? `遗漏 ${missing}`
        : selectedMetric.value === 'missing'
          ? `出现 ${frequency.count}`
          : `频 ${frequency.count} 遗 ${missing}`,
      opacity: intensity.toFixed(2),
      color: selectedArea.value === 'front' ? '56, 189, 248' : '245, 158, 11',
    };
  });
});

async function reloadHeatmap(): Promise<void> {
  lottery.loading = true;
  try {
    await Promise.all([lottery.loadStatistics(), lottery.loadOmissionStatistics()]);
    await selectDefaultCell();
  } finally {
    lottery.loading = false;
  }
}

async function handleAreaChange(): Promise<void> {
  selectedCell.value = null;
  await selectDefaultCell();
}

async function selectDefaultCell(): Promise<void> {
  const first = heatmapCells.value[0];
  if (first) await selectCell(first);
}

async function selectCell(cell: HeatmapCell): Promise<void> {
  selectedCell.value = cell;
  await lottery.loadOmissionDetail(cell.area, cell.number);
  await nextTick();
  renderDetailChart();
}

function isActiveCell(cell: HeatmapCell): boolean {
  return selectedCell.value?.area === cell.area && selectedCell.value.number === cell.number;
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
  void reloadHeatmap();
  window.addEventListener('resize', resizeChart);
});

watch(
  () => [lottery.omissionDetail, selectedMetric.value],
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
.heatmap-header {
  align-items: center;
}

.heatmap-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 12px;
}

.back-link,
.table-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.heatmap-metrics,
.heatmap-panel {
  margin-top: 16px;
}

.heatmap-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.46fr);
  gap: 12px;
}

.matrix-wrap,
.heatmap-detail {
  min-width: 0;
}

.heatmap-grid {
  display: grid;
  gap: 8px;
}

.heatmap-grid.front {
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.heatmap-grid.back {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.heatmap-cell {
  aspect-ratio: 1 / 0.86;
  background:
    linear-gradient(135deg, rgba(var(--accent), calc(var(--heat) * 0.72)), rgba(15, 23, 42, 0.72)),
    rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(var(--accent), calc(var(--heat) * 0.5 + 0.18));
  border-radius: 8px;
  color: var(--color-text);
  cursor: pointer;
  display: grid;
  gap: 4px;
  min-width: 0;
  padding: 10px;
  text-align: left;
  transition: border-color 0.18s ease, transform 0.18s ease;
}

.heatmap-cell:hover,
.heatmap-cell.active {
  border-color: rgba(var(--accent), 0.95);
  transform: translateY(-1px);
}

.cell-number {
  color: #e2e8f0;
  font-size: 18px;
  font-weight: 780;
}

.heatmap-cell strong {
  font-size: 24px;
  line-height: 1;
}

.heatmap-cell small {
  color: rgba(226, 232, 240, 0.72);
  font-size: 11px;
  overflow-wrap: anywhere;
}

.legend-row {
  align-items: center;
  color: var(--color-muted);
  display: grid;
  font-size: 12px;
  gap: 8px;
  grid-template-columns: auto 1fr auto;
  margin-top: 12px;
}

.legend-bar {
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.12), rgba(56, 189, 248, 0.86));
  border-radius: 999px;
  height: 8px;
}

.heatmap-detail {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.detail-heading,
.hit-row {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.detail-heading span,
.hit-row span {
  color: var(--color-muted);
  font-size: 12px;
}

.detail-stats {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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
  height: 260px;
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

@media (max-width: 1100px) {
  .heatmap-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .heatmap-header,
  .heatmap-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .heatmap-grid.front {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .heatmap-grid.front {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .heatmap-grid.back {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
