<template>
  <RevealContent as="section" class="panel fund-panel" :delay="375">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">组合基准对比</h2>
        <span class="panel-meta">判断当前持仓在同一段历史里，相对市场代理是领先还是落后</span>
      </div>
      <div class="benchmark-actions">
        <el-select
          v-model="benchmarkCode"
          class="benchmark-select"
          filterable
          allow-create
          default-first-option
          placeholder="选择或输入基金代码"
          @change="loadBenchmark"
        >
          <el-option
            v-for="option in benchmarkOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-select v-model="sampleLimit" class="sample-select" @change="loadBenchmark">
          <el-option
            v-for="option in sampleOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadBenchmark">比较</el-button>
        <el-button type="primary" :loading="syncing" @click="syncAndCompare">
          同步并比较
        </el-button>
      </div>
    </div>

    <div class="panel-body">
      <div v-if="benchmark?.calculation_available" class="benchmark-content">
        <div class="benchmark-summary">
          <div>
            <span>当前组合</span>
            <strong :class="rateClass(benchmark.portfolio_return)">
              {{ formatPercent(benchmark.portfolio_return, true) }}
            </strong>
          </div>
          <div>
            <span>{{ benchmark.benchmark_name }}</span>
            <strong :class="rateClass(benchmark.benchmark_return)">
              {{ formatPercent(benchmark.benchmark_return, true) }}
            </strong>
            <small>{{ benchmark.benchmark_code }}</small>
          </div>
          <div>
            <span>相对收益</span>
            <strong :class="rateClass(benchmark.relative_return)">
              {{ formatPercent(benchmark.relative_return, true) }}
            </strong>
          </div>
          <div>
            <span>跟踪误差</span>
            <strong>{{ formatPercent(benchmark.tracking_error) }}</strong>
          </div>
          <div>
            <span>信息比率</span>
            <strong>{{ formatNumber(benchmark.information_ratio) }}</strong>
          </div>
          <div>
            <span>收益相关性</span>
            <strong>{{ formatNumber(benchmark.return_correlation) }}</strong>
          </div>
          <div>
            <span>共同样本</span>
            <strong>{{ benchmark.sample_count }} 日</strong>
            <small>{{ sampleRange }}</small>
          </div>
        </div>

        <div ref="chartRef" class="benchmark-chart" />
        <p class="benchmark-note">{{ benchmark.warning }}</p>
      </div>

      <EmptyState
        v-else
        title="还没有可比较的共同样本"
        description="点击“同步并比较”获取所选基准代理的历史净值。组合与基准至少需要两个共同净值日。"
      />
    </div>
  </RevealContent>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import type { ECharts, EChartsOption } from 'echarts';
import { ElMessage } from 'element-plus';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { chartTheme } from '@/charts/useChartTheme';
import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  fetchFundPortfolioBenchmark,
  syncFundNavHistory,
  type FundPortfolioBenchmark,
} from '@/plugins/fund/api';

const props = defineProps<{
  refreshKey: number;
}>();

const benchmarkOptions = [
  { label: '沪深300代理 · 华夏沪深300ETF联接A (000051)', value: '000051' },
  { label: '标普500代理 · 博时标普500ETF联接A (050025)', value: '050025' },
  { label: '纳斯达克100代理 · 广发纳指100ETF联接A (270042)', value: '270042' },
];
const sampleOptions = [
  { label: '近 60 个净值日', value: 60 },
  { label: '近 120 个净值日', value: 120 },
  { label: '近 250 个净值日', value: 250 },
  { label: '近 365 个净值日', value: 365 },
  { label: '近 500 个净值日', value: 500 },
];
const benchmarkCode = ref(localStorage.getItem('hap.fund.benchmarkCode') || '000051');
const sampleLimit = ref(365);
const benchmark = ref<FundPortfolioBenchmark | null>(null);
const loading = ref(false);
const syncing = ref(false);
const chartRef = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;

const sampleRange = computed(() => {
  if (!benchmark.value?.start_date || !benchmark.value.end_date) return '样本不足';
  return `${benchmark.value.start_date} 至 ${benchmark.value.end_date}`;
});

