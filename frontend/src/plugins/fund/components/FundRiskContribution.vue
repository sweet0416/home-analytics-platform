<template>
  <RevealContent as="section" class="panel fund-panel" :delay="376">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">组合风险贡献</h2>
        <span class="panel-meta">
          结合当前仓位、历史波动和基金间联动，观察谁真正贡献了组合波动
        </span>
      </div>
      <div class="risk-actions">
        <el-select v-model="sampleLimit" class="sample-select" @change="loadContribution">
          <el-option
            v-for="option in sampleOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadContribution">
          刷新
        </el-button>
      </div>
    </div>

    <div class="panel-body">
      <div v-if="contribution?.calculation_available" class="risk-content">
        <div class="risk-summary">
          <div>
            <span>组合年化波动</span>
            <strong>{{ formatPercent(contribution.portfolio_annualized_volatility) }}</strong>
          </div>
          <div>
            <span>单体波动加权</span>
            <strong>{{ formatPercent(contribution.weighted_standalone_volatility) }}</strong>
          </div>
          <div>
            <span>分散化比率</span>
            <strong>{{ formatRatio(contribution.diversification_ratio) }}</strong>
          </div>
          <div>
            <span>分散效果</span>
            <strong :class="diversificationClass">{{ diversificationLabel }}</strong>
          </div>
          <div>
            <span>共同收益样本</span>
            <strong>{{ contribution.sample_count }} 日</strong>
            <small>{{ sampleRange }}</small>
          </div>
        </div>

        <div class="risk-table">
          <div class="risk-row table-head">
            <span>基金</span>
            <span>仓位占比</span>
            <span>单体年化波动</span>
            <span>风险贡献</span>
            <span>风险贡献结构</span>
            <span>通俗解释</span>
          </div>
          <div
            v-for="item in contribution.items"
            :key="item.fund_code"
            class="risk-row"
          >
            <span>
              <strong>{{ item.fund_name }}</strong>
              <small>{{ item.fund_code }}</small>
            </span>
            <span>{{ formatPercent(item.allocation_weight) }}</span>
            <span>{{ formatPercent(item.annualized_volatility) }}</span>
            <span :class="contributionClass(item.contribution_ratio)">
              {{ formatPercent(item.contribution_ratio) }}
            </span>
            <span class="bar-cell">
              <span class="bar-track">
                <span
                  :class="['bar-fill', contributionClass(item.contribution_ratio)]"
                  :style="barStyle(item.contribution_ratio)"
                />
              </span>
            </span>
            <span>{{ explainContribution(item) }}</span>
          </div>
        </div>

        <p v-if="contribution.excluded_fund_codes.length" class="excluded-note">
          因历史净值不足未纳入：{{ contribution.excluded_fund_codes.join('、') }}
        </p>
        <p class="risk-note">{{ contribution.warning }}</p>
      </div>
      <EmptyState
        v-else
        title="暂时无法计算风险贡献"
        description="至少需要一只持仓基金拥有三个以上共同净值日期，并且组合收益存在波动。"
      />
    </div>
  </RevealContent>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref, watch } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  fetchFundRiskContribution,
  type FundRiskContribution,
  type FundRiskContributionItem,
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
const contribution = ref<FundRiskContribution | null>(null);
const loading = ref(false);

const sampleRange = computed(() => {
  if (!contribution.value?.start_date || !contribution.value.end_date) {
    return '样本不足';
  }
  return `${contribution.value.start_date} 至 ${contribution.value.end_date}`;
});

const diversificationLabel = computed(() => {
  const value = Number(contribution.value?.diversification_ratio);
  if (!Number.isFinite(value)) return '样本不足';
  if (value >= 1.5) return '分散明显';
  if (value >= 1.15) return '分散有效';
  if (value >= 1.03) return '略有分散';
  return '分散有限';
});

const diversificationClass = computed(() => {
  const value = Number(contribution.value?.diversification_ratio);
  if (!Number.isFinite(value)) return '';
  if (value >= 1.15) return 'is-diversified';
  if (value < 1.03) return 'is-warning';
  return '';
});

async function loadContribution(): Promise<void> {
  loading.value = true;
  try {
    contribution.value = await fetchFundRiskContribution(sampleLimit.value);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '风险贡献加载失败');
  } finally {
    loading.value = false;
  }
}

function formatPercent(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : '--';
}

function formatRatio(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : '--';
}

function contributionClass(value: string): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '';
  if (numeric < 0) return 'is-diversified';
  if (numeric >= 0.4) return 'is-warning';
  return '';
}

function barStyle(value: string): Record<string, string> {
  const numeric = Number(value);
  const width = Number.isFinite(numeric)
    ? Math.min(Math.abs(numeric) * 100, 100)
    : 0;
  return { width: `${width}%` };
}

function explainContribution(item: FundRiskContributionItem): string {
  const contributionRatio = Number(item.contribution_ratio);
  const allocationWeight = Number(item.allocation_weight);
  if (!Number.isFinite(contributionRatio) || !Number.isFinite(allocationWeight)) {
    return '样本不足';
  }
  if (contributionRatio < 0) return '样本内降低了组合波动';
  const difference = contributionRatio - allocationWeight;
  if (difference >= 0.1) return '风险贡献明显高于仓位';
  if (difference <= -0.1) return '风险贡献低于仓位，有分散作用';
  return '风险贡献与仓位大致相当';
}

onMounted(() => {
  void loadContribution();
});

watch(
  () => props.refreshKey,
  () => {
    void loadContribution();
  },
);
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.risk-note,
.excluded-note {
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
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  padding-bottom: 14px;
}

.risk-summary div {
  display: grid;
  gap: 5px;
}

.risk-summary span,
.risk-row span,
.risk-summary small {
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
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 12px;
  grid-template-columns:
    minmax(220px, 1.5fr) 110px 130px 110px
    minmax(150px, 1fr) minmax(220px, 1.3fr);
  min-width: 980px;
  padding: 10px 4px;
}

.risk-row > span:first-child {
  display: grid;
  gap: 3px;
}

.risk-row small {
  color: var(--color-muted);
  font-size: 11px;
}

.table-head {
  font-weight: 700;
}

.bar-cell {
  width: 100%;
}

.bar-track {
  background: rgba(148, 163, 184, 0.14);
  display: block;
  height: 8px;
  overflow: hidden;
  width: 100%;
}

.bar-fill {
  background: #38bdf8;
  display: block;
  height: 100%;
  min-width: 2px;
}

.bar-fill.is-warning {
  background: #f59e0b;
}

.bar-fill.is-diversified {
  background: #22c55e;
}

.risk-note,
.excluded-note {
  line-height: 1.6;
  margin: 0;
}

.is-warning {
  color: #f59e0b !important;
}

.is-diversified {
  color: #22c55e !important;
}

@media (max-width: 920px) {
  .risk-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
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
