<template>
  <div>
    <RevealContent as="section" class="page-header" :delay="20">
      <div>
        <h1 class="page-title">Fund</h1>
        <div class="page-subtitle">ETF、QDII、资产配置和收益分析模块</div>
      </div>
    </RevealContent>

    <div class="grid metrics">
      <MetricCard label="持仓数量" :value="String(summary?.position_count ?? 0)" meta="已录入记录" :delay="80" />
      <MetricCard label="基金数量" :value="String(summary?.fund_count ?? 0)" meta="去重基金" :delay="140" />
      <MetricCard label="总成本" :value="formatMoney(summary?.total_cost)" meta="手动持仓" :delay="200" />
      <MetricCard label="浮盈亏" :value="formatMoney(summary?.unrealized_profit)" :meta="returnRateMeta" :delay="260" />
    </div>

    <RevealContent as="section" class="panel fund-panel" :delay="300">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">录入持仓</h2>
          <span class="panel-meta">先记录你的真实持仓，行情和净值后续再接入</span>
        </div>
      </div>
      <div class="panel-body">
        <div class="position-form">
          <div v-if="editingPositionId !== null" class="edit-banner wide">
            正在编辑持仓 #{{ editingPositionId }}
          </div>
          <label>
            <span>基金代码</span>
            <el-input v-model="form.fund_code" placeholder="例如 513100" />
          </label>
          <label>
            <span>基金名称</span>
            <el-input v-model="form.fund_name" placeholder="例如 纳指 ETF" />
          </label>
          <label>
            <span>基金类型</span>
            <el-select v-model="form.fund_type">
              <el-option label="ETF" value="ETF" />
              <el-option label="QDII" value="QDII" />
              <el-option label="指数基金" value="指数基金" />
              <el-option label="混合型" value="混合型" />
              <el-option label="债券型" value="债券型" />
              <el-option label="货币型" value="货币型" />
              <el-option label="其他" value="其他" />
            </el-select>
          </label>
          <label>
            <span>账户</span>
            <el-input v-model="form.account_name" placeholder="默认账户" />
          </label>
          <label>
            <span>持有份额</span>
            <el-input-number v-model="form.shares" :min="0" :precision="4" :step="100" />
          </label>
          <label>
            <span>成本净值</span>
            <el-input-number v-model="form.cost_price" :min="0" :precision="4" :step="0.01" />
          </label>
          <label>
            <span>总成本</span>
            <el-input-number v-model="form.total_cost" :min="0" :precision="2" :step="100" />
          </label>
          <label>
            <span>当前净值</span>
            <el-input-number v-model="form.current_nav" :min="0" :precision="4" :step="0.01" />
          </label>
          <label>
            <span>买入日期</span>
            <el-date-picker v-model="form.opened_at" type="date" value-format="YYYY-MM-DD" />
          </label>
          <label>
            <span>标签</span>
            <el-input v-model="form.tags" placeholder="A股, 海外, 长期" />
          </label>
          <label class="wide">
            <span>备注</span>
            <el-input v-model="form.note" placeholder="定投、波段、核心仓等" />
          </label>
          <div class="form-actions">
            <el-button plain @click="resetForm">{{ editingPositionId === null ? '清空' : '取消编辑' }}</el-button>
            <el-button type="primary" :loading="saving" @click="savePosition">
              {{ editingPositionId === null ? '保存持仓' : '更新持仓' }}
            </el-button>
          </div>
        </div>
      </div>
    </RevealContent>

    <RevealContent as="section" class="panel fund-panel" :delay="340">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">当前持仓</h2>
          <span class="panel-meta">当前净值未填写时，只统计成本，不计算浮盈亏</span>
        </div>
      </div>
      <div class="panel-body">
        <div v-if="positions.length" class="position-table">
          <div class="position-row table-head">
            <span>基金</span>
            <span>类型</span>
            <span>份额</span>
            <span>成本</span>
            <span>当前估值</span>
            <span>浮盈亏</span>
            <span>操作</span>
          </div>
          <div v-for="position in positions" :key="position.id" class="position-row">
            <span>
              <strong>{{ position.fund_name }}</strong>
              <small>{{ position.fund_code }} · {{ position.account_name }}</small>
            </span>
            <span>{{ position.fund_type }}</span>
            <span>{{ formatNumber(position.shares, 4) }}</span>
            <span>{{ formatMoney(position.total_cost) }}</span>
            <span>{{ formatMoney(position.current_value) }}</span>
            <span :class="profitClass(position.unrealized_profit)">
              {{ formatMoney(position.unrealized_profit) }}
            </span>
            <span class="row-actions">
              <el-button text size="small" @click="editPosition(position)">编辑</el-button>
              <el-button
                text
                size="small"
                type="danger"
                :loading="deletingPositionId === position.id"
                @click="removePosition(position)"
              >
                删除
              </el-button>
            </span>
          </div>
        </div>
        <EmptyState
          v-else
          title="还没有持仓"
          description="先录入一只基金，HAP 才能开始做收益、配置和日报分析。"
        />
      </div>
    </RevealContent>

    <RevealContent as="section" class="panel fund-panel" :delay="320">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">基金模块路线图</h2>
          <span class="panel-meta">{{ fundStatus?.description ?? '正在加载基金插件状态' }}</span>
        </div>
      </div>
      <div class="panel-body">
        <div v-if="isLoading" class="fund-loading">加载中...</div>
        <div v-else-if="errorMessage" class="fund-error">{{ errorMessage }}</div>
        <div v-else class="fund-roadmap">
          <div v-for="module in fundStatus?.modules ?? []" :key="module.code" class="roadmap-item">
            <div>
              <strong>{{ module.name }}</strong>
              <p>{{ module.description }}</p>
            </div>
            <span class="status-pill">{{ statusText(module.status) }}</span>
          </div>
        </div>
      </div>
    </RevealContent>

    <RevealContent as="section" class="panel fund-panel" :delay="380">
      <div class="panel-header">
        <h2 class="panel-title">下一步</h2>
      </div>
      <div class="panel-body">
        <p class="next-step">{{ fundStatus?.next_step ?? '等待后端基金插件状态接口返回。' }}</p>
      </div>
    </RevealContent>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import {
  createFundPosition,
  deleteFundPosition,
  fetchFundHoldingSummary,
  fetchFundPositions,
  fetchFundStatus,
  type FundHoldingSummary,
  type FundPosition,
  type FundPositionCreate,
  type FundStatus,
  updateFundPosition,
} from '@/plugins/fund/api';

