<template>
  <div>
    <RevealContent as="section" class="page-header" :delay="20">
      <div>
        <h1 class="page-title">Fund</h1>
        <div class="page-subtitle">ETF、QDII、资产配置和收益分析模块</div>
      </div>
    </RevealContent>

    <div class="grid metrics">
      <MetricCard label="观察基金" :value="String(watchSummary?.item_count ?? 0)" meta="关注池记录" :delay="80" />
      <MetricCard label="高优先级" :value="String(watchSummary?.high_priority_count ?? 0)" meta="优先级 1-2" :delay="120" />
      <MetricCard label="净值记录" :value="String(navSummary?.record_count ?? 0)" :meta="latestNavMeta" :delay="160" />
      <MetricCard label="持仓数量" :value="String(summary?.position_count ?? 0)" meta="已录入记录" :delay="200" />
      <MetricCard label="浮盈亏" :value="formatMoney(summary?.unrealized_profit)" :meta="returnRateMeta" :delay="240" />
    </div>

    <RevealContent as="section" class="panel fund-panel" :delay="260">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">基金观察池</h2>
          <span class="panel-meta">先记录想关注的基金，后续净值、估值和日报会从这里展开</span>
        </div>
        <el-button
          :icon="Refresh"
          :loading="syncingWatchlist"
          :disabled="watchItems.length === 0"
          @click="syncWatchlistNavs"
        >
          同步观察池净值
        </el-button>
      </div>
      <div class="panel-body">
        <div class="watchlist-form">
          <div v-if="editingWatchId !== null" class="edit-banner wide">
            正在编辑观察项 #{{ editingWatchId }}
          </div>
          <label>
            <span>基金代码</span>
            <el-input v-model="watchForm.fund_code" placeholder="例如 159915" />
          </label>
          <label>
            <span>基金名称</span>
            <el-input v-model="watchForm.fund_name" placeholder="例如 创业板 ETF" />
          </label>
          <label>
            <span>基金类型</span>
            <el-select v-model="watchForm.fund_type">
              <el-option v-for="type in fundTypes" :key="type" :label="type" :value="type" />
            </el-select>
          </label>
          <label>
            <span>优先级</span>
            <el-input-number v-model="watchForm.priority" :min="1" :max="5" :step="1" />
          </label>
          <label>
            <span>状态</span>
            <el-select v-model="watchForm.status">
              <el-option label="观察中" value="watching" />
              <el-option label="等待回调" value="waiting" />
              <el-option label="已暂停" value="paused" />
              <el-option label="准备买入" value="ready" />
            </el-select>
          </label>
          <label>
            <span>风险等级</span>
            <el-select v-model="watchForm.risk_level">
              <el-option label="低" value="low" />
              <el-option label="中" value="medium" />
              <el-option label="高" value="high" />
            </el-select>
          </label>
          <label>
            <span>目标仓位</span>
            <el-input v-model="watchForm.target_position" placeholder="例如 5%" />
          </label>
          <label>
            <span>标签</span>
            <el-input v-model="watchForm.tags" placeholder="A股, 海外, 长期" />
          </label>
          <label class="wide">
            <span>关注原因</span>
            <el-input v-model="watchForm.watch_reason" placeholder="为什么关注这只基金" />
          </label>
          <label class="wide">
            <span>备注</span>
            <el-input v-model="watchForm.note" placeholder="估值、买入条件、风险提示等" />
          </label>
          <div class="form-actions wide">
            <el-button plain @click="resetWatchForm">{{ editingWatchId === null ? '清空' : '取消编辑' }}</el-button>
            <el-button plain :loading="lookingUpWatch" @click="lookupWatchFund">查询基金信息</el-button>
            <el-button type="primary" :loading="savingWatch" @click="saveWatchItem">
              {{ editingWatchId === null ? '加入观察池' : '更新观察项' }}
            </el-button>
          </div>
        </div>

        <div v-if="watchItems.length" class="watchlist-grid">
          <div v-for="item in watchItems" :key="item.id" class="watch-card">
            <div class="watch-card-head">
              <div>
                <strong>{{ item.fund_name }}</strong>
                <small>{{ item.fund_code }} · {{ item.fund_type }}</small>
              </div>
              <span class="priority-pill">P{{ item.priority }}</span>
            </div>
            <div class="watch-meta">
              <span>{{ statusText(item.status) }}</span>
              <span>{{ riskText(item.risk_level) }}</span>
              <span>{{ item.target_position || '未设仓位' }}</span>
            </div>
            <p>{{ item.watch_reason || '暂无关注原因' }}</p>
            <small class="watch-note">{{ item.tags || '未设置标签' }}</small>
            <div class="row-actions">
              <el-button text size="small" @click="editWatchItem(item)">编辑</el-button>
              <el-button
                text
                size="small"
                type="danger"
                :loading="deletingWatchId === item.id"
                @click="removeWatchItem(item)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
        <EmptyState
          v-else
          title="还没有观察基金"
          description="先把想研究的 ETF、QDII 或主动基金加入观察池。"
        />
      </div>
    </RevealContent>

    <RevealContent as="section" class="panel fund-panel" :delay="280">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">净值记录</h2>
          <span class="panel-meta">手动录入最新净值；如果已有对应持仓，会同步刷新当前净值和浮盈亏</span>
        </div>
      </div>
      <div class="panel-body">
        <div class="nav-form">
          <label>
            <span>基金代码</span>
            <el-input v-model="navForm.fund_code" placeholder="例如 513100" />
          </label>
          <label>
            <span>基金名称</span>
            <el-input v-model="navForm.fund_name" placeholder="例如 纳指 ETF" />
          </label>
          <label>
            <span>基金类型</span>
            <el-select v-model="navForm.fund_type">
              <el-option v-for="type in fundTypes" :key="type" :label="type" :value="type" />
            </el-select>
          </label>
          <label>
            <span>净值日期</span>
            <el-date-picker v-model="navForm.nav_date" type="date" value-format="YYYY-MM-DD" />
          </label>
          <label>
            <span>单位净值</span>
            <el-input-number v-model="navForm.unit_nav" :min="0" :precision="4" :step="0.01" />
          </label>
          <label>
            <span>累计净值</span>
            <el-input-number v-model="navForm.accumulated_nav" :min="0" :precision="4" :step="0.01" />
          </label>
          <label>
            <span>来源</span>
            <el-input v-model="navForm.source" placeholder="manual" />
          </label>
          <label>
            <span>备注</span>
            <el-input v-model="navForm.note" placeholder="估算、收盘、补录等" />
          </label>
          <div class="form-actions">
            <el-button plain @click="resetNavForm">清空</el-button>
            <el-button plain :loading="lookingUpNav" @click="lookupLatestNav">查询基金信息</el-button>
            <el-button plain :loading="syncingNav" @click="syncLatestNav">自动获取最新净值</el-button>
            <el-button type="primary" :loading="savingNav" @click="saveNavRecord">保存净值</el-button>
          </div>
        </div>

        <div v-if="navRecords.length" class="nav-table">
          <div class="nav-row table-head">
            <span>基金</span>
            <span>日期</span>
            <span>单位净值</span>
            <span>累计净值</span>
            <span>来源</span>
            <span>操作</span>
          </div>
          <div v-for="record in navRecords" :key="record.id" class="nav-row">
            <span>
              <strong>{{ record.fund_name }}</strong>
              <small>{{ record.fund_code }} · {{ record.fund_type }}</small>
            </span>
            <span>{{ record.nav_date }}</span>
            <span>{{ formatNumber(record.unit_nav, 4) }}</span>
            <span>{{ formatNullableNumber(record.accumulated_nav, 4) }}</span>
            <span>{{ record.source }}</span>
            <span class="row-actions">
              <el-button
                text
                size="small"
                type="danger"
                :loading="deletingNavId === record.id"
                @click="removeNavRecord(record)"
              >
                删除
              </el-button>
            </span>
          </div>
        </div>
        <EmptyState
          v-else
          title="还没有净值记录"
          description="先手动录入最新净值，后续会接入自动同步。"
        />
      </div>
    </RevealContent>

    <FundNavTrend @synced="handleHistorySynced" />

    <FundTransactions @changed="handleTransactionChanged" />

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
              <el-option v-for="type in fundTypes" :key="type" :label="type" :value="type" />
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
            <el-button plain :loading="lookingUpPosition" @click="lookupPositionFund">查询基金信息</el-button>
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

    <FundAllocation :refresh-key="allocationRefreshKey" />

    <FundDailyReport :refresh-key="dailyReportRefreshKey" />

    <RevealContent as="section" class="panel fund-panel" :delay="380">
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
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import FundAllocation from '@/plugins/fund/components/FundAllocation.vue';
import FundDailyReport from '@/plugins/fund/components/FundDailyReport.vue';
import FundNavTrend from '@/plugins/fund/components/FundNavTrend.vue';
import FundTransactions from '@/plugins/fund/components/FundTransactions.vue';
import {
  createFundNavRecord,
  createFundPosition,
  createFundWatchlistItem,
  deleteFundNavRecord,
  deleteFundPosition,
  deleteFundWatchlistItem,
  fetchFundHoldingSummary,
  fetchFundNavRecords,
  fetchFundNavSummary,
  fetchFundPositions,
  fetchFundStatus,
  fetchFundWatchlist,
  fetchFundWatchlistSummary,
  lookupLatestFundNav,
  syncFundWatchlistNavs,
  syncLatestFundNav,
  type FundHoldingSummary,
  type FundLatestNav,
  type FundNavRecord,
  type FundNavRecordCreate,
  type FundNavSummary,
  type FundPosition,
  type FundPositionCreate,
  type FundStatus,
  type FundWatchlistCreate,
  type FundWatchlistItem,
  type FundWatchlistSummary,
  updateFundPosition,
  updateFundWatchlistItem,
} from '@/plugins/fund/api';

