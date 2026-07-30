<template>
  <RevealContent as="section" class="panel fund-panel" :delay="370">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">当前持仓静态组合走势</h2>
        <span class="panel-meta">把当前仓位放回共同历史区间，与等权持有作结构对照</span>
      </div>
      <div class="performance-actions">
        <el-select v-model="sampleLimit" class="sample-select" @change="loadPerformance">
          <el-option
            v-for="option in sampleOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadPerformance">
          刷新
        </el-button>
      </div>
    </div>

    <div class="panel-body">
      <div v-if="performance?.calculation_available" class="performance-content">
        <div class="performance-summary">
          <div>
            <span>当前权重收益</span>
            <strong :class="rateClass(performance.cumulative_return)">
              {{ formatPercent(performance.cumulative_return, true) }}
            </strong>
          </div>
          <div>
            <span>等权参考收益</span>
            <strong :class="rateClass(performance.equal_weight_return)">
              {{ formatPercent(performance.equal_weight_return, true) }}
            </strong>
          </div>
          <div>
            <span>年化波动率</span>
            <strong>{{ formatPercent(performance.annualized_volatility) }}</strong>
          </div>
          <div>
            <span>最大回撤</span>
            <strong class="is-loss">{{ formatPercent(performance.maximum_drawdown) }}</strong>
          </div>
          <div>
            <span>共同样本</span>
            <strong>{{ performance.sample_count }} 日</strong>
            <small>{{ sampleRange }}</small>
          </div>
        </div>

        <div ref="chartRef" class="performance-chart" />

        <div class="performance-members">
          <span
            v-for="member in performance.members"
            :key="member.fund_code"
            class="member-item"
          >
            <strong>{{ member.fund_name }}</strong>
            {{ member.fund_code }} · 当前权重 {{ formatPercent(member.allocation_weight) }}
          </span>
        </div>

        <p v-if="performance.excluded_fund_codes.length" class="excluded-note">
          因历史净值不足未纳入：{{ performance.excluded_fund_codes.join('、') }}
        </p>
        <p class="performance-note">{{ performance.warning }}</p>
      </div>

      <EmptyState
        v-else
        title="还不能生成组合走势"
        description="至少需要一只持仓基金拥有两个共同交易日的历史净值；可先在持仓风险区域同步全部历史。"
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
  fetchFundPortfolioPerformance,
  type FundPortfolioPerformance,
} from '@/plugins/fund/api';

const props = defineProps<{
  refreshKey: number;
}>();

const sampleOptions = [
  { label: '近 60 个交易日', value: 60 },
  { label: '近 120 个交易日', value: 120 },
  { label: '近 250 个交易日', value: 250 },
  { label: '近 365 个交易日', value: 365 },
  { label: '近 500 个交易日', value: 500 },
];
const sampleLimit = ref(365);
const performance = ref<FundPortfolioPerformance | null>(null);
const loading = ref(false);
const chartRef = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;

const sampleRange = computed(() => {
  if (!performance.value?.start_date || !performance.value.end_date) return '样本不足';
  return `${performance.value.start_date} 至 ${performance.value.end_date}`;
});

async function loadPerformance(): Promise<void> {
  loading.value = true;
  try {
    performance.value = await fetchFundPortfolioPerformance(sampleLimit.value);
    await nextTick();
    renderChart();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '组合走势加载失败');
  } finally {
    loading.value = false;
  }
}

function formatPercent(value: string | null, signed = false): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const prefix = signed && numeric > 0 ? '+' : '';
  return `${prefix}${(numeric * 100).toFixed(2)}%`;
}

function rateClass(value: string | null): string {
  const numeric = Number(value);
  if (numeric > 0) return 'is-profit';
  if (numeric < 0) return 'is-loss';
  return '';
}

function renderChart(): void {
  if (!chartRef.value || !performance.value?.calculation_available) {
    chart?.clear();
    return;
  }
  chart ??= echarts.init(chartRef.value);
  const points = performance.value.points;
  const option: EChartsOption = {
    ...chartTheme,
    color: ['#38bdf8', '#f59e0b', '#22c55e'],
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => `${Number(value).toFixed(2)}%`,
    },
    legend: {
      data: ['当前权重组合', '等权参考', '组合回撤'],
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
        name: '当前权重组合',
        type: 'line',
        showSymbol: false,
        smooth: 0.16,
        data: points.map((point) =>
          Number(((Number(point.portfolio_index) / 100 - 1) * 100).toFixed(2)),
        ),
      },
      {
        name: '等权参考',
        type: 'line',
        showSymbol: false,
        smooth: 0.16,
        lineStyle: { type: 'dashed' },
        data: points.map((point) =>
          Number(((Number(point.equal_weight_index) / 100 - 1) * 100).toFixed(2)),
        ),
      },
      {
        name: '组合回撤',
        type: 'line',
        showSymbol: false,
        areaStyle: { opacity: 0.08 },
        data: points.map((point) => Number((Number(point.drawdown) * 100).toFixed(2))),
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
  void loadPerformance();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart);
  chart?.dispose();
});

watch(
  () => props.refreshKey,
  () => {
    void loadPerformance();
  },
);
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.performance-note,
.excluded-note {
  color: var(--color-muted);
  font-size: 12px;
}

.performance-actions {
  align-items: center;
  display: flex;
  gap: 8px;
}

.sample-select {
  width: 168px;
}

.performance-content {
  display: grid;
  gap: 14px;
}

.performance-summary {
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  padding-bottom: 14px;
}

.performance-summary div {
  display: grid;
  gap: 5px;
}

.performance-summary span,
.performance-summary small {
  color: var(--color-muted);
  font-size: 12px;
}

.performance-summary strong {
  color: var(--color-text);
  font-size: 15px;
}

.performance-chart {
  height: 360px;
  width: 100%;
}

.performance-members {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.member-item {
  color: var(--color-muted);
  font-size: 12px;
}

.member-item strong {
  color: var(--color-text);
  margin-right: 5px;
}

.performance-note,
.excluded-note {
  line-height: 1.6;
  margin: 0;
}

.excluded-note {
  color: #fbbf24;
}

.is-profit {
  color: #ef4444 !important;
}

.is-loss {
  color: #22c55e !important;
}

@media (max-width: 920px) {
  .performance-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .panel-header,
  .performance-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .sample-select {
    width: 100%;
  }

  .performance-summary {
    grid-template-columns: 1fr;
  }

  .performance-chart {
    height: 320px;
  }
}
</style>