const fundStatus = ref<FundStatus | null>(null);
const positions = ref<FundPosition[]>([]);
const summary = ref<FundHoldingSummary | null>(null);
const isLoading = ref(false);
const saving = ref(false);
const deletingPositionId = ref<number | null>(null);
const errorMessage = ref('');
const editingPositionId = ref<number | null>(null);
const form = ref<FundPositionCreate>({
  fund_code: '',
  fund_name: '',
  fund_type: 'ETF',
  account_name: '默认账户',
  shares: 0,
  cost_price: 0,
  total_cost: null,
  current_nav: null,
  opened_at: null,
  tags: '',
  note: '',
});

const labelMap: Record<string, string> = {
  scaffolded: '已接入',
  planned: '规划中',
  in_progress: '进行中',
  not_configured: '未配置',
  not_created: '未创建',
  created: '已创建',
};

const statusText = (status: string): string => labelMap[status] ?? status;

const returnRateMeta = computed(() => {
  if (!summary.value?.unrealized_return_rate) return '等待当前净值';
  return `${(Number(summary.value.unrealized_return_rate) * 100).toFixed(2)}%`;
});

function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '--';
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return '--';
  return `¥${numberValue.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`;
}

function formatNumber(value: string | number, digits = 2): string {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return '--';
  return numberValue.toLocaleString('zh-CN', { maximumFractionDigits: digits });
}

function profitClass(value: string | null): string {
  const numberValue = Number(value ?? 0);
  if (numberValue > 0) return 'profit positive';
  if (numberValue < 0) return 'profit negative';
  return 'profit';
}

function resetForm(): void {
  editingPositionId.value = null;
  form.value = {
    fund_code: '',
    fund_name: '',
    fund_type: 'ETF',
    account_name: '默认账户',
    shares: 0,
    cost_price: 0,
    total_cost: null,
    current_nav: null,
    opened_at: null,
    tags: '',
    note: '',
  };
}

async function loadHoldings(): Promise<void> {
  const [nextPositions, nextSummary] = await Promise.all([
    fetchFundPositions(),
    fetchFundHoldingSummary(),
  ]);
  positions.value = nextPositions;
  summary.value = nextSummary;
}