const fundTypes = ['ETF', 'QDII', '指数基金', '混合型', '债券型', '货币型', '其他'];

const fundStatus = ref<FundStatus | null>(null);
const positions = ref<FundPosition[]>([]);
const watchItems = ref<FundWatchlistItem[]>([]);
const navRecords = ref<FundNavRecord[]>([]);
const summary = ref<FundHoldingSummary | null>(null);
const watchSummary = ref<FundWatchlistSummary | null>(null);
const navSummary = ref<FundNavSummary | null>(null);
const allocationRefreshKey = ref(0);
const dailyReportRefreshKey = ref(0);
const isLoading = ref(false);
const saving = ref(false);
const savingWatch = ref(false);
const savingNav = ref(false);
const lookingUpWatch = ref(false);
const lookingUpNav = ref(false);
const lookingUpPosition = ref(false);
const syncingNav = ref(false);
const syncingWatchlist = ref(false);
const deletingPositionId = ref<number | null>(null);
const deletingWatchId = ref<number | null>(null);
const deletingNavId = ref<number | null>(null);
const errorMessage = ref('');
const editingPositionId = ref<number | null>(null);
const editingWatchId = ref<number | null>(null);

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

const watchForm = ref<FundWatchlistCreate>({
  fund_code: '',
  fund_name: '',
  fund_type: 'ETF',
  priority: 3,
  status: 'watching',
  watch_reason: '',
  risk_level: 'medium',
  target_position: '',
  tags: '',
  note: '',
});

