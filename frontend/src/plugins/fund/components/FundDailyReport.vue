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

        <div v-if="aiSummaryStatus" class="ai-summary">
          <div class="ai-summary-heading">
            <div>
              <strong>AI 日报摘要</strong>
              <span>{{ aiSummaryStatus.input_contract }}</span>
            </div>
            <div class="ai-summary-actions">
              <span class="ai-status" :class="aiStatusClass">{{ aiStatusLabel }}</span>
              <el-button
                :icon="MagicStick"
                :loading="generatingAiSummary"
                :disabled="!aiSummaryAvailable"
                @click="generateAiSummary"
              >
                生成 AI 摘要
              </el-button>
            </div>
          </div>
          <div class="ai-summary-status">
            <span>提供方：通用 Webhook</span>
            <span>目标：{{ aiSummaryStatus.target }}</span>
          </div>
          <div v-if="aiSummary" class="ai-summary-result">
            <div>
              <strong>{{ aiSummary.report_date }}</strong>
              <span>{{ formatDateTime(aiSummary.generated_at) }}</span>
            </div>
            <p>{{ aiSummary.summary }}</p>
            <small>{{ aiSummary.disclaimer }}</small>
          </div>
          <p v-else class="ai-summary-note">{{ aiSummaryStatus.note }}</p>
          <p v-if="!aiSummaryAvailable" class="ai-summary-help">
            请在 Portainer 的 HAP Stack 环境变量中启用并配置 AI Webhook，密钥不会保存在网页中。
          </p>
        </div>

        <div v-if="insights" class="daily-insights">
          <div class="daily-insights-heading">
            <div>
              <strong>变化洞察</strong>
              <span>{{ insights.contract_version }}</span>
            </div>
            <span>共 {{ insights.snapshot_count }} 条日报快照</span>
          </div>
          <div class="period-comparisons">
            <div
              v-for="comparison in insights.comparisons"
              :key="comparison.period_days"
              class="period-comparison"
            >
              <div class="period-comparison-heading">
                <strong>近 {{ comparison.period_days }} 日</strong>
                <span :class="`is-${comparison.status}`">
                  {{ comparison.status === 'available' ? '可比较' : '样本积累中' }}
                </span>
              </div>
              <div v-if="comparison.change" class="period-change-grid">
                <div>
                  <span>估值变化</span>
                  <strong :class="valueClass(comparison.change.current_value)">
                    {{ formatSignedMoney(comparison.change.current_value) }}
                  </strong>
                </div>
                <div>
                  <span>浮盈亏变化</span>
                  <strong :class="valueClass(comparison.change.unrealized_profit)">
                    {{ formatSignedMoney(comparison.change.unrealized_profit) }}
                  </strong>
                </div>
                <div>
                  <span>收益率变化</span>
                  <strong :class="valueClass(comparison.change.unrealized_return_rate)">
                    {{ formatPercentagePointChange(comparison.change.unrealized_return_rate) }}
                  </strong>
                </div>
                <div>
                  <span>持仓变化</span>
                  <strong>{{ formatSignedCount(comparison.change.position_count) }}</strong>
                </div>
              </div>
              <p>{{ comparison.explanation }}</p>
            </div>
          </div>
          <div v-if="insights.alerts.length" class="insight-alerts">
            <div
              v-for="alert in insights.alerts"
              :key="alert.code"
              class="insight-alert"
              :class="`is-${alert.level}`"
            >
              <InfoFilled />
              <div>
                <span>{{ alert.message }}</span>
                <small>{{ alert.sample_scope }}</small>
              </div>
            </div>
          </div>
          <p v-else class="insight-clear">当前快照中没有触发需要核对的异常变化。</p>
          <p class="insight-disclaimer">{{ insights.disclaimers.join(' ') }}</p>
        </div>

        <div class="snapshot-history">
          <div class="snapshot-history-heading">
            <div>
              <strong>日报历史变化</strong>
              <span>最近 30 个快照 · 每天最多一条</span>
            </div>
            <span>同一天再次保存会更新当天快照</span>
          </div>
          <div v-if="snapshots.length" class="snapshot-change-summary">
            <span>{{ latestChangeSummary }}</span>
            <small>变化均与上一个已保存快照比较，不等同于单日市场涨跌。</small>
          </div>
          <div v-if="snapshots.length" ref="snapshotChartRef" class="snapshot-chart"></div>
          <div v-if="snapshots.length" class="snapshot-table">
            <div class="snapshot-row snapshot-header">
              <span>日期</span>
              <span>当前估值</span>
              <span>浮盈亏</span>
              <span>收益率</span>
              <span>较前次估值</span>
              <span>数据状态</span>
            </div>
            <div v-for="snapshot in historyRows" :key="snapshot.id" class="snapshot-row">
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
import { Bell, DocumentAdd, InfoFilled, MagicStick, Refresh } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import type { ECharts, EChartsOption } from 'echarts';
import { ElMessage } from 'element-plus';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { chartTheme } from '@/charts/useChartTheme';
import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  fetchFundDailyReport,
  fetchFundDailyAiSummaryStatus,
  fetchFundDailyInsights,
  fetchFundDailySnapshots,
  generateFundDailyAiSummary,
  pushFundDailyReport,
  saveFundDailySnapshot,
  type FundDailyAiSummary,
  type FundDailyAiSummaryStatus,
  type FundDailyReport,
  type FundDailyInsights,
  type FundDailySnapshot,
} from '@/plugins/fund/api';

