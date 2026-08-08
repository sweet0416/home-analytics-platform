<template>
  <RevealContent as="section" class="panel fund-panel" :delay="295">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">交易流水</h2>
        <span class="panel-meta">
          保存买入、卖出、分红和费用；当前不会自动修改持仓
        </span>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadTransactions">
        刷新
      </el-button>
    </div>
    <div class="panel-body">
      <div class="transaction-form">
        <label>
          <span>流水类型</span>
          <el-select v-model="form.transaction_type">
            <el-option
              v-for="option in transactionTypes"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </label>
        <label>
          <span>交易日期</span>
          <el-date-picker
            v-model="form.trade_date"
            type="date"
            value-format="YYYY-MM-DD"
          />
        </label>
        <label>
          <span>基金代码</span>
          <el-input v-model="form.fund_code" placeholder="例如 110022" />
        </label>
        <label>
          <span>基金名称</span>
          <el-input v-model="form.fund_name" placeholder="例如 易方达消费行业" />
        </label>
        <label>
          <span>基金类型</span>
          <el-select v-model="form.fund_type">
            <el-option
              v-for="type in fundTypes"
              :key="type"
              :label="type"
              :value="type"
            />
          </el-select>
        </label>
        <label>
          <span>账户</span>
          <el-input v-model="form.account_name" placeholder="默认账户" />
        </label>
        <label v-if="usesShares">
          <span>份额</span>
          <el-input-number
            v-model="form.shares"
            :min="0"
            :precision="4"
            :step="100"
          />
        </label>
        <label v-if="usesShares">
          <span>成交净值</span>
          <el-input-number
            v-model="form.unit_price"
            :min="0"
            :precision="4"
            :step="0.01"
          />
        </label>
        <label v-else>
          <span>{{ form.transaction_type === 'dividend' ? '分红金额' : '费用金额' }}</span>
          <el-input-number
            v-model="form.amount"
            :min="0"
            :precision="2"
            :step="10"
          />
        </label>
        <label v-if="form.transaction_type !== 'fee'">
          <span>附加手续费</span>
          <el-input-number
            v-model="form.fee"
            :min="0"
            :precision="2"
            :step="1"
          />
        </label>
        <label class="wide">
          <span>备注</span>
          <el-input
            v-model="form.note"
            placeholder="定投、赎回、现金分红、平台费用等"
          />
        </label>
        <div class="transaction-actions wide">
          <span v-if="usesShares" class="calculated-amount">
            成交金额：{{ formatMoney(calculatedAmount) }}
          </span>
          <div>
            <el-button plain @click="resetForm">清空</el-button>
            <el-button
              plain
              :icon="Search"
              :loading="lookingUp"
              @click="lookupFund"
            >
              查询基金
            </el-button>
            <el-button type="primary" :loading="saving" @click="saveTransaction">
              保存流水
            </el-button>
          </div>
        </div>
      </div>

      <div class="transaction-summary">
        <div>
          <span>流水数量</span>
          <strong>{{ summary?.transaction_count ?? 0 }}</strong>
        </div>
        <div>
          <span>累计买入</span>
          <strong>{{ formatMoney(summary?.total_buy) }}</strong>
        </div>
        <div>
          <span>累计卖出</span>
          <strong>{{ formatMoney(summary?.total_sell) }}</strong>
        </div>
        <div>
          <span>累计分红</span>
          <strong>{{ formatMoney(summary?.total_dividend) }}</strong>
        </div>
        <div>
          <span>累计费用</span>
          <strong>{{ formatMoney(summary?.total_fee) }}</strong>
        </div>
        <div>
          <span>净现金流</span>
          <strong :class="cashFlowClass(summary?.net_cash_flow)">
            {{ formatSignedMoney(summary?.net_cash_flow) }}
          </strong>
        </div>
      </div>

      <div v-if="latestTtSkillSyncAt" class="transaction-sync-status">
        <span class="sync-status-dot" aria-hidden="true" />
        <span>天天 Skills 最近同步：{{ formatDateTime(latestTtSkillSyncAt) }}</span>
        <span>已导入 {{ importedTransactionCount }} 条</span>
      </div>

      <div class="transaction-filters">
        <el-input v-model="transactionQuery" clearable placeholder="搜索基金代码或名称" />
        <el-select v-model="transactionTypeFilter" clearable placeholder="全部流水类型">
          <el-option
            v-for="option in transactionTypes"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <span class="filter-result">显示 {{ paginatedTransactions.length }} / {{ filteredTransactions.length }} 条</span>
      </div>

      <div v-if="paginatedTransactions.length" class="transaction-table">
        <div class="transaction-row table-head">
          <span>日期 / 类型</span>
          <span>基金</span>
          <span>账户</span>
          <span>份额 / 净值</span>
          <span>金额</span>
          <span>现金流</span>
          <span>操作</span>
        </div>
        <div
          v-for="transaction in paginatedTransactions"
          :key="transaction.id"
          class="transaction-row"
        >
          <span>
            <strong>{{ transaction.trade_date }}</strong>
            <small>{{ transactionTypeText(transaction.transaction_type) }}</small>
          </span>
          <span>
            <strong>{{ transaction.fund_name }}</strong>
            <small>{{ transaction.fund_code }} · {{ transaction.fund_type }}</small>
          </span>
          <span>
            <strong>{{ transaction.account_name }}</strong>
            <small>{{ transactionSourceText(transaction) }}</small>
            <small v-if="transaction.external_trade_id">
              {{ transaction.external_trade_id }}
            </small>
          </span>
          <span>
            {{ formatNumber(transaction.shares, 4) }}
            <small>{{ formatNumber(transaction.unit_price, 4) }}</small>
          </span>
          <span>
            {{ formatMoney(transaction.amount) }}
            <small>费用 {{ formatMoney(transaction.fee) }}</small>
          </span>
          <span :class="cashFlowClass(transaction.cash_flow)">
            {{ formatSignedMoney(transaction.cash_flow) }}
          </span>
          <span>
            <el-button
              text
              type="danger"
              :icon="Delete"
              :loading="deletingId === transaction.id"
              title="删除流水"
              @click="removeTransaction(transaction)"
            />
          </span>
        </div>
      </div>
      <div v-else-if="transactions.length" class="transaction-message">
        没有符合当前筛选条件的流水。
      </div>
      <EmptyState
        v-else-if="!loading"
        title="还没有交易流水"
        description="流水账本独立于当前持仓，后续用于计算真实收益和持仓演变。"
      />

      <el-pagination
        v-if="filteredTransactions.length > pageSize"
        v-model:current-page="currentPage"
        class="transaction-pagination"
        layout="prev, pager, next"
        :page-size="pageSize"
        :total="filteredTransactions.length"
        background
      />

      <p class="transaction-note">
        净现金流以账户视角计算：买入和费用为流出，卖出和分红为流入。
        删除流水不会影响当前持仓。
      </p>
    </div>
  </RevealContent>