const navForm = ref<FundNavRecordCreate>({
  fund_code: '',
  fund_name: '',
  fund_type: 'ETF',
  nav_date: new Date().toISOString().slice(0, 10),
  unit_nav: 0,
  accumulated_nav: null,
  source: 'manual',
  note: '',
});

const labelMap: Record<string, string> = {
  scaffolded: '已接入',
  planned: '规划中',
  in_progress: '进行中',
  not_configured: '未配置',
  not_created: '未创建',
  created: '已创建',
  watching: '观察中',
  waiting: '等待回调',
  paused: '已暂停',
  ready: '准备买入',
};

const riskMap: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
};

const statusText = (status: string): string => labelMap[status] ?? status;
const riskText = (risk: string): string => riskMap[risk] ?? risk;

const returnRateMeta = computed(() => {
  if (!summary.value?.unrealized_return_rate) return '等待当前净值';
  return `${(Number(summary.value.unrealized_return_rate) * 100).toFixed(2)}%`;
});

const latestNavMeta = computed(() => navSummary.value?.latest_nav_date ?? '等待净值');

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

function formatNullableNumber(value: string | number | null, digits = 2): string {
  if (value === null) return '--';
  return formatNumber(value, digits);
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

function resetWatchForm(): void {
  editingWatchId.value = null;
  watchForm.value = {
    fund_code: '',
    fund_name: '',
    fund_type: 'ETF',
    priority: 3,
    status: 'watching',
    watch_reason: '',
    risk_level: 'medium',
    target_position: '',
    tags: '',
    note: '',
  };
}

function resetNavForm(): void {
  navForm.value = {
    fund_code: '',
    fund_name: '',
    fund_type: 'ETF',
    nav_date: new Date().toISOString().slice(0, 10),
    unit_nav: 0,
    accumulated_nav: null,
    source: 'manual',
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
  allocationRefreshKey.value += 1;
  dailyReportRefreshKey.value += 1;
}

async function loadWatchlist(): Promise<void> {
  const [nextItems, nextSummary] = await Promise.all([
    fetchFundWatchlist(),
    fetchFundWatchlistSummary(),
  ]);
  watchItems.value = nextItems;
  watchSummary.value = nextSummary;
  dailyReportRefreshKey.value += 1;
}

async function loadNavRecords(): Promise<void> {
  const [nextRecords, nextSummary] = await Promise.all([
    fetchFundNavRecords(10),
    fetchFundNavSummary(),
  ]);
  navRecords.value = nextRecords;
  navSummary.value = nextSummary;
  dailyReportRefreshKey.value += 1;
}

async function handleHistorySynced(): Promise<void> {
  await Promise.all([loadNavRecords(), loadHoldings()]);
}

function handleTransactionChanged(): void {
  dailyReportRefreshKey.value += 1;
}

async function syncWatchlistNavs(): Promise<void> {
  if (!watchItems.value.length) {
    ElMessage.warning('请先添加观察基金');
    return;
  }
  syncingWatchlist.value = true;
  try {
    const result = await syncFundWatchlistNavs();
    if (result.failed === 0) {
      ElMessage.success(`已同步 ${result.succeeded} 只观察基金的最新净值`);
    } else {
      const failedCodes = result.items
        .filter((item) => item.status === 'failed')
        .map((item) => item.fund_code)
        .join('、');
      ElMessage.warning(
        `同步完成：成功 ${result.succeeded}，失败 ${result.failed}（${failedCodes}）`,
      );
    }
    await Promise.all([loadNavRecords(), loadHoldings()]);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '观察池净值同步失败');
  } finally {
    syncingWatchlist.value = false;
  }
}

async function saveNavRecord(): Promise<void> {
  if (!navForm.value.fund_code.trim() || !navForm.value.fund_name.trim()) {
    ElMessage.warning('基金代码和名称不能为空');
    return;
  }
  if (!navForm.value.nav_date || navForm.value.unit_nav <= 0) {
    ElMessage.warning('净值日期和单位净值必须填写');
    return;
  }
  savingNav.value = true;
  try {
    await createFundNavRecord({
      ...navForm.value,
      accumulated_nav:
        navForm.value.accumulated_nav && navForm.value.accumulated_nav > 0
          ? navForm.value.accumulated_nav
          : null,
      source: navForm.value.source || 'manual',
    });
    ElMessage.success('净值已保存，相关持仓已刷新');
    resetNavForm();
    await Promise.all([loadNavRecords(), loadHoldings()]);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '净值保存失败');
  } finally {
    savingNav.value = false;
  }
}

