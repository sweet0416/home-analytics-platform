<template>
  <RevealContent as="section" class="panel fund-panel" :delay="300">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">历史净值与收益走势</h2>
        <span class="panel-meta">
          收益率以当前样本第一条净值为起点，仅反映所选时间范围
        </span>
      </div>
    </div>
    <div class="panel-body">
      <div class="trend-controls">
        <label>
          <span>基金代码</span>
          <el-input v-model="fundCode" placeholder="例如 110022" />
        </label>
        <label>
          <span>基金类型</span>
          <el-select v-model="fundType">
            <el-option
              v-for="type in fundTypes"
              :key="type"
              :label="type"
              :value="type"
            />
          </el-select>
        </label>
        <label>
          <span>样本范围</span>
          <el-select v-model="limit">
            <el-option
              v-for="option in limitOptions"
              :key="option"
              :label="`${option} 个交易日`"
              :value="option"
            />
          </el-select>
        </label>
        <div class="trend-actions">
          <el-button :icon="Search" :loading="loading" @click="loadHistory">
            查看已存数据
          </el-button>
          <el-button
            type="primary"
            :icon="Refresh"
            :loading="syncing"
            @click="syncHistory"
          >
            同步历史净值
          </el-button>
        </div>
      </div>

      <div v-if="records.length" class="trend-content">
        <div class="trend-summary">
          <div>
            <span>基金</span>
            <strong>{{ selectedFundName }}</strong>
          </div>
          <div>
            <span>样本</span>
            <strong>{{ records.length }} 个交易日</strong>
          </div>
          <div>
            <span>日期范围</span>
            <strong>{{ historyRange }}</strong>
          </div>
          <div>
            <span>区间收益</span>
            <strong :class="returnClass">{{ formattedReturn }}</strong>
          </div>
          <div>
            <span>最大回撤</span>
            <strong class="negative">{{ formatRate(risk?.maximum_drawdown) }}</strong>
            <small>{{ drawdownRange }}</small>
          </div>
          <div>
            <span>年化波动率</span>
            <strong>{{ formatRate(risk?.annualized_volatility) }}</strong>
          </div>
          <div>
            <span>上涨日占比</span>
            <strong>{{ formatRate(risk?.positive_day_ratio) }}</strong>
          </div>
        </div>
        <div ref="chartRef" class="trend-chart" />
        <p class="trend-note">
          {{ risk?.warning ?? '单位净值用于展示价格变化，风险指标仅反映当前样本范围。' }}
          未计申购赎回费、分红再投资和个人现金流。
        </p>
      </div>
      <EmptyState
        v-else
        title="还没有历史净值"
        description="输入基金代码后同步历史净值，或查看数据库中已经保存的记录。"
      />
    </div>
  </RevealContent>
</template>

<script setup lang="ts">
import { Refresh, Search } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import type { ECharts, EChartsOption } from 'echarts';
import { ElMessage } from 'element-plus';
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';

import { chartTheme } from '@/charts/useChartTheme';
import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  fetchFundNavHistory,
  fetchFundNavRisk,
  syncFundNavHistory,
  type FundNavRecord,
  type FundNavRisk,
} from '@/plugins/fund/api';

const emit = defineEmits<{
  synced: [];
}>();

const fundTypes = ['ETF', 'QDII', '指数基金', '混合型', '债券型', '货币型', '其他'];
const limitOptions = [90, 180, 365, 500];
const fundCode = ref('');
const fundType = ref('ETF');
const limit = ref(365);
const records = ref<FundNavRecord[]>([]);
const risk = ref<FundNavRisk | null>(null);
const loading = ref(false);
const syncing = ref(false);
const chartRef = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;

const selectedFundName = computed(() => records.value.at(-1)?.fund_name ?? fundCode.value);
const historyRange = computed(() => {
  if (!records.value.length) return '--';
  return `${records.value[0].nav_date} 至 ${records.value.at(-1)?.nav_date ?? '--'}`;
});
const returnRate = computed(() => {
  if (risk.value?.cumulative_return === null || !risk.value) return null;
  const value = Number(risk.value.cumulative_return) * 100;
  return Number.isFinite(value) ? value : null;
});
const formattedReturn = computed(() => {
  if (returnRate.value === null) return '--';
  const prefix = returnRate.value > 0 ? '+' : '';
  return `${prefix}${returnRate.value.toFixed(2)}%`;
});
const returnClass = computed(() => {
  if (returnRate.value === null || returnRate.value === 0) return '';
  return returnRate.value > 0 ? 'positive' : 'negative';
});
const drawdownRange = computed(() => {
  if (!risk.value?.drawdown_peak_date || !risk.value.drawdown_trough_date) {
    return risk.value?.maximum_drawdown === '0.000000' ? '样本内无回撤' : '样本内';
  }
  return `${risk.value.drawdown_peak_date} 至 ${risk.value.drawdown_trough_date}`;
});