async function loadBenchmark(): Promise<void> {
  const code = benchmarkCode.value.trim();
  if (!code) return;
  localStorage.setItem('hap.fund.benchmarkCode', code);
  loading.value = true;
  try {
    benchmark.value = await fetchFundPortfolioBenchmark(code, sampleLimit.value);
    await nextTick();
    renderChart();
  } catch (error) {
    benchmark.value = null;
    ElMessage.error(error instanceof Error ? error.message : '基准对比加载失败');
  } finally {
    loading.value = false;
  }
}

async function syncAndCompare(): Promise<void> {
  const code = benchmarkCode.value.trim();
  if (!code) {
    ElMessage.warning('请先选择或输入基准基金代码');
    return;
  }
  syncing.value = true;
  try {
    const result = await syncFundNavHistory({
      fund_code: code,
      fund_type: '指数基准代理',
      limit: sampleLimit.value,
    });
    ElMessage.success(`已同步 ${result.synced_count} 条基准净值`);
    await loadBenchmark();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '基准净值同步失败');
  } finally {
    syncing.value = false;
  }
}

function formatPercent(value: string | null, signed = false): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const prefix = signed && numeric > 0 ? '+' : '';
  return `${prefix}${(numeric * 100).toFixed(2)}%`;
}

function formatNumber(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : '--';
}

function rateClass(value: string | null): string {
  const numeric = Number(value);
  if (numeric > 0) return 'is-profit';
  if (numeric < 0) return 'is-loss';
  return '';
}

function renderChart(): void {
  if (!chartRef.value || !benchmark.value?.calculation_available) {
    chart?.clear();
    return;
  }
  chart ??= echarts.init(chartRef.value);
  const points = benchmark.value.points;
  const option: EChartsOption = {
    ...chartTheme,
    color: ['#38bdf8', '#f59e0b', '#a78bfa'],
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => `${Number(value).toFixed(2)}%`,
    },
    legend: {
      data: ['当前组合', benchmark.value.benchmark_name, '相对收益'],
      textStyle: { color: '#94a3b8' },
    },
    grid: { left: 54, right: 28, top: 48, bottom: 54 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8 }],
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: points.map((point) => point.nav_date),
      axisLabel: { color: '#94a3b8', hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8', formatter: '{value}%' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } },
    },
    series: [
      {
        name: '当前组合',
        type: 'line',
        showSymbol: false,
        smooth: 0.16,
        data: points.map((point) =>
          Number(((Number(point.portfolio_index) / 100 - 1) * 100).toFixed(2)),
        ),
      },
      {
        name: benchmark.value.benchmark_name,
        type: 'line',
        showSymbol: false,
        smooth: 0.16,
        lineStyle: { type: 'dashed' },
        data: points.map((point) =>
          Number(((Number(point.benchmark_index) / 100 - 1) * 100).toFixed(2)),
        ),
      },
      {
        name: '相对收益',
        type: 'line',
        showSymbol: false,
        areaStyle: { opacity: 0.06 },
        data: points.map((point) =>
          Number((Number(point.relative_return) * 100).toFixed(2)),
        ),
      },
    ],
  };
  chart.setOption(option, true);
}

function resizeChart(): void {
  chart?.resize();
}

onMounted(() => {
  window.addEventListener('resize', resizeChart);
  void loadBenchmark();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart);
  chart?.dispose();
});

watch(
  () => props.refreshKey,
  () => {
    void loadBenchmark();
  },
);
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.benchmark-note {
  color: var(--color-muted);
  font-size: 12px;
}

.benchmark-actions {
  align-items: center;
  display: flex;
  gap: 8px;
}

.benchmark-select {
  width: 330px;
}

.sample-select {
  width: 156px;
}

.benchmark-content {
  display: grid;
  gap: 14px;
}

.benchmark-summary {
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  padding-bottom: 14px;
}

.benchmark-summary div {
  display: grid;
  gap: 5px;
}

.benchmark-summary span,
.benchmark-summary small {
  color: var(--color-muted);
  font-size: 12px;
}

.benchmark-summary strong {
  color: var(--color-text);
  font-size: 15px;
}

.benchmark-chart {
  height: 360px;
  width: 100%;
}

.benchmark-note {
  line-height: 1.6;
  margin: 0;
}

.is-profit {
  color: #ef4444 !important;
}

.is-loss {
  color: #22c55e !important;
}

@media (max-width: 1120px) {
  .benchmark-summary {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .panel-header,
  .benchmark-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .benchmark-select,
  .sample-select {
    width: 100%;
  }

  .benchmark-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .benchmark-chart {
    height: 320px;
  }
}
</style>