async function syncLatestNav(): Promise<void> {
  if (!navForm.value.fund_code.trim()) {
    ElMessage.warning('请先填写基金代码');
    return;
  }
  syncingNav.value = true;
  try {
    const record = await syncLatestFundNav({
      fund_code: navForm.value.fund_code,
      fund_type: navForm.value.fund_type || 'unknown',
    });
    ElMessage.success(`已同步 ${record.fund_name} ${record.nav_date} 净值`);
    navForm.value = {
      fund_code: record.fund_code,
      fund_name: record.fund_name,
      fund_type: record.fund_type,
      nav_date: record.nav_date,
      unit_nav: Number(record.unit_nav),
      accumulated_nav: record.accumulated_nav === null ? null : Number(record.accumulated_nav),
      source: record.source,
      note: record.note,
    };
    await Promise.all([loadNavRecords(), loadHoldings()]);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '自动获取净值失败');
  } finally {
    syncingNav.value = false;
  }
}

async function lookupLatestNav(): Promise<void> {
  if (!navForm.value.fund_code.trim()) {
    ElMessage.warning('请先填写基金代码');
    return;
  }
  lookingUpNav.value = true;
  try {
    const latest = await lookupLatestFundNav({
      fund_code: navForm.value.fund_code,
      fund_type: navForm.value.fund_type || 'unknown',
    });
    navForm.value = {
      fund_code: latest.fund_code,
      fund_name: latest.fund_name,
      fund_type: latest.fund_type,
      nav_date: latest.nav_date,
      unit_nav: Number(latest.unit_nav),
      accumulated_nav: latest.accumulated_nav === null ? null : Number(latest.accumulated_nav),
      source: latest.source,
      note: buildSourceNote(latest),
    };
    ElMessage.success(`已查询 ${latest.fund_name} ${latest.nav_date} 净值，尚未保存`);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '查询基金信息失败');
  } finally {
    lookingUpNav.value = false;
  }
}

