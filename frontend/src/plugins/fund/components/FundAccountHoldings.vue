<template>
  <section class="panel account-panel">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">天天账户快照</h2>
        <span class="panel-meta">
          官方账户只读快照，不会覆盖手工持仓
        </span>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadSnapshot">
        刷新
      </el-button>
    </div>

    <div class="panel-body">
      <div v-if="snapshot" class="account-summary">
        <div>
          <span>官方资产</span>
          <strong>{{ formatMoney(snapshot.total_asset_value) }}</strong>
        </div>
        <div>
          <span>官方项目</span>
          <strong>{{ snapshot.holding_count }}</strong>
        </div>
        <div>
          <span>匹配手工持仓</span>
          <strong>{{ snapshot.matched_count }}</strong>
        </div>
        <div>
          <span>同步时间</span>
          <strong class="snapshot-time">{{ formatDateTime(snapshot.captured_at) }}</strong>
        </div>
      </div>

      <div v-if="snapshot?.items.length" class="account-table">
        <div class="account-row table-head">
          <span>资产</span>
          <span>类型</span>
          <span>官方金额</span>
          <span>日收益</span>
          <span>持仓收益</span>
          <span>手工估值</span>
          <span>差额</span>
          <span>对照</span>
        </div>
        <div
          v-for="item in snapshot.items"
          :key="item.id"
          class="account-row"
        >
          <span>
            <strong>{{ item.asset_name }}</strong>
            <small>{{ item.asset_code }}</small>
          </span>
          <span>{{ assetTypeText(item.asset_type) }}</span>
          <span>{{ formatMoney(item.asset_value) }}</span>
          <span :class="profitClass(item.daily_profit)">
            {{ formatMoney(item.daily_profit) }}
          </span>
          <span :class="profitClass(item.hold_profit)">
            {{ formatMoney(item.hold_profit) }}
            <small>{{ formatPercent(item.hold_profit_rate) }}</small>
          </span>
          <span>{{ formatMoney(item.manual_current_value) }}</span>
          <span :class="profitClass(item.value_difference)">
            {{ formatSignedMoney(item.value_difference) }}
          </span>
          <span :class="['comparison-status', `is-${item.comparison_status}`]">
            {{ comparisonText(item.comparison_status) }}
          </span>
        </div>
      </div>

      <div v-else-if="loading" class="account-message">正在读取账户快照...</div>
      <div v-else-if="errorMessage" class="account-message is-error">
        {{ errorMessage }}
      </div>
      <div v-else class="account-message">
        尚未同步天天账户。运行本机持仓同步脚本后，这里会显示官方资产和手工持仓差异。
      </div>

      <div v-if="snapshot?.manual_only.length" class="manual-only">
        <strong>仅存在于手工持仓</strong>
        <span
          v-for="item in snapshot.manual_only"
          :key="item.fund_code"
        >
          {{ item.fund_name }}（{{ item.fund_code }}）
        </span>
      </div>

      <p v-if="snapshot" class="account-note">
        官方金额来自 {{ snapshot.account_label }}；差额仅在对应手工持仓都有当前净值时计算。
        “仅官方”不会自动新增手工份额或成本，避免错误污染收益分析。
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { onMounted, ref } from 'vue';

import {
  fetchLatestFundAccountSnapshot,
  type FundAccountComparisonStatus,
  type FundAccountSnapshot,
} from '@/plugins/fund/api';

const snapshot = ref<FundAccountSnapshot | null>(null);
const loading = ref(false);
const errorMessage = ref('');

const comparisonLabels: Record<FundAccountComparisonStatus, string> = {
  matched: '已匹配',
  official_only: '仅官方',
  manual_incomplete: '手工估值不完整',
};

async function loadSnapshot(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    snapshot.value = await fetchLatestFundAccountSnapshot();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '账户快照加载失败';
  } finally {
    loading.value = false;
  }
}

function comparisonText(status: FundAccountComparisonStatus): string {
  return comparisonLabels[status];
}

function assetTypeText(value: string): string {
  const labels: Record<string, string> = {
    fund: '基金',
    hqb: '活期宝',
    gdlc: '高端理财',
    tg: '投顾',
  };
  return labels[value] ?? value;
}

function formatMoney(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return `¥${numeric.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatSignedMoney(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  const prefix = numeric > 0 ? '+' : '';
  return `${prefix}${formatMoney(value)}`;
}

function formatPercent(value: string | null): string {
  if (value === null) return '--';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '--';
  return `${(numeric * 100).toFixed(2)}%`;
}

function formatDateTime(value: string): string {
  const utcValue = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`;
  return new Date(utcValue).toLocaleString('zh-CN', { hour12: false });
}

function profitClass(value: string | null): string {
  const numeric = Number(value ?? 0);
  if (numeric > 0) return 'profit positive';
  if (numeric < 0) return 'profit negative';
  return 'profit';
}

onMounted(loadSnapshot);
</script>

<style scoped>
.account-panel {
  margin-top: 16px;
}

.account-summary {
  border-block: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 14px;
  padding: 12px 0;
}

.account-summary div {
  display: grid;
  gap: 5px;
}

.account-summary span,
.account-row small,
.account-note,
.account-message,
.manual-only {
  color: var(--color-muted);
  font-size: 12px;
}

.account-summary strong {
  font-size: 17px;
  font-variant-numeric: tabular-nums;
}

.account-summary .snapshot-time {
  font-size: 13px;
}

.account-table {
  overflow-x: auto;
}

.account-row {
  align-items: center;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: grid;
  font-size: 13px;
  gap: 12px;
  grid-template-columns: minmax(210px, 1.5fr) 82px repeat(5, 110px) 104px;
  min-width: 1030px;
  padding: 11px 0;
}

.account-row > span:first-child,
.account-row > span:nth-child(5) {
  display: grid;
  gap: 3px;
}

.table-head {
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 650;
}

.profit,
.account-row > span:nth-child(n + 3):nth-child(-n + 7) {
  font-variant-numeric: tabular-nums;
}

.positive,
.is-matched {
  color: #34d399;
}

.negative,
.account-message.is-error {
  color: #fb7185;
}

.is-official_only {
  color: #67e8f9;
}

.is-manual_incomplete {
  color: #fbbf24;
}

.comparison-status {
  font-size: 12px;
  font-weight: 700;
}

.manual-only {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 14px;
}

.manual-only strong {
  color: var(--color-text);
}

.account-note {
  line-height: 1.7;
  margin: 12px 0 0;
}

@media (max-width: 720px) {
  .account-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    row-gap: 14px;
  }
}
</style>