</template>

<script setup lang="ts">
import { Delete, Refresh, Search } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, ref, watch } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  createFundTransaction,
  deleteFundTransaction,
  fetchFundTransactions,
  fetchFundTransactionSummary,
  lookupLatestFundNav,
  type FundTransaction,
  type FundTransactionCreate,
  type FundTransactionSummary,
  type FundTransactionType,
} from '@/plugins/fund/api';

const emit = defineEmits<{
  changed: [];
}>();

const fundTypes = ['ETF', 'QDII', '指数基金', '混合型', '债券型', '货币型', '其他'];
const transactionTypes: Array<{ label: string; value: FundTransactionType }> = [
  { label: '买入', value: 'buy' },
  { label: '卖出', value: 'sell' },
  { label: '分红', value: 'dividend' },
  { label: '费用', value: 'fee' },
];

const transactions = ref<FundTransaction[]>([]);
const summary = ref<FundTransactionSummary | null>(null);
const loading = ref(false);
const saving = ref(false);
const lookingUp = ref(false);
const deletingId = ref<number | null>(null);
const transactionQuery = ref('');
const transactionTypeFilter = ref<FundTransactionType | ''>('');
const currentPage = ref(1);
const pageSize = 20;
const form = ref<FundTransactionCreate>(buildDefaultForm());