function buildSourceNote(latest: FundLatestNav): string {
  return `source_url=${latest.source_url}`;
}

async function lookupWatchFund(): Promise<void> {
  if (!watchForm.value.fund_code.trim()) {
    ElMessage.warning('请先填写基金代码');
    return;
  }
  lookingUpWatch.value = true;
  try {
    const latest = await lookupLatestFundNav({
      fund_code: watchForm.value.fund_code,
      fund_type: watchForm.value.fund_type || 'unknown',
    });
    watchForm.value = {
      ...watchForm.value,
      fund_code: latest.fund_code,
      fund_name: latest.fund_name,
      fund_type: latest.fund_type,
    };
    ElMessage.success(`已查询 ${latest.fund_name}，尚未加入观察池`);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '查询基金信息失败');
  } finally {
    lookingUpWatch.value = false;
  }
}

async function lookupPositionFund(): Promise<void> {
  if (!form.value.fund_code.trim()) {
    ElMessage.warning('请先填写基金代码');
    return;
  }
  lookingUpPosition.value = true;
  try {
    const latest = await lookupLatestFundNav({
      fund_code: form.value.fund_code,
      fund_type: form.value.fund_type || 'unknown',
    });
    form.value = {
      ...form.value,
      fund_code: latest.fund_code,
      fund_name: latest.fund_name,
      fund_type: latest.fund_type,
      current_nav: Number(latest.unit_nav),
      note: form.value.note || buildSourceNote(latest),
    };
    ElMessage.success(`已查询 ${latest.fund_name} ${latest.nav_date} 净值，尚未保存持仓`);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '查询基金信息失败');
  } finally {
    lookingUpPosition.value = false;
  }
}