const props = defineProps<{
  refreshKey: number;
}>();

const report = ref<FundDailyReport | null>(null);
const insights = ref<FundDailyInsights | null>(null);
const aiSummaryStatus = ref<FundDailyAiSummaryStatus | null>(null);
const aiSummary = ref<FundDailyAiSummary | null>(null);
const snapshots = ref<FundDailySnapshot[]>([]);
const loading = ref(false);
const pushing = ref(false);
const savingSnapshot = ref(false);
const generatingAiSummary = ref(false);
const snapshotChartRef = ref<HTMLDivElement | null>(null);
let snapshotChart: ECharts | null = null;

const historyRows = computed(() => snapshots.value.slice(0, 10));

const aiSummaryAvailable = computed(
  () => aiSummaryStatus.value?.enabled === true && aiSummaryStatus.value.configured === true,
);

const aiStatusLabel = computed(() => {
  if (aiSummaryAvailable.value) return '可生成';
  if (aiSummaryStatus.value?.enabled) return '待配置';
  return '未启用';
});

const aiStatusClass = computed(() => ({
  'is-available': aiSummaryAvailable.value,
  'is-pending': aiSummaryStatus.value?.enabled === true && !aiSummaryStatus.value.configured,
}));

const latestChangeSummary = computed(() => {
  const latest = snapshots.value[0];
  const change = latest?.change_from_previous;
  if (!latest || !change) return '当前快照将作为后续变化比较的基准。';
  return [
    `估值 ${formatSignedMoney(change.current_value)}`,
    `浮盈亏 ${formatSignedMoney(change.unrealized_profit)}`,
    `收益率 ${formatPercentagePointChange(change.unrealized_return_rate)}`,
    `持仓 ${formatSignedCount(change.position_count)}`,
  ].join(' · ');
});

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
  aiSummary.value = null;
  try {
    const [reportResult, historyResult, insightsResult, aiStatusResult] = await Promise.allSettled([
      fetchFundDailyReport(),
      fetchFundDailySnapshots(30),
      fetchFundDailyInsights(),
      fetchFundDailyAiSummaryStatus(),
    ]);
    if (reportResult.status === 'rejected') throw reportResult.reason;
    report.value = reportResult.value;
    snapshots.value = historyResult.status === 'fulfilled' ? historyResult.value.items : [];
    insights.value = insightsResult.status === 'fulfilled' ? insightsResult.value : null;
    aiSummaryStatus.value = aiStatusResult.status === 'fulfilled' ? aiStatusResult.value : null;
    await nextTick();
    renderSnapshotChart();
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
    const [history, insightResult] = await Promise.all([
      fetchFundDailySnapshots(30),
      fetchFundDailyInsights(),
    ]);
    snapshots.value = history.items;
    insights.value = insightResult;
    await nextTick();
    renderSnapshotChart();
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

async function generateAiSummary(): Promise<void> {
  if (!aiSummaryAvailable.value) return;
  generatingAiSummary.value = true;
  try {
    aiSummary.value = await generateFundDailyAiSummary();
    ElMessage.success('AI 日报摘要已生成');
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'AI 日报摘要生成失败');
  } finally {
    generatingAiSummary.value = false;
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

function formatPercentagePointChange(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const prefix = numeric > 0 ? '+' : '';
  return `${prefix}${(numeric * 100).toFixed(2)} 个百分点`;
}

function formatSignedCount(value: number): string {
  return `${value > 0 ? '+' : ''}${value} 条`;
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

function renderSnapshotChart(): void {
  if (!snapshotChartRef.value || snapshots.value.length === 0) {
    snapshotChart?.clear();
    return;
  }
  snapshotChart ??= echarts.init(snapshotChartRef.value);
  const points = [...snapshots.value].reverse();
  const option: EChartsOption = {
    ...chartTheme,
    color: ['#38bdf8', '#f59e0b'],
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const items = Array.isArray(params) ? params : [params];
        const date = String(items[0]?.name ?? '');
        const lines = items.map((item) => {
          const value = Number(item.value);
          const display = item.seriesName === '收益率'
            ? `${value.toFixed(2)}%`
            : formatMoney(value);
          return `${item.marker ?? ''}${item.seriesName}: ${display}`;
        });
        return [date, ...lines].join('<br>');
      },
    },
    legend: {
      data: ['当前估值', '收益率'],
      textStyle: { color: '#94a3b8' },
    },
    grid: { left: 62, right: 58, top: 44, bottom: 42 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: points.map((point) => point.report_date),
      axisLabel: { color: '#94a3b8', hideOverlap: true },
    },
    yAxis: [
      {
        type: 'value',
        axisLabel: { color: '#94a3b8', formatter: (value: number) => `¥${value}` },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } },
      },
      {
        type: 'value',
        axisLabel: { color: '#94a3b8', formatter: '{value}%' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '当前估值',
        type: 'line',
        showSymbol: points.length < 8,
        smooth: 0.16,
        data: points.map((point) => point.current_value === null ? null : Number(point.current_value)),
      },
      {
        name: '收益率',
        type: 'line',
        yAxisIndex: 1,
        showSymbol: points.length < 8,
        smooth: 0.16,
        data: points.map((point) => point.unrealized_return_rate === null
          ? null
          : Number((Number(point.unrealized_return_rate) * 100).toFixed(2))),
      },
    ],
  };
  snapshotChart.setOption(option, true);
}

