<template>
  <RevealContent as="section" class="panel fund-panel" :delay="375">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">基金日报</h2>
        <span class="panel-meta">
          按已保存的持仓、观察池和净值生成，不代表实时行情
        </span>
      </div>
      <div class="report-actions">
        <el-button :icon="Bell" :loading="pushing" @click="pushReport">
          推送到 Bark
        </el-button>
        <el-button :icon="Refresh" :loading="loading" @click="loadReport">
          刷新
        </el-button>
      </div>
    </div>
    <div class="panel-body">
      <div v-if="report" class="report-content">
        <div class="report-time">
          <strong>{{ report.report_date }}</strong>
          <span>生成于 {{ formatDateTime(report.generated_at) }}</span>
        </div>

        <div class="report-metrics">
          <div>
            <span>持仓成本</span>
            <strong>{{ formatMoney(report.holding_summary.total_cost) }}</strong>
          </div>
          <div>
            <span>当前估值</span>
            <strong>{{ formatMoney(report.holding_summary.current_value) }}</strong>
          </div>
          <div>
            <span>浮盈亏</span>
            <strong :class="profitClass">
              {{ formatSignedMoney(report.holding_summary.unrealized_profit) }}
            </strong>
          </div>
          <div>
            <span>收益率</span>
            <strong :class="profitClass">
              {{ formatPercent(report.holding_summary.unrealized_return_rate) }}
            </strong>
          </div>
        </div>

        <div class="report-status">
          <div>
            <span>持仓</span>
            <strong>{{ report.holding_summary.position_count }} 条</strong>
          </div>
          <div>
            <span>观察池</span>
            <strong>{{ report.watchlist_summary.item_count }} 只</strong>
          </div>
          <div>
            <span>最新净值</span>
            <strong>{{ report.nav_summary.latest_nav_date ?? '--' }}</strong>
          </div>
          <div>
            <span>估值完整度</span>
            <strong>
              {{ report.allocation.current_nav_count }}/{{ report.allocation.position_count }}
            </strong>
          </div>
          <div>
            <span>最大单基金</span>
            <strong>{{ formatPercent(report.allocation.top_holding_weight) }}</strong>
          </div>
          <div>
            <span>集中度 HHI</span>
            <strong>{{ formatHhi(report.allocation.concentration_hhi) }}</strong>
          </div>
          <div>
            <span>交易流水</span>
            <strong>{{ report.transaction_summary.transaction_count }} 条</strong>
          </div>
          <div>
            <span>净现金流</span>
            <strong>
              {{ formatSignedMoney(report.transaction_summary.net_cash_flow) }}
            </strong>
          </div>
        </div>

        <div v-if="report.holding_risk.fund_count" class="risk-digest">
          <div class="risk-digest-title">
            <strong>风险摘要</strong>
            <span>
              {{ report.holding_risk.analyzed_fund_count }}/{{ report.holding_risk.fund_count }}
              只基金可计算 · 每只最多 {{ report.holding_risk.sample_limit }} 个交易日
            </span>
          </div>
          <div class="risk-digest-metrics">
            <div>
              <span>最高年化波动</span>
              <strong>{{ highestVolatilityItem?.fund_name ?? '--' }}</strong>
              <small>{{ formatPercent(highestVolatilityItem?.annualized_volatility ?? null) }}</small>
            </div>
            <div>
              <span>样本内最大回撤</span>
              <strong>{{ deepestDrawdownItem?.fund_name ?? '--' }}</strong>
              <small class="is-loss">
                {{ formatPercent(deepestDrawdownItem?.maximum_drawdown ?? null) }}
              </small>
            </div>
          </div>
          <p>
            按各基金自身历史净值分别计算，不代表整个持仓组合的波动率，也不构成投资建议。
          </p>
        </div>

        <div v-if="report.alerts.length" class="report-alerts">
          <div
            v-for="alert in report.alerts"
            :key="alert.code"
            class="report-alert"
            :class="`is-${alert.level}`"
          >
            <InfoFilled />
            <span>{{ alert.message }}</span>
          </div>
        </div>
        <p v-else class="report-clear">
          当前数据完整，暂未发现需要提醒的数据状态。
        </p>

        <p class="report-note">
          日报用于整理已记录数据。缺少当前净值的持仓不会计入浮盈亏，
          配置分析则会使用成本暂估，两者口径不同。
        </p>
      </div>
      <div v-else-if="loading" class="report-loading">正在生成日报...</div>
      <EmptyState
        v-else
        title="日报暂时不可用"
        description="刷新后仍无数据时，请检查后端服务状态。"
      />
    </div>
  </RevealContent>
</template>

<script setup lang="ts">
import { Bell, InfoFilled, Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref, watch } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  fetchFundDailyReport,
  pushFundDailyReport,
  type FundDailyReport,
} from '@/plugins/fund/api';

const props = defineProps<{
  refreshKey: number;
}>();