async function savePosition(): Promise<void> {
  if (!form.value.fund_code.trim() || !form.value.fund_name.trim()) {
    ElMessage.warning('基金代码和名称不能为空');
    return;
  }
  if (form.value.shares <= 0 || form.value.cost_price <= 0) {
    ElMessage.warning('份额和成本净值必须大于 0');
    return;
  }
  saving.value = true;
  try {
    const payload = {
      ...form.value,
      total_cost: form.value.total_cost && form.value.total_cost > 0 ? form.value.total_cost : null,
      current_nav: form.value.current_nav && form.value.current_nav > 0 ? form.value.current_nav : null,
    };
    if (editingPositionId.value === null) {
      await createFundPosition(payload);
      ElMessage.success('持仓已保存');
    } else {
      await updateFundPosition(editingPositionId.value, payload);
      ElMessage.success('持仓已更新');
    }
    resetForm();
    await loadHoldings();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '持仓保存失败');
  } finally {
    saving.value = false;
  }
}

function editPosition(position: FundPosition): void {
  editingPositionId.value = position.id;
  form.value = {
    fund_code: position.fund_code,
    fund_name: position.fund_name,
    fund_type: position.fund_type,
    account_name: position.account_name,
    shares: Number(position.shares),
    cost_price: Number(position.cost_price),
    total_cost: Number(position.total_cost),
    current_nav: position.current_nav === null ? null : Number(position.current_nav),
    opened_at: position.opened_at,
    tags: position.tags,
    note: position.note,
  };
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function removePosition(position: FundPosition): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除 ${position.fund_name}（${position.fund_code}）这条持仓？`,
      '确认删除持仓',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
  } catch {
    return;
  }

  deletingPositionId.value = position.id;
  try {
    await deleteFundPosition(position.id);
    if (editingPositionId.value === position.id) {
      resetForm();
    }
    ElMessage.success('持仓已删除');
    await loadHoldings();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '持仓删除失败');
  } finally {
    deletingPositionId.value = null;
  }
}

onMounted(async () => {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    fundStatus.value = await fetchFundStatus();
    await loadHoldings();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '基金模块状态加载失败';
  } finally {
    isLoading.value = false;
  }
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

.position-form {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.position-form label {
  display: grid;
  gap: 7px;
}

.position-form label span {
  color: var(--color-muted);
  font-size: 12px;
}

.position-form .wide {
  grid-column: span 2;
}

.edit-banner {
  border: 1px solid rgba(56, 189, 248, 0.28);
  border-radius: 8px;
  color: #7dd3fc;
  font-size: 13px;
  padding: 10px 12px;
}

.form-actions {
  align-items: end;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.position-table {
  display: grid;
  gap: 8px;
}

.position-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  grid-template-columns: 1.5fr 0.65fr repeat(4, 0.8fr) 0.95fr;
  padding: 11px 12px;
}

.position-row span {
  color: var(--color-muted);
  font-size: 13px;
}

.position-row strong {
  color: var(--color-text);
  display: block;
}

.position-row small {
  display: block;
  font-size: 12px;
  margin-top: 4px;
}

.table-head {
  background: rgba(15, 23, 42, 0.45);
  font-weight: 700;
}

.profit.positive {
  color: #86efac;
}

.profit.negative {
  color: #fca5a5;
}

.row-actions {
  align-items: center;
  display: flex;
  gap: 6px;
}

.fund-roadmap {
  display: grid;
  gap: 10px;
}

.roadmap-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.32);
  padding: 14px;
}

.roadmap-item strong {
  color: var(--color-text);
  font-size: 14px;
}

.roadmap-item p,
.next-step,
.fund-loading,
.fund-error {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.7;
  margin: 6px 0 0;
}

.status-pill {
  border: 1px solid rgba(56, 189, 248, 0.34);
  border-radius: 999px;
  color: #7dd3fc;
  flex: 0 0 auto;
  font-size: 12px;
  padding: 4px 9px;
}

.fund-error {
  color: #fca5a5;
}

@media (max-width: 720px) {
  .position-form,
  .position-row {
    grid-template-columns: 1fr;
  }

  .position-form .wide {
    grid-column: auto;
  }

  .form-actions {
    justify-content: flex-start;
  }

  .roadmap-item {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
