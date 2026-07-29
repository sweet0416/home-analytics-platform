<template>
  <RevealContent as="section" class="panel fund-panel" :delay="370">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">资产配置</h2>
        <span class="panel-meta">
          按持仓市值统计；缺少当前净值时使用录入成本，并单独标记
        </span>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadAllocation">
        刷新
      </el-button>
    </div>
    <div class="panel-body">
      <div v-if="allocation?.position_count" class="allocation-content">
        <div class="allocation-summary">
          <div>
            <span>统计金额</span>
            <strong>{{ formatMoney(allocation.total_amount) }}</strong>
          </div>
          <div>
            <span>最大单一基金</span>
            <strong>{{ formatPercent(allocation.top_holding_weight) }}</strong>
          </div>
          <div>
            <span>集中度 HHI（越高越集中）</span>
            <strong>{{ formatHhi(allocation.concentration_hhi) }}</strong>
          </div>
          <div>
            <span>估值完整度</span>
            <strong>
              {{ allocation.current_nav_count }}/{{ allocation.position_count }} 使用当前净值
            </strong>
          </div>
        </div>

        <div class="allocation-toolbar">
          <el-segmented
            v-model="groupMode"
            :options="groupOptions"
            @change="renderChart"
          />
          <span v-if="allocation.cost_fallback_count" class="fallback-warning">
            {{ allocation.cost_fallback_count }} 条持仓暂按成本估算
          </span>
        </div>

        <div class="allocation-layout">
          <div ref="chartRef" class="allocation-chart" />
          <div class="allocation-list">
            <div class="allocation-row table-head">
              <span>分组</span>
              <span>金额</span>
              <span>占比</span>
            </div>
            <div
              v-for="group in activeGroups"
              :key="group.label"
              class="allocation-row"
            >
              <span>
                <strong>{{ group.label }}</strong>
                <small>{{ group.position_count }} 条持仓</small>
              </span>
              <span>{{ formatMoney(group.amount) }}</span>
              <span>{{ formatPercent(group.weight) }}</span>
            </div>
          </div>
        </div>

        <div class="holding-breakdown">
          <div class="holding-row table-head">
            <span>基金</span>
            <span>账户</span>
            <span>估值金额</span>
            <span>占比</span>
            <span>估值依据</span>
          </div>
          <div
            v-for="holding in allocation.holdings"
            :key="holding.position_id"
            class="holding-row"
          >
            <span>
              <strong>{{ holding.fund_name }}</strong>
              <small>{{ holding.fund_code }} · {{ holding.fund_type }}</small>
            </span>
            <span>{{ holding.account_name }}</span>
            <span>{{ formatMoney(holding.amount) }}</span>
            <span>{{ formatPercent(holding.weight) }}</span>
            <span :class="{ fallback: holding.valuation_basis === 'cost' }">
              {{ holding.valuation_basis === 'current_nav' ? '当前净值' : '成本估算' }}
            </span>
          </div>
        </div>

        <p class="allocation-note">
          当前仅按基金类型和账户汇总，不代表基金底层股票、债券或地区暴露；底层资产穿透将在后续数据源完善后加入。
        </p>
      </div>
      <EmptyState
        v-else
        title="还没有可分析的持仓"
        description="录入基金持仓后，这里会展示类型、账户和单一基金的配置比例。"
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
  fetchFundAllocation,
  type FundAllocation,
  type FundAllocationGroup,
} from '@/plugins/fund/api';

const props = defineProps<{
  refreshKey: number;
}>();

const groupOptions = [
  { label: '按基金类型', value: 'fund_type' },
  { label: '按账户', value: 'account' },
];
const groupMode = ref<'fund_type' | 'account'>('fund_type');
const allocation = ref<FundAllocation | null>(null);
const loading = ref(false);
const chartRef = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;

const activeGroups = computed<FundAllocationGroup[]>(() => {
  if (!allocation.value) return [];
  return groupMode.value === 'fund_type'
    ? allocation.value.by_fund_type
    : allocation.value.by_account;
});

async function loadAllocation(): Promise<void> {
  loading.value = true;
  try {
    allocation.value = await fetchFundAllocation();
    await nextTick();
    renderChart();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '资产配置加载失败');
  } finally {
    loading.value = false;
  }
}

function renderChart(): void {
  if (!chartRef.value || !activeGroups.value.length) {
    chart?.clear();
    return;
  }
  chart ??= echarts.init(chartRef.value);
  const option: EChartsOption = {
    ...chartTheme,
    tooltip: {
      trigger: 'item',
      formatter: '{b}<br/>{c} 元 · {d}%',
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#94a3b8' },
    },
    series: [
      {
        name: '配置占比',
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '43%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderColor: '#1f2937',
          borderWidth: 2,
        },
        label: {
          color: '#cbd5e1',
          formatter: '{b}\n{d}%',
        },
        data: activeGroups.value.map((group) => ({
          name: group.label,
          value: Number(group.amount),
        })),
      },
    ],
  };
  chart.setOption(option, true);
}

function formatMoney(value: string | number): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return `¥${numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`;
}

function formatPercent(value: string | number | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return `${(numeric * 100).toFixed(2)}%`;
}

function formatHhi(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return numeric.toFixed(4);
}

function resizeChart(): void {
  chart?.resize();
}

onMounted(() => {
  window.addEventListener('resize', resizeChart);
});

watch(
  () => props.refreshKey,
  () => {
    void loadAllocation();
  },
);

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart);
  chart?.dispose();
});
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.allocation-note {
  color: var(--color-muted);
  font-size: 12px;
}

.allocation-content {
  display: grid;
  gap: 16px;
}

.allocation-summary {
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding-bottom: 14px;
}

.allocation-summary div {
  display: grid;
  gap: 5px;
}

.allocation-summary span {
  color: var(--color-muted);
  font-size: 12px;
}

.allocation-summary strong {
  color: var(--color-text);
  font-size: 14px;
}

.allocation-toolbar {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.fallback-warning,
.fallback {
  color: #fbbf24;
  font-size: 12px;
}

.allocation-layout {
  align-items: stretch;
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(300px, 0.85fr) minmax(0, 1.15fr);
}

.allocation-chart {
  height: 320px;
  min-width: 0;
  width: 100%;
}

.allocation-list,
.holding-breakdown {
  display: grid;
  gap: 8px;
}

.allocation-row,
.holding-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 10px 12px;
}

.allocation-row {
  grid-template-columns: 1.2fr 0.9fr 0.65fr;
}

.holding-row {
  grid-template-columns: 1.5fr 0.8fr 0.85fr 0.65fr 0.7fr;
}

.allocation-row span,
.holding-row span {
  color: var(--color-muted);
  font-size: 13px;
}

.allocation-row strong,
.holding-row strong {
  color: var(--color-text);
  display: block;
}

.allocation-row small,
.holding-row small {
  display: block;
  font-size: 12px;
  margin-top: 4px;
}

.table-head {
  background: rgba(15, 23, 42, 0.45);
  font-weight: 700;
}

.allocation-note {
  line-height: 1.6;
  margin: 0;
}

@media (max-width: 920px) {
  .allocation-summary {
    grid-template-columns: 1fr 1fr;
  }

  .allocation-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .panel-header,
  .allocation-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .allocation-summary {
    grid-template-columns: 1fr;
  }

  .holding-breakdown {
    overflow-x: auto;
  }

  .holding-row {
    min-width: 680px;
  }
}
</style>