const report = ref<FundDailyReport | null>(null);
const loading = ref(false);
const pushing = ref(false);

const profitClass = computed(() => {
  const value = Number(report.value?.holding_summary.unrealized_profit ?? 0);
  if (value > 0) return 'is-profit';
  if (value < 0) return 'is-loss';
  return '';
});

const analyzedRiskItems = computed(() =>
  report.value?.holding_risk.items.filter((item) => item.calculation_available) ?? [],
);

const highestVolatilityItem = computed(() => {
  return analyzedRiskItems.value.reduce<(typeof analyzedRiskItems.value)[number] | null>(
    (highest, item) => {
      if (!highest) return item;
      return Number(item.annualized_volatility ?? -1)
        > Number(highest.annualized_volatility ?? -1)
        ? item
        : highest;
    },
    null,
  );
});

const deepestDrawdownItem = computed(() => {
  return analyzedRiskItems.value.reduce<(typeof analyzedRiskItems.value)[number] | null>(
    (deepest, item) => {
      if (!deepest) return item;
      return Number(item.maximum_drawdown ?? 0)
        < Number(deepest.maximum_drawdown ?? 0)
        ? item
        : deepest;
    },
    null,
  );
});

async function loadReport(): Promise<void> {
  loading.value = true;
  try {
    report.value = await fetchFundDailyReport();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '基金日报加载失败');
  } finally {
    loading.value = false;
  }
}

async function pushReport(): Promise<void> {
  pushing.value = true;
  try {
    const result = await pushFundDailyReport();
    const bark = result.results.find((item) => item.channel === 'bark');
    if (bark?.status === 'sent') {
      ElMessage.success('基金日报已推送到 Bark');
      return;
    }
    ElMessage.warning(bark?.message ?? 'Bark 推送未发送');
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '基金日报推送失败');
  } finally {
    pushing.value = false;
  }
}

function formatMoney(value: string | number | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return `¥${numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`;
}

function formatSignedMoney(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const prefix = numeric > 0 ? '+' : numeric < 0 ? '-' : '';
  return `${prefix}${formatMoney(Math.abs(numeric))}`;
}

function formatPercent(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const prefix = numeric > 0 ? '+' : '';
  return `${prefix}${(numeric * 100).toFixed(2)}%`;
}

function formatHhi(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(4) : '--';
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', { hour12: false });
}

onMounted(() => {
  void loadReport();
});

watch(
  () => props.refreshKey,
  () => {
    void loadReport();
  },
);
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.report-note {
  color: var(--color-muted);
  font-size: 12px;
}

.report-content {
  display: grid;
  gap: 16px;
}

.report-time {
  align-items: center;
  display: flex;
  gap: 10px;
}

.report-actions {
  display: flex;
  gap: 8px;
}

.report-time strong {
  color: var(--color-text);
}

.report-time span {
  color: var(--color-muted);
  font-size: 12px;
}

.report-metrics,
.report-status {
  display: grid;
  gap: 10px;
}

.report-metrics {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.report-status {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.report-metrics div,
.report-status div {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 12px;
}

.report-metrics span,
.report-status span {
  color: var(--color-muted);
  font-size: 12px;
}

.report-metrics strong,
.report-status strong {
  color: var(--color-text);
  font-size: 14px;
}

.report-alerts {
  display: grid;
  gap: 8px;
}

.risk-digest {
  border-block: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 10px;
  padding-block: 14px;
}

.risk-digest-title {
  align-items: baseline;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.risk-digest-title span,
.risk-digest p {
  color: var(--color-muted);
  font-size: 12px;
}

.risk-digest-metrics {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.risk-digest-metrics div {
  display: grid;
  gap: 4px;
}

.risk-digest-metrics span,
.risk-digest-metrics small {
  color: var(--color-muted);
  font-size: 12px;
}

.risk-digest-metrics strong {
  color: var(--color-text);
  font-size: 14px;
}

.risk-digest p {
  line-height: 1.6;
  margin: 0;
}

.report-alert {
  align-items: center;
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-radius: 8px;
  color: #7dd3fc;
  display: flex;
  font-size: 13px;
  gap: 8px;
  padding: 10px 12px;
}

.report-alert.is-warning {
  border-color: rgba(251, 191, 36, 0.28);
  color: #fbbf24;
}

.report-clear {
  color: #34d399;
  font-size: 13px;
  margin: 0;
}

.report-note {
  line-height: 1.6;
  margin: 0;
}

.report-loading {
  color: var(--color-muted);
  padding: 20px 0;
  text-align: center;
}

.is-profit {
  color: #ef4444 !important;
}

.is-loss {
  color: #22c55e !important;
}

@media (max-width: 980px) {
  .report-status {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .panel-header,
  .report-actions,
  .report-time,
  .risk-digest-title {
    align-items: stretch;
    flex-direction: column;
  }

  .report-metrics,
  .report-status,
  .risk-digest-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
