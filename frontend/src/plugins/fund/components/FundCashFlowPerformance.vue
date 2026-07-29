<template>
  <RevealContent as="section" class="panel fund-panel" :delay="325">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">现金流收益分析</h2>
        <span class="panel-meta">按已录入流水与当前持仓市值计算，不等同于基金净值涨幅</span>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadPerformance">
        刷新
      </el-button>
    </div>
    <div class="panel-body">
      <div class="performance-summary">
        <div>
          <span>累计投入</span>
          <strong>{{ formatMoney(performance?.invested_cash) }}</strong>
        </div>
        <div>
          <span>累计回收</span>
          <strong>{{ formatMoney(performance?.recovered_cash) }}</strong>
        </div>
        <div>
          <span>当前市值</span>
          <strong>{{ formatMoney(performance?.current_value) }}</strong>
        </div>
        <div>
          <span>现金流收益</span>
          <strong :class="profitClass(performance?.net_profit)">
            {{ formatSignedMoney(performance?.net_profit) }}
          </strong>
        </div>
        <div>
          <span>简单收益率</span>
          <strong :class="profitClass(performance?.simple_return_rate)">
            {{ formatPercent(performance?.simple_return_rate) }}
          </strong>
        </div>
        <div>
          <span>样本范围</span>
          <strong>{{ tradeDateRange }}</strong>
        </div>
      </div>

      <div class="performance-status">
        <span :class="['status-pill', performance?.calculation_available ? 'ready' : 'waiting']">
          {{ performance?.calculation_available ? '可计算' : '等待数据' }}
        </span>
        <span>{{ performance?.calculation_basis ?? '已录入现金流 + 当前持仓市值' }}</span>
        <span>
          {{ performance?.transaction_count ?? 0 }} 条流水 ·
          {{ performance?.position_count ?? 0 }} 条持仓 ·
          {{ performance?.valuation_complete ? '估值完整' : '估值不完整' }}
        </span>
      </div>

      <p class="performance-warning">
        {{ performance?.warning ?? '正在检查现金流和持仓估值完整性。' }}
      </p>
    </div>
  </RevealContent>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref, watch } from 'vue';

import RevealContent from '@/components/common/RevealContent.vue';
import {
  fetchFundCashFlowPerformance,
  type FundCashFlowPerformance,
} from '@/plugins/fund/api';

const props = defineProps<{
  refreshKey: number;
}>();

const performance = ref<FundCashFlowPerformance | null>(null);
const loading = ref(false);

const tradeDateRange = computed(() => {
  if (!performance.value?.earliest_trade_date || !performance.value.latest_trade_date) {
    return '--';
  }
  if (performance.value.earliest_trade_date === performance.value.latest_trade_date) {
    return performance.value.earliest_trade_date;
  }
  return `${performance.value.earliest_trade_date} 至 ${performance.value.latest_trade_date}`;
});

async function loadPerformance(): Promise<void> {
  loading.value = true;
  try {
    performance.value = await fetchFundCashFlowPerformance();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '现金流收益加载失败');
  } finally {
    loading.value = false;
  }
}

function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return `¥${numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`;
}

function formatSignedMoney(value: string | null | undefined): string {
  if (value === null || value === undefined) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const prefix = numeric > 0 ? '+' : numeric < 0 ? '-' : '';
  return `${prefix}${formatMoney(Math.abs(numeric))}`;
}

function formatPercent(value: string | null | undefined): string {
  if (value === null || value === undefined) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const prefix = numeric > 0 ? '+' : '';
  return `${prefix}${(numeric * 100).toFixed(2)}%`;
}

function profitClass(value: string | null | undefined): string {
  const numeric = Number(value ?? 0);
  if (numeric > 0) return 'profit positive';
  if (numeric < 0) return 'profit negative';
  return 'profit';
}

watch(
  () => props.refreshKey,
  () => {
    void loadPerformance();
  },
);

onMounted(() => {
  void loadPerformance();
});
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.performance-warning {
  color: var(--color-muted);
  font-size: 12px;
}

.performance-summary {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.performance-summary > div {
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 12px;
}

.performance-summary span {
  color: var(--color-muted);
  font-size: 12px;
}

.performance-summary strong {
  font-size: 15px;
  overflow-wrap: anywhere;
}

.performance-status {
  align-items: center;
  color: var(--color-muted);
  display: flex;
  flex-wrap: wrap;
  font-size: 12px;
  gap: 10px;
  margin-top: 12px;
}

.status-pill {
  border: 1px solid currentColor;
  border-radius: 999px;
  padding: 3px 8px;
}

.status-pill.ready {
  color: #48c78e;
}

.status-pill.waiting {
  color: #e6a23c;
}

.performance-warning {
  margin: 10px 0 0;
}

.profit.positive {
  color: #f56c6c;
}

.profit.negative {
  color: #48c78e;
}

@media (max-width: 1080px) {
  .performance-summary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .performance-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
