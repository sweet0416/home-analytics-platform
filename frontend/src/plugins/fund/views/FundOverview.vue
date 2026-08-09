<template>
  <div>
    <RevealContent as="section" class="page-header" :delay="20">
      <div>
        <h1 class="page-title">Fund</h1>
        <div class="page-subtitle">ETF、QDII、资产配置和收益分析模块</div>
      </div>
    </RevealContent>

    <div class="grid metrics">
      <MetricCard label="观察基金" :value="watchCountText" meta="关注池记录" :delay="80" />
      <MetricCard label="高优先级" :value="highPriorityCountText" meta="优先级 1-2" :delay="120" />
      <MetricCard label="净值记录" :value="navRecordCountText" :meta="latestNavMeta" :delay="160" />
      <MetricCard label="持仓数量" :value="positionCountText" meta="已录入记录" :delay="200" />
      <MetricCard label="浮盈亏" :value="formatMoney(summary?.unrealized_profit)" :meta="returnRateMeta" :delay="240" />
      <MetricCard label="自动净值" :value="schedulerStatusText" :meta="schedulerNextRunMeta" :delay="250" />
    </div>

    <RevealContent
      v-if="isLoading || errorMessage"
      as="section"
      class="overview-load-state"
      :delay="252"
    >
      <span>{{ isLoading ? '正在读取基金数据...' : errorMessage }}</span>
      <el-button
        v-if="errorMessage"
        :icon="Refresh"
        plain
        size="small"
        @click="loadOverview"
      >
        重新加载
      </el-button>
    </RevealContent>

    <RevealContent
      v-if="navSchedulerStatus?.last_run"
      as="section"
      class="auto-sync-status"
      :delay="255"
    >
      <strong>{{ lastSyncStatusText }}</strong>
      <span>{{ lastSyncDetail }}</span>
    </RevealContent>

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

    <FundTradeSyncPanel @imported="handleTransactionChanged" />
    <FundTransactions @changed="handleTransactionChanged" />

    <RevealContent as="section" class="panel fund-panel" :delay="300">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">录入持仓</h2>
          <span class="panel-meta">先记录你的真实持仓，行情和净值后续再接入</span>
        </div>
      </div>
      <div class="panel-body">
        <div class="position-export-actions">
          <el-button :icon="Download" @click="downloadPositions">
            导出持仓 CSV
          </el-button>
        </div>
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
            <span>目标占比（%）</span>
            <el-input-number
              v-model="targetWeightPercent"
              :min="0"
              :max="100"
              :precision="2"
              :step="5"
            />
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
        <div v-if="positions.length" class="position-sort">
          <el-select v-model="positionSortField" aria-label="持仓排序字段">
            <el-option
              v-for="option in positionSortOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-button
            :icon="positionSortDirection === 'desc' ? SortDown : SortUp"
            :title="positionSortDirection === 'desc' ? '当前为降序' : '当前为升序'"
            aria-label="切换持仓排序方向"
            @click="togglePositionSortDirection"
          />
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
            <span>目标占比</span>
            <span>浮盈亏</span>
            <span>操作</span>
          </div>
          <div v-for="position in sortedPositions" :key="position.id" class="position-row">
            <span>
              <strong>{{ position.fund_name }}</strong>
              <small>{{ position.fund_code }} · {{ position.account_name }}</small>
            </span>
            <span>{{ position.fund_type }}</span>
            <span>{{ formatNumber(position.shares, 4) }}</span>
            <span>{{ formatMoney(position.total_cost) }}</span>
            <span>{{ formatMoney(position.current_value) }}</span>
            <span>{{ formatPercent(position.target_weight) }}</span>
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

    <FundAccountHoldings />

    <FundNavFreshness
      :refresh-key="holdingRiskRefreshKey"
      @profiles-synced="loadOverview"
    />

    <FundCashFlowPerformance :refresh-key="cashFlowPerformanceRefreshKey" />

    <FundAllocation :refresh-key="allocationRefreshKey" />

    <FundLookthrough :refresh-key="allocationRefreshKey" />

    <FundPortfolioPerformance :refresh-key="holdingRiskRefreshKey" />

    <FundPortfolioBenchmark :refresh-key="holdingRiskRefreshKey" />

    <FundHoldingCorrelation :refresh-key="holdingRiskRefreshKey" />

    <FundRiskContribution :refresh-key="holdingRiskRefreshKey" />

    <FundHoldingRisk
      :refresh-key="holdingRiskRefreshKey"
      @synced="handleHistorySynced"
    />

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
import { Download, Refresh, SortDown, SortUp } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import FundAccountHoldings from '@/plugins/fund/components/FundAccountHoldings.vue';
import FundAllocation from '@/plugins/fund/components/FundAllocation.vue';
import FundCashFlowPerformance from '@/plugins/fund/components/FundCashFlowPerformance.vue';
import FundDailyReport from '@/plugins/fund/components/FundDailyReport.vue';
import FundHoldingRisk from '@/plugins/fund/components/FundHoldingRisk.vue';
import FundHoldingCorrelation from '@/plugins/fund/components/FundHoldingCorrelation.vue';
import FundLookthrough from '@/plugins/fund/components/FundLookthrough.vue';
import FundNavFreshness from '@/plugins/fund/components/FundNavFreshness.vue';
import FundNavTrend from '@/plugins/fund/components/FundNavTrend.vue';
import FundPortfolioBenchmark from '@/plugins/fund/components/FundPortfolioBenchmark.vue';
import FundPortfolioPerformance from '@/plugins/fund/components/FundPortfolioPerformance.vue';
import FundRiskContribution from '@/plugins/fund/components/FundRiskContribution.vue';
import FundTransactions from '@/plugins/fund/components/FundTransactions.vue';
import FundTradeSyncPanel from '@/plugins/fund/components/FundTradeSyncPanel.vue';
import {
  createFundNavRecord,
  createFundPosition,
  createFundWatchlistItem,
  deleteFundNavRecord,
  deleteFundPosition,
  deleteFundWatchlistItem,
  fetchFundHoldingSummary,
  fetchFundNavRecords,
  fetchFundNavSchedulerStatus,
  fetchFundNavSummary,
  fetchFundPositions,
  getFundPositionsExportUrl,
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
  type FundNavSchedulerStatus,
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
type PositionSortField =
  | 'current_value'
  | 'unrealized_profit'
  | 'unrealized_return_rate'
  | 'total_cost'
  | 'fund_code'
  | 'account_name';

const positionSortOptions: Array<{ label: string; value: PositionSortField }> = [
  { label: '按当前估值', value: 'current_value' },
  { label: '按浮盈亏', value: 'unrealized_profit' },
  { label: '按收益率', value: 'unrealized_return_rate' },
  { label: '按总成本', value: 'total_cost' },
  { label: '按基金代码', value: 'fund_code' },
  { label: '按账户名称', value: 'account_name' },
];

const fundStatus = ref<FundStatus | null>(null);
const positions = ref<FundPosition[]>([]);
const watchItems = ref<FundWatchlistItem[]>([]);
const navRecords = ref<FundNavRecord[]>([]);
const summary = ref<FundHoldingSummary | null>(null);
const watchSummary = ref<FundWatchlistSummary | null>(null);
const navSummary = ref<FundNavSummary | null>(null);
const navSchedulerStatus = ref<FundNavSchedulerStatus | null>(null);
const allocationRefreshKey = ref(0);
const cashFlowPerformanceRefreshKey = ref(0);
const dailyReportRefreshKey = ref(0);
const holdingRiskRefreshKey = ref(0);
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
const positionSortField = ref<PositionSortField>('current_value');
const positionSortDirection = ref<'asc' | 'desc'>('desc');
const targetWeightPercent = ref<number | null>(null);

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
  operational: '运行中',
  completed: '已完成',
  configured: '已配置',
  storage_ready: '就绪',
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

const watchCountText = computed(() => (
  watchSummary.value === null ? '--' : String(watchSummary.value.item_count)
));
const highPriorityCountText = computed(() => (
  watchSummary.value === null ? '--' : String(watchSummary.value.high_priority_count)
));
const navRecordCountText = computed(() => (
  navSummary.value === null ? '--' : String(navSummary.value.record_count)
));
const positionCountText = computed(() => (
  summary.value === null ? '--' : String(summary.value.position_count)
));

const returnRateMeta = computed(() => {
  if (summary.value === null) return isLoading.value ? '正在加载' : '暂不可用';
  if (summary.value.unrealized_return_rate === null) return '等待当前净值';
  return `${(Number(summary.value.unrealized_return_rate) * 100).toFixed(2)}%`;
});

const latestNavMeta = computed(() => {
  if (navSummary.value === null) return isLoading.value ? '正在加载' : '暂不可用';
  return navSummary.value.latest_nav_date ?? '等待净值';
});
const schedulerStatusText = computed(() => {
  if (navSchedulerStatus.value === null) return isLoading.value ? '检查中' : '暂不可用';
  if (!navSchedulerStatus.value.enabled) return '已关闭';
  return navSchedulerStatus.value.running ? '运行中' : '未运行';
});
const schedulerNextRunMeta = computed(() => {
  if (navSchedulerStatus.value === null) {
    return isLoading.value ? '正在读取任务状态' : '请重新加载';
  }
  const notification = navSchedulerStatus.value?.notification_enabled
    ? ` · ${notificationChannelLabel(navSchedulerStatus.value.notification_channel)} 推送`
    : '';
  const value = navSchedulerStatus.value?.next_run_at;
  if (!value) return `19:00-22:00 每小时检查${notification}`;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return `19:00-22:00 每小时检查${notification}`;
  return `下次 ${date.toLocaleString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    month: '2-digit',
    day: '2-digit',
    hour12: false,
  })}${notification}`;
});

function notificationChannelLabel(channel: FundNavSchedulerStatus['notification_channel']): string {
  if (channel === 'bark') return 'Bark';
  if (channel === 'wecom') return '企业微信';
  if (channel === 'whatsapp') return 'WhatsApp';
  if (channel === 'custom_webhook') return 'Webhook';
  return '全部通道';
}
const lastSyncStatusText = computed(() => {
  const run = navSchedulerStatus.value?.last_run;
  if (!run) return '尚无自动检查记录';
  if (run.skipped) return '最近检查：已跳过';
  if (run.status === 'failed') return '最近检查：失败';
  if (run.status === 'partial') return '最近检查：部分成功';
  return '最近检查：成功';
});
const lastSyncDetail = computed(() => {
  const run = navSchedulerStatus.value?.last_run;
  if (!run) return '';
  const finishedAt = new Date(run.finished_at);
  const time = Number.isNaN(finishedAt.getTime())
    ? run.finished_at
    : finishedAt.toLocaleString('zh-CN', { hour12: false });
  if (run.skipped) return `${time} · 当天已有新净值，不再重复请求`;
  return `${time} · 成功 ${run.succeeded}/${run.total} · 新增日期 ${run.updated} · 失败 ${run.failed}`;
});
const sortedPositions = computed(() => {
  const direction = positionSortDirection.value === 'asc' ? 1 : -1;
  return [...positions.value].sort((left, right) => {
    const leftValue = positionSortValue(left, positionSortField.value);
    const rightValue = positionSortValue(right, positionSortField.value);
    if (leftValue === null && rightValue === null) return left.id - right.id;
    if (leftValue === null) return 1;
    if (rightValue === null) return -1;
    if (typeof leftValue === 'string' && typeof rightValue === 'string') {
      const compared = leftValue.localeCompare(rightValue, 'zh-CN', {
        numeric: true,
        sensitivity: 'base',
      });
      return compared === 0 ? left.id - right.id : compared * direction;
    }
    const compared = Number(leftValue) - Number(rightValue);
    return compared === 0 ? left.id - right.id : compared * direction;
  });
});

function positionSortValue(
  position: FundPosition,
  field: PositionSortField,
): number | string | null {
  if (field === 'fund_code') return position.fund_code;
  if (field === 'account_name') return position.account_name;
  const value = position[field];
  if (value === null) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function togglePositionSortDirection(): void {
  positionSortDirection.value = positionSortDirection.value === 'desc' ? 'asc' : 'desc';
}

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

function formatPercent(value: string | number | null): string {
  if (value === null) return '--';
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return '--';
  return `${(numberValue * 100).toFixed(2)}%`;
}

function profitClass(value: string | null): string {
  const numberValue = Number(value ?? 0);
  if (numberValue > 0) return 'profit positive';
  if (numberValue < 0) return 'profit negative';
  return 'profit';
}

function resetForm(): void {
  editingPositionId.value = null;
  targetWeightPercent.value = null;
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
  holdingRiskRefreshKey.value += 1;
  cashFlowPerformanceRefreshKey.value += 1;
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
  cashFlowPerformanceRefreshKey.value += 1;
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
      target_weight:
        targetWeightPercent.value === null ? null : targetWeightPercent.value / 100,
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
  targetWeightPercent.value =
    position.target_weight === null ? null : Number(position.target_weight) * 100;
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

async function loadOverviewData(): Promise<void> {
  [fundStatus.value, navSchedulerStatus.value] = await Promise.all([
    fetchFundStatus(),
    fetchFundNavSchedulerStatus(),
  ]);
  await Promise.all([loadHoldings(), loadWatchlist(), loadNavRecords()]);
}

async function loadOverview(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    try {
      await loadOverviewData();
    } catch {
      await new Promise((resolve) => window.setTimeout(resolve, 800));
      await loadOverviewData();
    }
  } catch (loadError) {
    errorMessage.value = loadError instanceof Error ? loadError.message : '基金模块状态加载失败';
  } finally {
    isLoading.value = false;
  }
}

onMounted(loadOverview);

function downloadPositions(): void {
  window.location.href = getFundPositionsExportUrl();
}
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.auto-sync-status {
  align-items: center;
  border-block: 1px solid rgba(148, 163, 184, 0.14);
  display: flex;
  gap: 12px;
  margin-top: 12px;
  padding: 10px 2px;
}

.overview-load-state {
  align-items: center;
  border-block: 1px solid rgba(56, 189, 248, 0.2);
  color: var(--color-muted);
  display: flex;
  font-size: 13px;
  justify-content: space-between;
  margin-top: 12px;
  padding: 10px 2px;
}

.auto-sync-status strong {
  color: #34d399;
  font-size: 13px;
}

.auto-sync-status span {
  color: var(--color-muted);
  font-size: 12px;
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
  flex-wrap: wrap;
  grid-column: 1 / -1;
  gap: 10px;
  justify-content: flex-end;
  min-width: 0;
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

.position-sort {
  align-items: center;
  display: flex;
  gap: 8px;
}

.position-sort .el-select {
  width: 140px;
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
  grid-template-columns: 1.5fr 0.65fr repeat(5, 0.8fr) 0.95fr;
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
  .auto-sync-status {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .position-sort {
    align-items: stretch;
    width: 100%;
  }

  .position-sort .el-select {
    flex: 1;
    width: auto;
  }

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
