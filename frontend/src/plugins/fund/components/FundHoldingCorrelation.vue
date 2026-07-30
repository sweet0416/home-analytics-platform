<template>
  <RevealContent as="section" class="panel fund-panel" :delay="372">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">持仓相关性与分散效果</h2>
        <span class="panel-meta">比较共同日期收益是否经常同涨同跌，识别表面分散、实际联动的持仓</span>
      </div>
      <div class="correlation-actions">
        <el-select v-model="sampleLimit" class="sample-select" @change="loadCorrelation">
          <el-option
            v-for="option in sampleOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadCorrelation">
          刷新
        </el-button>
      </div>
    </div>

    <div class="panel-body">
      <div v-if="correlation?.total_pair_count" class="correlation-content">
        <div class="correlation-summary">
          <div>
            <span>持仓基金</span>
            <strong>{{ correlation.fund_count }} 只</strong>
          </div>
          <div>
            <span>可计算组合</span>
            <strong>
              {{ correlation.calculated_pair_count }}/{{ correlation.total_pair_count }}
            </strong>
          </div>
          <div>
            <span>平均相关性</span>
            <strong>{{ formatCorrelation(correlation.average_pairwise_correlation) }}</strong>
          </div>
          <div>
            <span>高度正相关</span>
            <strong>{{ correlation.high_correlation_pair_count }} 对</strong>
          </div>
          <div>
            <span>分散提示</span>
            <strong :class="diversificationClass">{{ diversificationLabel }}</strong>
          </div>
        </div>

        <div ref="chartRef" class="correlation-chart" />

        <div class="correlation-table">
          <div class="correlation-row table-head">
            <span>基金组合</span>
            <span>共同收益样本</span>
            <span>相关系数</span>
            <span>通俗解释</span>
          </div>
          <div
            v-for="pair in sortedPairs"
            :key="`${pair.first_fund_code}-${pair.second_fund_code}`"
            class="correlation-row"
          >
            <span>
              <strong>{{ memberName(pair.first_fund_code) }}</strong>
              <small>{{ pair.first_fund_code }}</small>
              <strong>{{ memberName(pair.second_fund_code) }}</strong>
              <small>{{ pair.second_fund_code }}</small>
            </span>
            <span>{{ pair.observation_count }} 日</span>
            <span :class="correlationClass(pair.correlation)">
              {{ formatCorrelation(pair.correlation) }}
            </span>
            <span>{{ explainCorrelation(pair.correlation) }}</span>
          </div>
        </div>

        <p class="correlation-note">{{ correlation.warning }}</p>
      </div>
      <EmptyState
        v-else
        title="还没有可比较的基金组合"
        description="至少需要两只持仓基金，并且每只基金拥有三个以上共同净值日期。"
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
  fetchFundHoldingCorrelation,
  type FundCorrelationPair,
  type FundHoldingCorrelation,
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
const correlation = ref<FundHoldingCorrelation | null>(null);
const loading = ref(false);
const chartRef = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;

const sortedPairs = computed(() =>
  [...(correlation.value?.pairs ?? [])].sort(
    (first, second) =>
      Math.abs(Number(second.correlation ?? 0)) - Math.abs(Number(first.correlation ?? 0)),
  ),
);

const diversificationLabel = computed(() => {
  const rawValue = correlation.value?.average_pairwise_correlation;
  if (rawValue === null || rawValue === undefined) return '样本不足';
  const value = Number(rawValue);
  if (!Number.isFinite(value)) return '样本不足';
  if (value >= 0.8) return '联动很强';
  if (value >= 0.5) return '分散有限';
  if (value >= 0.2) return '有一定分散';
  return '分散较明显';
});

const diversificationClass = computed(() => {
  const rawValue = correlation.value?.average_pairwise_correlation;
  if (rawValue === null || rawValue === undefined) return '';
  const value = Number(rawValue);
  if (!Number.isFinite(value)) return '';
  if (value >= 0.8) return 'is-warning';
  if (value < 0.5) return 'is-diversified';
  return '';
});

async function loadCorrelation(): Promise<void> {
  loading.value = true;
  try {
    correlation.value = await fetchFundHoldingCorrelation(sampleLimit.value);
    await nextTick();
    renderChart();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '持仓相关性加载失败');
  } finally {
    loading.value = false;
  }
}

function formatCorrelation(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : '--';
}

function memberName(fundCode: string): string {
  return (
    correlation.value?.members.find((member) => member.fund_code === fundCode)
      ?.fund_name ?? fundCode
  );
}

function explainCorrelation(value: string | null): string {
  if (value === null) return '样本不足或其中一只基金没有波动';
  const numeric = Number(value);
  if (numeric >= 0.8) return '大多数时候同向变化，分散作用较弱';
  if (numeric >= 0.5) return '同向关系较明显';
  if (numeric >= 0.2) return '存在一定同向关系';
  if (numeric > -0.2) return '历史联动较弱';
  return '样本内常出现反向变化';
}