const usesShares = computed(() => (
  form.value.transaction_type === 'buy' || form.value.transaction_type === 'sell'
));
const calculatedAmount = computed(() => (
  Number(form.value.shares ?? 0) * Number(form.value.unit_price ?? 0)
));
const filteredTransactions = computed(() => {
  const query = transactionQuery.value.trim().toLowerCase();
  return transactions.value.filter((transaction) => {
    const matchesQuery = !query
      || transaction.fund_code.toLowerCase().includes(query)
      || transaction.fund_name.toLowerCase().includes(query);
    const matchesType = !transactionTypeFilter.value
      || transaction.transaction_type === transactionTypeFilter.value;
    return matchesQuery && matchesType;
  });
});
const paginatedTransactions = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return filteredTransactions.value.slice(start, start + pageSize);
});
const importedTransactions = computed(() => (
  transactions.value.filter((transaction) => transaction.external_source === 'ttfund_skills')
));
const importedTransactionCount = computed(() => importedTransactions.value.length);
const latestTtSkillSyncAt = computed(() => {
  const latest = importedTransactions.value
    .map((transaction) => transaction.updated_at)
    .sort()
    .at(-1);
  return latest ?? null;
});

function buildDefaultForm(): FundTransactionCreate {
  return {
    fund_code: '',
    fund_name: '',
    fund_type: 'ETF',
    account_name: '默认账户',
    transaction_type: 'buy',
    trade_date: new Date().toISOString().slice(0, 10),
    shares: null,
    unit_price: null,
    amount: null,
    fee: 0,
    note: '',
  };
}

function resetForm(): void {
  form.value = buildDefaultForm();
}

watch([transactionQuery, transactionTypeFilter], () => {
  currentPage.value = 1;
});

async function loadTransactions(): Promise<void> {
  loading.value = true;
  try {
    const [nextTransactions, nextSummary] = await Promise.all([
      fetchFundTransactions(),
      fetchFundTransactionSummary(),
    ]);
    transactions.value = nextTransactions;
    summary.value = nextSummary;
    if (currentPage.value > Math.max(1, Math.ceil(filteredTransactions.value.length / pageSize))) {
      currentPage.value = 1;
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '交易流水加载失败');
  } finally {
    loading.value = false;
  }
}

async function lookupFund(): Promise<void> {
  if (!form.value.fund_code.trim()) {
    ElMessage.warning('请先填写基金代码');
    return;
  }
  lookingUp.value = true;
  try {
    const fund = await lookupLatestFundNav({
      fund_code: form.value.fund_code.trim(),
      fund_type: form.value.fund_type,
    });
    form.value.fund_code = fund.fund_code;
    form.value.fund_name = fund.fund_name;
    form.value.fund_type = fund.fund_type;
    ElMessage.success(`已识别 ${fund.fund_name}`);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '基金信息查询失败');
  } finally {
    lookingUp.value = false;
  }
}

async function saveTransaction(): Promise<void> {
  if (!form.value.fund_code.trim() || !form.value.fund_name.trim()) {
    ElMessage.warning('请填写基金代码和名称');
    return;
  }
  if (usesShares.value && (!form.value.shares || !form.value.unit_price)) {
    ElMessage.warning('买入或卖出必须填写份额和成交净值');
    return;
  }
  if (!usesShares.value && !form.value.amount) {
    ElMessage.warning('请填写金额');
    return;
  }

  saving.value = true;
  try {
    await createFundTransaction({
      ...form.value,
      amount: usesShares.value ? null : form.value.amount,
      fee: form.value.transaction_type === 'fee' ? 0 : form.value.fee,
    });
    ElMessage.success('交易流水已保存');
    resetForm();
    await loadTransactions();
    emit('changed');
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '交易流水保存失败');
  } finally {
    saving.value = false;
  }
}

