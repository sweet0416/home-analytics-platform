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
        <el-button :icon="DocumentAdd" :loading="savingSnapshot" @click="saveSnapshot">
          保存今日快照
        </el-button>
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

        <div class="analysis-context">
          <div class="analysis-context-heading">
            <div>
              <strong>结构化分析摘要</strong>
              <span>{{ report.analysis_context.contract_version }}</span>
            </div>
            <span class="quality-badge" :class="`is-${qualityLevel}`">
              {{ qualityLabel }}
            </span>
          </div>
          <div class="analysis-context-metrics">
            <div>
              <span>风险覆盖</span>
              <strong>
                {{ report.analysis_context.data_quality.risk_covered_fund_count }}/{{
                  report.analysis_context.data_quality.risk_fund_count
                }} 只
              </strong>
            </div>
            <div>
              <span>风险样本</span>
              <strong>{{ report.analysis_context.data_quality.risk_sample_count }} 个</strong>
            </div>
            <div>
              <span>目标配置</span>
              <strong>
                {{ report.analysis_context.data_quality.target_configured_count }}/{{
                  report.analysis_context.data_quality.position_count
                }} 条
              </strong>
            </div>
            <div>
              <span>可追溯事实</span>
              <strong>{{ report.analysis_context.facts.length }} 项</strong>
            </div>
          </div>
          <p>当前内容由固定规则生成，为后续 AI 总结提供带样本口径的数据，不直接生成投资结论。</p>
        </div>

        <div class="snapshot-history">
          <div class="snapshot-history-heading">
            <strong>日报历史变化</strong>
            <span>每天最多一条；同一天再次保存会更新当天快照</span>
          </div>
          <div v-if="snapshots.length" class="snapshot-table">
            <div class="snapshot-row snapshot-header">
              <span>日期</span>
              <span>当前估值</span>
              <span>浮盈亏</span>
              <span>收益率</span>
              <span>较前次估值</span>
              <span>数据状态</span>
            </div>
            <div v-for="snapshot in snapshots" :key="snapshot.id" class="snapshot-row">
              <strong>{{ snapshot.report_date }}</strong>
              <span>{{ formatMoney(snapshot.current_value) }}</span>
              <span :class="valueClass(snapshot.unrealized_profit)">
                {{ formatSignedMoney(snapshot.unrealized_profit) }}
              </span>
              <span :class="valueClass(snapshot.unrealized_return_rate)">
                {{ formatPercent(snapshot.unrealized_return_rate) }}
              </span>
              <span :class="valueClass(snapshot.change_from_previous?.current_value ?? null)">
                {{ formatSignedMoney(snapshot.change_from_previous?.current_value ?? null) }}
              </span>
              <span class="snapshot-quality" :class="`is-${snapshot.quality_level}`">
                {{ qualityText(snapshot.quality_level) }}
              </span>
            </div>
          </div>
          <p v-else>还没有历史快照。净值自动更新成功后会保存，也可以手动保存今天的数据。</p>
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
import { Bell, DocumentAdd, InfoFilled, Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref, watch } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  fetchFundDailyReport,
  fetchFundDailySnapshots,
  pushFundDailyReport,
  saveFundDailySnapshot,
  type FundDailyReport,
  type FundDailySnapshot,
} from '@/plugins/fund/api';

const props = defineProps<{
  refreshKey: number;
}>();

const report = ref<FundDailyReport | null>(null);
const snapshots = ref<FundDailySnapshot[]>([]);
const loading = ref(false);
const pushing = ref(false);
const savingSnapshot = ref(false);

const profitClass = computed(() => {
  const value = Number(report.value?.holding_summary.unrealized_profit ?? 0);
  if (value > 0) return 'is-profit';
  if (value < 0) return 'is-loss';
  return '';
});

const qualityLevel = computed(
  () => report.value?.analysis_context.data_quality.level ?? 'insufficient',
);

const qualityLabel = computed(() => {
  const labels = {
    complete: '数据完整',
    partial: '部分可用',
    insufficient: '样本不足',
  } as const;
  return labels[qualityLevel.value];
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
    const [reportResult, historyResult] = await Promise.allSettled([
      fetchFundDailyReport(),
      fetchFundDailySnapshots(7),
    ]);
    if (reportResult.status === 'rejected') throw reportResult.reason;
    report.value = reportResult.value;
    snapshots.value = historyResult.status === 'fulfilled' ? historyResult.value.items : [];
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '基金日报加载失败');
  } finally {
    loading.value = false;
  }
}

async function saveSnapshot(): Promise<void> {
  savingSnapshot.value = true;
  try {
    await saveFundDailySnapshot();
    snapshots.value = (await fetchFundDailySnapshots(7)).items;
    ElMessage.success('今日基金日报快照已保存');
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '日报快照保存失败');
  } finally {
    savingSnapshot.value = false;
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

function valueClass(value: string | null): string {
  const numeric = Number(value ?? 0);
  if (numeric > 0) return 'is-profit';
  if (numeric < 0) return 'is-loss';
  return '';
}

function qualityText(level: FundDailySnapshot['quality_level']): string {
  return {
    complete: '完整',
    partial: '部分可用',
    insufficient: '样本不足',
  }[level];
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

.snapshot-history {
  display: grid;
  gap: 10px;
}

.snapshot-history-heading {
  align-items: baseline;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.snapshot-history-heading span,
.snapshot-history > p {
  color: var(--color-muted);
  font-size: 12px;
}

.snapshot-table {
  border-block: 1px solid rgba(148, 163, 184, 0.14);
  overflow-x: auto;
}

.snapshot-row {
  align-items: center;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: grid;
  gap: 10px;
  grid-template-columns: 110px repeat(4, minmax(110px, 1fr)) 90px;
  min-width: 760px;
  padding: 9px 4px;
}

.snapshot-row:last-child {
  border-bottom: 0;
}

.snapshot-row span,
.snapshot-row strong {
  font-size: 12px;
}

.snapshot-header span {
  color: var(--color-muted);
}

.snapshot-quality {
  color: #7dd3fc;
}

.snapshot-quality.is-complete {
  color: #34d399;
}

.snapshot-quality.is-insufficient {
  color: #fbbf24;
}

.snapshot-history > p {
  line-height: 1.6;
  margin: 0;
}

.analysis-context {
  border-block: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 10px;
  padding-block: 14px;
}

.analysis-context-heading,
.analysis-context-heading > div {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.analysis-context-heading > div {
  justify-content: flex-start;
}

.analysis-context-heading span,
.analysis-context p,
.analysis-context-metrics span {
  color: var(--color-muted);
  font-size: 12px;
}

.analysis-context-metrics {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.analysis-context-metrics div {
  display: grid;
  gap: 4px;
}

.analysis-context-metrics strong {
  color: var(--color-text);
  font-size: 14px;
}

.analysis-context p {
  line-height: 1.6;
  margin: 0;
}

.quality-badge {
  border: 1px solid rgba(56, 189, 248, 0.28);
  border-radius: 6px;
  color: #7dd3fc !important;
  padding: 4px 8px;
}

.quality-badge.is-complete {
  border-color: rgba(52, 211, 153, 0.3);
  color: #34d399 !important;
}

.quality-badge.is-insufficient {
  border-color: rgba(251, 191, 36, 0.3);
  color: #fbbf24 !important;
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
  .snapshot-history-heading,
  .risk-digest-title {
    align-items: stretch;
    flex-direction: column;
  }

  .report-metrics,
  .report-status,
  .analysis-context-metrics,
  .risk-digest-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