async function removeNavRecord(record: FundNavRecord): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除 ${record.fund_name}（${record.fund_code}）${record.nav_date} 的净值记录？`,
      '确认删除净值',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
  } catch {
    return;
  }

  deletingNavId.value = record.id;
  try {
    await deleteFundNavRecord(record.id);
    ElMessage.success('净值记录已删除');
    await loadNavRecords();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '净值记录删除失败');
  } finally {
    deletingNavId.value = null;
  }
}

async function saveWatchItem(): Promise<void> {
  if (!watchForm.value.fund_code.trim() || !watchForm.value.fund_name.trim()) {
    ElMessage.warning('基金代码和名称不能为空');
    return;
  }
  savingWatch.value = true;
  try {
    if (editingWatchId.value === null) {
      await createFundWatchlistItem(watchForm.value);
      ElMessage.success('已加入观察池');
    } else {
      await updateFundWatchlistItem(editingWatchId.value, watchForm.value);
      ElMessage.success('观察项已更新');
    }
    resetWatchForm();
    await loadWatchlist();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '观察项保存失败');
  } finally {
    savingWatch.value = false;
  }
}

function editWatchItem(item: FundWatchlistItem): void {
  editingWatchId.value = item.id;
  watchForm.value = {
    fund_code: item.fund_code,
    fund_name: item.fund_name,
    fund_type: item.fund_type,
    priority: item.priority,
    status: item.status,
    watch_reason: item.watch_reason,
    risk_level: item.risk_level,
    target_position: item.target_position,
    tags: item.tags,
    note: item.note,
  };
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function removeWatchItem(item: FundWatchlistItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除 ${item.fund_name}（${item.fund_code}）这条观察项？`,
      '确认删除观察项',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
  } catch {
    return;
  }

  deletingWatchId.value = item.id;
  try {
    await deleteFundWatchlistItem(item.id);
    if (editingWatchId.value === item.id) {
      resetWatchForm();
    }
    ElMessage.success('观察项已删除');
    await loadWatchlist();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '观察项删除失败');
  } finally {
    deletingWatchId.value = null;
  }
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
    await Promise.all([loadHoldings(), loadWatchlist(), loadNavRecords()]);
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

.position-form,
.nav-form,
.watchlist-form {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.position-form label,
.nav-form label,
.watchlist-form label {
  display: grid;
  gap: 7px;
}

.position-form label span,
.nav-form label span,
.watchlist-form label span {
  color: var(--color-muted);
  font-size: 12px;
}

.position-form .wide,
.nav-form .wide,
.watchlist-form .wide {
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

.watchlist-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 16px;
}

.watch-card {
  background: rgba(15, 23, 42, 0.32);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 13px;
}

.watch-card-head,
.watch-meta {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.watch-card strong {
  color: var(--color-text);
  display: block;
  font-size: 14px;
}

.watch-card small,
.watch-note {
  color: var(--color-muted);
  font-size: 12px;
}

.watch-card p {
  color: var(--color-text);
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}

.watch-meta {
  justify-content: flex-start;
}

.watch-meta span,
.priority-pill {
  border: 1px solid rgba(56, 189, 248, 0.26);
  border-radius: 999px;
  color: #7dd3fc;
  font-size: 12px;
  padding: 4px 8px;
}

.position-table {
  display: grid;
  gap: 8px;
}

.nav-table {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.nav-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  grid-template-columns: 1.4fr 0.8fr repeat(3, 0.75fr) 0.7fr;
  padding: 11px 12px;
}

.nav-row span {
  color: var(--color-muted);
  font-size: 13px;
}

.nav-row strong {
  color: var(--color-text);
  display: block;
}

.nav-row small {
  display: block;
  font-size: 12px;
  margin-top: 4px;
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
  align-items: center;
  background: rgba(15, 23, 42, 0.32);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  display: flex;
  gap: 14px;
  justify-content: space-between;
  padding: 14px;
}

.roadmap-item strong {
  color: var(--color-text);
  font-size: 14px;
}

.roadmap-item p,
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

@media (max-width: 920px) {
  .position-form,
  .nav-form,
  .watchlist-form,
  .watchlist-grid {
    grid-template-columns: 1fr;
  }

  .position-form .wide,
  .nav-form .wide,
  .watchlist-form .wide {
    grid-column: auto;
  }
}

@media (max-width: 720px) {
  .nav-row,
  .position-row {
    grid-template-columns: 1fr;
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
