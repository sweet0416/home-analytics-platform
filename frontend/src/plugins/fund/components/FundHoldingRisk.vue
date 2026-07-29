<template>
  <RevealContent as="section" class="panel fund-panel" :delay="375">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">持仓风险比较</h2>
        <span class="panel-meta">使用各基金自身的历史净值样本，不把不同基金强行合成一个风险值</span>
      </div>
      <div class="risk-actions">
        <el-select v-model="sampleLimit" class="sample-select" @change="loadRisk">
          <el-option
            v-for="option in sampleOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadRisk">刷新</el-button>
      </div>
    </div>
    <div class="panel-body">
      <div v-if="risk?.fund_count" class="risk-content">
        <div class="risk-summary">
          <div>
            <span>持仓基金</span>
            <strong>{{ risk.fund_count }} 只</strong>
          </div>
          <div>
            <span>可计算风险</span>
            <strong>{{ risk.analyzed_fund_count }}/{{ risk.fund_count }}</strong>
          </div>
          <div>
            <span>样本上限</span>
            <strong>{{ risk.sample_limit }} 个交易日</strong>
          </div>
        </div>

        <div class="risk-table">
          <div class="risk-row table-head">
            <span>基金</span>
            <span>仓位占比</span>
            <span>样本</span>
            <span>区间收益</span>
            <span>年化波动率</span>
            <span>最大回撤</span>
            <span>上涨日占比</span>
          </div>
          <div v-for="item in risk.items" :key="item.fund_code" class="risk-row">
            <span>
              <strong>{{ item.fund_name }}</strong>
              <small>{{ item.fund_code }} · {{ item.fund_type }}</small>
            </span>
            <span>{{ formatPercent(item.allocation_weight) }}</span>
            <span>
              {{ item.sample_count }} 日
              <small>{{ formatRange(item.start_date, item.end_date) }}</small>
            </span>
            <span :class="rateClass(item.cumulative_return)">
              {{ formatPercent(item.cumulative_return, true) }}
            </span>
            <span>{{ formatPercent(item.annualized_volatility) }}</span>
            <span class="is-loss">{{ formatPercent(item.maximum_drawdown) }}</span>
            <span>{{ formatPercent(item.positive_day_ratio) }}</span>
          </div>
        </div>

        <p class="risk-note">{{ risk.warning }}</p>
      </div>
      <EmptyState
        v-else
        title="还没有可比较的持仓"
        description="录入持仓并同步至少两个交易日的历史净值后，这里会比较各基金的收益、波动和回撤。"
      />
    </div>
  </RevealContent>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { onMounted, ref, watch } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  fetchFundHoldingRisk,
  type FundHoldingRisk,
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
const risk = ref<FundHoldingRisk | null>(null);
const loading = ref(false);

async function loadRisk(): Promise<void> {
  loading.value = true;
  try {
    risk.value = await fetchFundHoldingRisk(sampleLimit.value);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '持仓风险比较加载失败');
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

function formatRange(startDate: string | null, endDate: string | null): string {
  if (!startDate || !endDate) return '样本不足';
  return `${startDate} 至 ${endDate}`;
}

function rateClass(value: string | null): string {
  const numeric = Number(value);
  if (numeric > 0) return 'is-profit';
  if (numeric < 0) return 'is-loss';
  return '';
}

onMounted(() => {
  void loadRisk();
});

watch(
  () => props.refreshKey,
  () => {
    void loadRisk();
  },
);
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.risk-note {
  color: var(--color-muted);
  font-size: 12px;
}

.risk-actions {
  align-items: center;
  display: flex;
  gap: 8px;
}

.sample-select {
  width: 168px;
}

.risk-content {
  display: grid;
  gap: 14px;
}

.risk-summary {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.risk-summary div {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 12px;
}

.risk-summary span,
.risk-row span {
  color: var(--color-muted);
  font-size: 12px;
}

.risk-summary strong,
.risk-row strong {
  color: var(--color-text);
}

.risk-table {
  display: grid;
  gap: 8px;
  overflow-x: auto;
}

.risk-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  grid-template-columns: minmax(180px, 1.5fr) repeat(6, minmax(100px, 0.75fr));
  min-width: 980px;
  padding: 10px 12px;
}

.risk-row small {
  display: block;
  font-size: 11px;
  margin-top: 4px;
}

.table-head {
  background: rgba(15, 23, 42, 0.45);
  font-weight: 700;
}

.risk-note {
  line-height: 1.6;
  margin: 0;
}

.is-profit {
  color: #ef4444 !important;
}

.is-loss {
  color: #22c55e !important;
}

@media (max-width: 640px) {
  .panel-header,
  .risk-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .sample-select {
    width: 100%;
  }

  .risk-summary {
    grid-template-columns: 1fr;
  }
}
</style>