function correlationClass(value: string | null): string {
  if (value === null) return '';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '';
  if (numeric >= 0.8) return 'is-warning';
  if (numeric < 0.2) return 'is-diversified';
  return '';
}

function renderChart(): void {
  if (!chartRef.value || !correlation.value?.total_pair_count) {
    chart?.clear();
    return;
  }
  chart ??= echarts.init(chartRef.value);
  const codes = correlation.value.members.map((member) => member.fund_code);
  const pairMap = new Map<string, FundCorrelationPair>();
  correlation.value.pairs.forEach((pair) => {
    pairMap.set(`${pair.first_fund_code}-${pair.second_fund_code}`, pair);
    pairMap.set(`${pair.second_fund_code}-${pair.first_fund_code}`, pair);
  });
  const data: Array<[number, number, number | null, number]> = [];
  codes.forEach((rowCode, rowIndex) => {
    codes.forEach((columnCode, columnIndex) => {
      if (rowCode === columnCode) {
        data.push([columnIndex, rowIndex, 1, 0]);
        return;
      }
      const pair = pairMap.get(`${rowCode}-${columnCode}`);
      data.push([
        columnIndex,
        rowIndex,
        pair?.correlation === null || pair?.correlation === undefined
          ? null
          : Number(pair.correlation),
        pair?.observation_count ?? 0,
      ]);
    });
  });
  const option: EChartsOption = {
    ...chartTheme,
    tooltip: {
      formatter: (params: unknown) => {
        const item = params as { data: [number, number, number | null, number] };
        const [xIndex, yIndex, value, observations] = item.data;
        return [
          `${memberName(codes[yIndex])} × ${memberName(codes[xIndex])}`,
          `相关系数：${value === null ? '--' : value.toFixed(2)}`,
          observations ? `共同收益样本：${observations} 日` : '',
        ]
          .filter(Boolean)
          .join('<br>');
      },
    },
    grid: { left: 82, right: 82, top: 24, bottom: 70 },
    xAxis: {
      type: 'category',
      data: codes,
      splitArea: { show: true },
      axisLabel: { color: '#94a3b8' },
    },
    yAxis: {
      type: 'category',
      data: codes,
      splitArea: { show: true },
      axisLabel: { color: '#94a3b8' },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 8,
      text: ['正相关', '负相关'],
      textStyle: { color: '#94a3b8' },
      inRange: { color: ['#38bdf8', '#172033', '#f59e0b'] },
    },
    series: [
      {
        type: 'heatmap',
        data,
        label: {
          show: true,
          color: '#f8fafc',
          formatter: (params: unknown) => {
            const item = params as { data: [number, number, number | null, number] };
            return item.data[2] === null ? '--' : item.data[2].toFixed(2);
          },
        },
        emphasis: {
          itemStyle: {
            borderColor: '#f8fafc',
            borderWidth: 1,
          },
        },
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
  void loadCorrelation();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart);
  chart?.dispose();
});

watch(
  () => props.refreshKey,
  () => {
    void loadCorrelation();
  },
);
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.correlation-note {
  color: var(--color-muted);
  font-size: 12px;
}

.correlation-actions {
  align-items: center;
  display: flex;
  gap: 8px;
}

.sample-select {
  width: 168px;
}

.correlation-content {
  display: grid;
  gap: 14px;
}

.correlation-summary {
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  padding-bottom: 14px;
}

.correlation-summary div {
  display: grid;
  gap: 5px;
}

.correlation-summary span,
.correlation-row span {
  color: var(--color-muted);
  font-size: 12px;
}

.correlation-summary strong,
.correlation-row strong {
  color: var(--color-text);
}

.correlation-chart {
  height: 360px;
  width: 100%;
}

.correlation-table {
  display: grid;
  gap: 8px;
  overflow-x: auto;
}

.correlation-row {
  align-items: center;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(260px, 1.6fr) 140px 120px minmax(220px, 1fr);
  min-width: 820px;
  padding: 10px 4px;
}

.correlation-row small {
  color: var(--color-muted);
  font-size: 11px;
  margin: 0 12px 0 4px;
}

.table-head {
  font-weight: 700;
}

.correlation-note {
  line-height: 1.6;
  margin: 0;
}

.is-warning {
  color: #f59e0b !important;
}

.is-diversified {
  color: #38bdf8 !important;
}

@media (max-width: 920px) {
  .correlation-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .panel-header,
  .correlation-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .sample-select {
    width: 100%;
  }

  .correlation-summary {
    grid-template-columns: 1fr;
  }

  .correlation-chart {
    height: 320px;
  }
}
</style>