function resizeSnapshotChart(): void {
  snapshotChart?.resize();
}

onMounted(() => {
  window.addEventListener('resize', resizeSnapshotChart);
  void loadReport();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeSnapshotChart);
  snapshotChart?.dispose();
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

.snapshot-history-heading > div {
  align-items: baseline;
  display: flex;
  gap: 10px;
}

.snapshot-history-heading span,
.snapshot-history > p {
  color: var(--color-muted);
  font-size: 12px;
}

.snapshot-change-summary {
  align-items: baseline;
  border-left: 2px solid rgba(56, 189, 248, 0.72);
  display: flex;
  gap: 12px;
  padding: 2px 0 2px 10px;
}

.snapshot-change-summary span {
  color: var(--color-text);
  font-size: 13px;
}

.snapshot-change-summary small {
  color: var(--color-muted);
  font-size: 11px;
}

.snapshot-chart {
  height: 250px;
  min-width: 0;
  width: 100%;
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

.ai-summary {
  border-block: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 10px;
  padding-block: 14px;
}

.ai-summary-heading,
.ai-summary-heading > div,
.ai-summary-actions,
.ai-summary-result > div {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.ai-summary-heading > div,
.ai-summary-result > div {
  justify-content: flex-start;
}

.ai-summary-heading span,
.ai-summary-status,
.ai-summary-note,
.ai-summary-help,
.ai-summary-result span,
.ai-summary-result small {
  color: var(--color-muted);
  font-size: 12px;
}

.ai-summary-status {
  display: flex;
  gap: 16px;
}

.ai-status {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 6px;
  padding: 4px 8px;
}

.ai-status.is-available {
  border-color: rgba(52, 211, 153, 0.3);
  color: #34d399;
}

.ai-status.is-pending {
  border-color: rgba(251, 191, 36, 0.3);
  color: #fbbf24;
}

.ai-summary-result {
  border-left: 2px solid rgba(56, 189, 248, 0.72);
  display: grid;
  gap: 8px;
  padding-left: 10px;
}

.ai-summary-result p,
.ai-summary-note,
.ai-summary-help {
  line-height: 1.65;
  margin: 0;
}

.ai-summary-result p {
  color: var(--color-text);
  font-size: 13px;
  white-space: pre-wrap;
}

.ai-summary-help {
  color: #fbbf24;
}

.daily-insights {
  border-block: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 12px;
  padding-block: 14px;
}

.daily-insights-heading,
.daily-insights-heading > div,
.period-comparison-heading {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.daily-insights-heading > div {
  justify-content: flex-start;
}

.daily-insights-heading span,
.period-comparison p,
.insight-disclaimer {
  color: var(--color-muted);
  font-size: 12px;
}

.period-comparisons {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.period-comparison {
  display: grid;
  gap: 10px;
  padding: 4px 16px 4px 0;
}

.period-comparison + .period-comparison {
  border-left: 1px solid rgba(148, 163, 184, 0.14);
  padding: 4px 0 4px 16px;
}

.period-comparison-heading > span {
  color: #fbbf24;
  font-size: 12px;
}

.period-comparison-heading > span.is-available {
  color: #34d399;
}

.period-change-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.period-change-grid > div {
  display: grid;
  gap: 4px;
}

.period-change-grid span,
.insight-alert small {
  color: var(--color-muted);
  font-size: 11px;
}

.period-change-grid strong {
  color: var(--color-text);
  font-size: 13px;
}

.period-comparison p,
.insight-disclaimer {
  line-height: 1.6;
  margin: 0;
}

.insight-alerts {
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 8px;
  padding-top: 10px;
}

.insight-alert {
  align-items: flex-start;
  color: #7dd3fc;
  display: flex;
  font-size: 13px;
  gap: 8px;
}

.insight-alert.is-warning {
  color: #fbbf24;
}

.insight-alert > div {
  display: grid;
  gap: 2px;
}

.insight-clear {
  color: #34d399;
  font-size: 13px;
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
  .daily-insights-heading,
  .daily-insights-heading > div,
  .ai-summary-heading,
  .ai-summary-heading > div,
  .ai-summary-actions,
  .ai-summary-status,
  .ai-summary-result > div,
  .snapshot-history-heading,
  .snapshot-history-heading > div,
  .snapshot-change-summary,
  .risk-digest-title {
    align-items: stretch;
    flex-direction: column;
  }

  .snapshot-chart {
    height: 220px;
  }

  .report-metrics,
  .report-status,
  .analysis-context-metrics,
  .period-change-grid,
  .risk-digest-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .period-comparisons {
    grid-template-columns: 1fr;
  }

  .period-comparison,
  .period-comparison + .period-comparison {
    border-left: 0;
    padding: 4px 0;
  }

  .period-comparison + .period-comparison {
    border-top: 1px solid rgba(148, 163, 184, 0.14);
    padding-top: 12px;
  }
}
</style>