async function removeTransaction(transaction: FundTransaction): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除 ${transaction.trade_date} 的${transactionTypeText(transaction.transaction_type)}流水？`,
      '确认删除流水',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
  } catch {
    return;
  }

  deletingId.value = transaction.id;
  try {
    await deleteFundTransaction(transaction.id);
    ElMessage.success('交易流水已删除');
    await loadTransactions();
    emit('changed');
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '交易流水删除失败');
  } finally {
    deletingId.value = null;
  }
}

function transactionTypeText(type: FundTransactionType): string {
  return transactionTypes.find((item) => item.value === type)?.label ?? type;
}

function transactionSourceText(transaction: FundTransaction): string {
  return transaction.external_source === 'ttfund_skills'
    ? '天天 Skills'
    : '手动录入';
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
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

function formatNumber(value: string | null, precision: number): string {
  if (value === null) return '--';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(precision) : '--';
}

function cashFlowClass(value: string | null | undefined): string {
  const numeric = Number(value ?? 0);
  if (numeric > 0) return 'is-inflow';
  if (numeric < 0) return 'is-outflow';
  return '';
}

onMounted(() => {
  void loadTransactions();
});
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.transaction-note {
  color: var(--color-muted);
  font-size: 12px;
}

.transaction-form {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.transaction-form label {
  display: grid;
  gap: 7px;
}

.transaction-form label > span {
  color: var(--color-muted);
  font-size: 12px;
}

.transaction-form .wide {
  grid-column: 1 / -1;
}

.transaction-actions {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.calculated-amount {
  color: #7dd3fc;
  font-size: 13px;
}

.transaction-summary {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  margin-top: 18px;
}

.transaction-summary div {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 11px;
}

.transaction-summary span,
.transaction-row span {
  color: var(--color-muted);
  font-size: 12px;
}

.transaction-summary strong,
.transaction-row strong {
  color: var(--color-text);
}

.transaction-filters {
  align-items: center;
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.transaction-filters .el-input {
  max-width: 260px;
}

.transaction-filters .el-select {
  max-width: 160px;
}

.filter-result,
.transaction-message {
  color: var(--color-muted);
  font-size: 12px;
}

.transaction-table {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.transaction-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  grid-template-columns: 0.9fr 1.4fr 0.8fr 0.9fr 0.85fr 0.85fr 44px;
  padding: 10px 12px;
}

.transaction-row small {
  display: block;
  margin-top: 4px;
}

.table-head {
  background: rgba(15, 23, 42, 0.45);
  font-weight: 700;
}

.is-inflow {
  color: #ef4444 !important;
}

.is-outflow {
  color: #22c55e !important;
}

.transaction-sync-status {
  align-items: center;
  color: var(--color-muted);
  display: flex;
  flex-wrap: wrap;
  font-size: 12px;
  gap: 10px;
  margin-top: 12px;
}

.sync-status-dot {
  background: #22c55e;
  border-radius: 999px;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.14);
  height: 7px;
  width: 7px;
}

.transaction-note {
  line-height: 1.6;
  margin: 16px 0 0;
}

.transaction-pagination {
  justify-content: center;
  margin-top: 14px;
}

@media (max-width: 980px) {
  .transaction-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .transaction-summary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .transaction-table {
    overflow-x: auto;
  }

  .transaction-row {
    min-width: 900px;
  }
}

@media (max-width: 640px) {
  .panel-header,
  .transaction-actions,
  .transaction-filters {
    align-items: stretch;
    flex-direction: column;
  }

  .transaction-filters .el-input,
  .transaction-filters .el-select {
    max-width: none;
  }

  .transaction-form,
  .transaction-summary {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