function formatRate(value: string | null | undefined): string {
  if (value === null || value === undefined) return '--';
  const rate = Number(value) * 100;
  if (!Number.isFinite(rate)) return '--';
  const prefix = rate > 0 ? '+' : '';
  return `${prefix}${rate.toFixed(2)}%`;
}

async function loadHistory(): Promise<void> {
  const code = fundCode.value.trim();
  if (!code) {
    ElMessage.warning('请先填写基金代码');
    return;
  }
  loading.value = true;
  try {
    const [history, riskResult] = await Promise.all([
      fetchFundNavHistory(code, limit.value),
      fetchFundNavRisk(code, limit.value),
    ]);
    records.value = history;
    risk.value = riskResult;
    if (!records.value.length) {
      ElMessage.info('数据库中还没有这只基金的历史净值');
    }
    await nextTick();
    renderChart();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '历史净值加载失败');
  } finally {
    loading.value = false;
  }
}

async function syncHistory(): Promise<void> {
  const code = fundCode.value.trim();
  if (!code) {
    ElMessage.warning('请先填写基金代码');
    return;
  }
  syncing.value = true;
  try {
    const result = await syncFundNavHistory({
      fund_code: code,
      fund_type: fundType.value,
      limit: limit.value,
    });
    fundCode.value = result.fund_code;
    fundType.value = result.fund_type;
    await loadHistory();
    ElMessage.success(
      `已同步 ${result.fund_name} 的 ${result.synced_count} 个交易日净值`,
    );
    emit('synced');
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '历史净值同步失败');
  } finally {
    syncing.value = false;
  }
}

function renderChart(): void {
  if (!chartRef.value || records.value.length < 2) {
    chart?.clear();
    return;
  }
  chart ??= echarts.init(chartRef.value);
  const firstNav = Number(records.value[0].unit_nav);
  const returns = records.value.map((record) => {
    const nav = Number(record.unit_nav);
    return Number.isFinite(nav) && firstNav > 0
      ? Number(((nav / firstNav - 1) * 100).toFixed(2))
      : null;
  });
  const option: EChartsOption = {
    ...chartTheme,
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => String(value),
    },
    legend: {
      data: ['单位净值', '区间收益'],
      textStyle: { color: '#94a3b8' },
    },
    grid: { left: 48, right: 54, top: 48, bottom: 54 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8 }],
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: records.value.map((record) => record.nav_date),
      axisLabel: { color: '#94a3b8', hideOverlap: true },
    },
    yAxis: [
      {
        type: 'value',
        name: '净值',
        scale: true,
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } },
      },
      {
        type: 'value',
        name: '收益率',
        scale: true,
        axisLabel: { color: '#94a3b8', formatter: '{value}%' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '单位净值',
        type: 'line',
        showSymbol: false,
        smooth: 0.2,
        data: records.value.map((record) => Number(record.unit_nav)),
      },
      {
        name: '区间收益',
        type: 'line',
        yAxisIndex: 1,
        showSymbol: false,
        smooth: 0.2,
        data: returns,
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
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart);
  chart?.dispose();
});
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.trend-controls {
  align-items: end;
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr 0.8fr 0.8fr auto;
}

.trend-controls label {
  display: grid;
  gap: 7px;
}

.trend-controls label span,
.trend-summary span,
.trend-note {
  color: var(--color-muted);
  font-size: 12px;
}

.trend-actions {
  display: flex;
  gap: 8px;
}

.trend-content {
  margin-top: 18px;
}

.trend-summary {
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding-bottom: 14px;
}

.trend-summary div {
  display: grid;
  gap: 5px;
}

.trend-summary small {
  color: var(--color-muted);
  font-size: 11px;
}

.trend-summary strong {
  color: var(--color-text);
  font-size: 14px;
}

.trend-summary .positive {
  color: #86efac;
}

.trend-summary .negative {
  color: #fca5a5;
}

.trend-chart {
  height: 360px;
  margin-top: 12px;
  width: 100%;
}

.trend-note {
  line-height: 1.6;
  margin: 8px 0 0;
}

@media (max-width: 920px) {
  .trend-controls,
  .trend-summary {
    grid-template-columns: 1fr 1fr;
  }

  .trend-actions {
    grid-column: 1 / -1;
  }
}

@media (max-width: 560px) {
  .trend-controls,
  .trend-summary {
    grid-template-columns: 1fr;
  }

  .trend-actions {
    align-items: stretch;
    display: grid;
  }

  .trend-chart {
    height: 320px;
  }
}
</style>
