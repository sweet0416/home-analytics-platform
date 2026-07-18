<template>
  <div>
    <section class="page-header backtest-header">
      <div>
        <h1 class="page-title">组合回测</h1>
        <div class="page-subtitle">把一组 5+2 放回历史开奖里验证命中表现</div>
      </div>
      <div class="backtest-actions">
        <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
        <el-checkbox v-model="form.addon">按追加成本计算</el-checkbox>
        <el-input-number v-model="form.hitLimit" :min="1" :max="100" size="small" />
        <el-button plain :disabled="!canAddCurrentSet" @click="addCurrentToPool">加入回测池</el-button>
        <el-button type="primary" :loading="analyzing" @click="handleBacktest">开始回测</el-button>
      </div>
    </section>

    <DisclaimerAlert :text="lottery.backtest?.disclaimer ?? fallbackDisclaimer" />

    <el-alert
      v-if="errorMessage"
      class="backtest-alert"
      type="warning"
      :title="errorMessage"
      :closable="false"
      show-icon
    />

    <section class="panel input-panel">
      <div class="panel-header">
        <h2 class="panel-title">回测输入</h2>
        <span class="panel-meta">点击号码球选择一组 5+2，选满后再点其他号码会先提示</span>
      </div>
      <div class="picker-grid">
        <div class="number-picker">
          <div class="picker-header">
            <div>
              <h3>前区号码</h3>
              <span>必须选择 5 个，范围 01-35</span>
            </div>
            <el-button plain size="small" @click="clearNumbers('front')">清空前区</el-button>
          </div>
          <LotteryNumberBoard
            area="front"
            :numbers="frontOptions"
            :columns="7"
            :tablet-columns="7"
            :mobile-columns="6"
            :classes-for-number="frontNumberClasses"
            @toggle="toggleNumber('front', $event)"
          />
          <div class="selected-line">
            <span>已选 {{ form.frontNumbers.length }}/5</span>
            <div class="ball-row">
              <LotteryBall
                v-for="number in form.frontNumbers"
                :key="`selected-front-${number}`"
                area="front"
                :value="number"
              />
            </div>
          </div>
        </div>

        <div class="number-picker">
          <div class="picker-header">
            <div>
              <h3>后区号码</h3>
              <span>必须选择 2 个，范围 01-12</span>
            </div>
            <el-button plain size="small" @click="clearNumbers('back')">清空后区</el-button>
          </div>
          <LotteryNumberBoard
            area="back"
            :numbers="backOptions"
            :columns="6"
            :tablet-columns="6"
            :mobile-columns="6"
            :classes-for-number="backNumberClasses"
            @toggle="toggleNumber('back', $event)"
          />
          <div class="selected-line">
            <span>已选 {{ form.backNumbers.length }}/2</span>
            <div class="ball-row">
              <LotteryBall
                v-for="number in form.backNumbers"
                :key="`selected-back-${number}`"
                area="back"
                :value="number"
              />
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="panel pool-panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">回测池</h2>
          <span class="panel-meta">可放入多组 5+2 号码，批量比较历史表现</span>
        </div>
        <div class="pool-actions">
          <el-button plain size="small" :disabled="!backtestPool.length" @click="clearBacktestPool">
            清空
          </el-button>
          <el-button
            type="primary"
            size="small"
            :loading="batchAnalyzing"
            :disabled="!backtestPool.length"
            @click="handleBatchBacktest"
          >
            批量回测
          </el-button>
        </div>
      </div>
      <div v-if="backtestPool.length" class="pool-list">
        <article v-for="item in backtestPool" :key="item.id" class="pool-row">
          <div>
            <el-input
              v-model="item.label"
              class="pool-label-input"
              maxlength="24"
              size="small"
              @change="normalizePoolLabel(item)"
            />
            <span>{{ item.source }}</span>
          </div>
          <div class="pool-balls">
            <LotteryBall
              v-for="number in item.frontNumbers"
              :key="`${item.id}-front-${number}`"
              area="front"
              :value="number"
            />
            <LotteryBall
              v-for="number in item.backNumbers"
              :key="`${item.id}-back-${number}`"
              area="back"
              :value="number"
            />
          </div>
          <el-button plain size="small" @click="removePoolItem(item.id)">移除</el-button>
        </article>
      </div>
      <EmptyState
        v-else
        title="回测池为空"
        description="选好一组号码后点击加入回测池，或从推荐页跳转后先加入池子。"
      />
    </section>

    <section v-if="batchResults.length" class="panel batch-panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">批量回测结果</h2>
          <span class="panel-meta">{{ batchSummary }}</span>
        </div>
        <el-button plain size="small" @click="exportBatchResultsCsv">导出 CSV</el-button>
      </div>
      <div class="batch-table">
        <div class="batch-row batch-head">
          <span>组合</span>
          <span>号码</span>
          <span>中奖期数</span>
          <span>最高命中</span>
          <span>固定奖净值</span>
        </div>
        <template v-for="item in batchResults" :key="item.id">
          <div class="batch-row">
            <span>{{ item.label }}</span>
            <span>{{ formatPoolNumbers(item) }}</span>
            <span>{{ item.analysis.hit_count }} / {{ item.analysis.sample_size }}</span>
            <span>{{ item.analysis.highest_hit?.match_key ?? '--' }}</span>
            <div class="batch-result-actions">
              <strong>{{ formatCurrency(item.analysis.net_fixed_result) }}</strong>
              <el-button link size="small" @click="toggleBatchDetails(item.id)">
                {{ isBatchDetailsExpanded(item.id) ? '收起明细' : '查看明细' }}
              </el-button>
            </div>
          </div>
          <div v-if="isBatchDetailsExpanded(item.id)" class="batch-details">
            <div class="batch-details-summary">
              <span>展示 {{ item.analysis.hits.length }} 条命中记录</span>
              <span>最高命中 {{ item.analysis.highest_hit?.match_key ?? '--' }}</span>
              <span>最近命中 {{ item.analysis.latest_hit?.issue_no ?? '--' }}</span>
            </div>
            <div v-if="item.analysis.hits.length" class="batch-hit-list">
              <article v-for="hit in item.analysis.hits" :key="`${item.id}-${hit.issue_no}`" class="batch-hit-card">
                <div class="batch-hit-main">
                  <strong>{{ hit.issue_no }}</strong>
                  <span>{{ hit.draw_date }}</span>
                  <el-tag effect="dark" size="small" :type="hit.prize_tier <= 3 ? 'success' : 'info'">
                    {{ hit.tier_name }} / {{ hit.match_key }}
                  </el-tag>
                </div>
                <div class="batch-hit-balls">
                  <span>前区命中 {{ formatNumberList(hit.front_matches) }}</span>
                  <span>后区命中 {{ formatNumberList(hit.back_matches) }}</span>
                  <span>{{ hit.is_floating ? '浮动奖' : `固定奖 ${formatCurrency(hit.base_prize_amount ?? 0)}` }}</span>
                </div>
              </article>
            </div>
            <EmptyState
              v-else
              title="暂无命中明细"
              description="这组号码在当前历史样本里没有命中过官方奖级。"
            />
          </div>
        </template>
      </div>
    </section>

    <div class="grid metrics backtest-metrics">
      <MetricCard label="历史样本" :value="sampleSize" :meta="sampleRange" />
      <MetricCard label="中奖期数" :value="hitCount" :meta="hitRate" />
      <MetricCard label="最高命中" :value="highestHitLabel" :meta="highestHitMeta" />
      <MetricCard label="固定奖净值" :value="netFixedResult" meta="不含浮动奖估算" />
    </div>

    <section v-if="lottery.backtest" class="panel selected-panel">
      <div class="panel-header">
        <h2 class="panel-title">快速汇总</h2>
        <span class="panel-meta">{{ costSummary }}</span>
      </div>
      <div class="selected-content">
        <div class="selected-balls">
          <span class="number-label">前区</span>
          <LotteryBall
            v-for="number in lottery.backtest.front_numbers"
            :key="`front-${number}`"
            area="front"
            :value="number"
          />
          <span class="number-label back-label">后区</span>
          <LotteryBall
            v-for="number in lottery.backtest.back_numbers"
            :key="`back-${number}`"
            area="back"
            :value="number"
          />
        </div>
        <div class="cost-grid">
          <div>
            <span>普通成本</span>
            <strong>{{ formatCurrency(lottery.backtest.base_cost) }}</strong>
          </div>
          <div>
            <span>追加成本</span>
            <strong>{{ formatCurrency(lottery.backtest.addon_cost) }}</strong>
          </div>
          <div>
            <span>固定奖回报</span>
            <strong>{{ formatCurrency(lottery.backtest.fixed_prize_return) }}</strong>
          </div>
          <div>
            <span>浮动奖命中</span>
            <strong>{{ lottery.backtest.floating_hit_count }} 次</strong>
          </div>
        </div>
      </div>
    </section>

    <section v-if="lottery.backtest" class="panel hit-panel">
      <div class="panel-header">
        <h2 class="panel-title">命中明细</h2>
        <span class="panel-meta">最多展示 {{ lottery.backtest.hit_preview_limit }} 条，按奖级优先排序</span>
      </div>
      <div v-if="lottery.backtest.hits.length" class="hit-list">
        <article v-for="hit in lottery.backtest.hits" :key="hit.issue_no" class="hit-card">
          <div class="hit-topline">
            <div>
              <strong>{{ hit.issue_no }}</strong>
              <span>{{ hit.draw_date }}</span>
            </div>
            <el-tag effect="dark" :type="hit.prize_tier <= 3 ? 'success' : 'info'">
              {{ hit.tier_name }} / {{ hit.match_key }}
            </el-tag>
          </div>
          <div class="hit-balls">
            <span class="number-label">开奖前区</span>
            <LotteryBall
              v-for="number in hit.draw_front_numbers"
              :key="`${hit.issue_no}-front-${number}`"
              area="front"
              :value="number"
            />
            <span class="number-label back-label">开奖后区</span>
            <LotteryBall
              v-for="number in hit.draw_back_numbers"
              :key="`${hit.issue_no}-back-${number}`"
              area="back"
              :value="number"
            />
          </div>
          <div class="hit-meta">
            <span>前区命中 {{ formatNumberList(hit.front_matches) }}</span>
            <span>后区命中 {{ formatNumberList(hit.back_matches) }}</span>
            <span>
              {{ hit.is_floating ? '浮动奖，未估算金额' : `固定奖 ${formatCurrency(hit.base_prize_amount ?? 0)}` }}
            </span>
          </div>
        </article>
      </div>
      <EmptyState
        v-else
        title="历史未命中奖级"
        description="这组号码在当前历史库中没有命中过官方奖级。"
      />
    </section>

    <section v-if="lottery.backtest" class="panel distribution-panel">
      <div class="panel-header">
        <h2 class="panel-title">命中分布</h2>
        <span class="panel-meta">每一种前区+后区命中结构出现过多少次</span>
      </div>
      <div class="distribution-grid">
        <div
          v-for="item in visibleDistribution"
          :key="item.match_key"
          class="distribution-item"
        >
          <strong>{{ item.match_key }}</strong>
          <span>{{ item.count }} 期</span>
          <small>{{ item.tier_name }}</small>
        </div>
      </div>
    </section>

    <section v-if="lottery.backtest" class="panel explain-panel">
      <div class="panel-header">
        <h2 class="panel-title">回测说明</h2>
        <span class="panel-meta">通俗解释</span>
      </div>
      <div class="methodology-list">
        <div v-for="item in lottery.backtest.methodology" :key="item" class="methodology-item">
          {{ item }}
        </div>
      </div>
    </section>

    <EmptyState
      v-if="!lottery.backtest"
      class="backtest-empty"
      title="输入一组号码开始回测"
      description="回测只说明这组号码在历史上表现如何，不代表未来更容易开奖。"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import LotteryNumberBoard from '@/plugins/lottery/components/LotteryNumberBoard.vue';
import {
  backtestNumbers as backtestNumbersRequest,
  type LotteryBacktestAnalysis,
} from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

interface BacktestPoolItem {
  id: string;
  label: string;
  source: string;
  frontNumbers: number[];
  backNumbers: number[];
}

interface BatchBacktestResult extends BacktestPoolItem {
  analysis: LotteryBacktestAnalysis;
}

interface StoredBacktestPool {
  addon?: boolean;
  hitLimit?: number;
  pool?: unknown[];
}

const BACKTEST_STORAGE_KEY = 'hap:lottery:dlt:backtest-pool:v1';
const lottery = useLotteryStore();
const route = useRoute();
const analyzing = ref(false);
const batchAnalyzing = ref(false);
const errorMessage = ref('');
const fallbackDisclaimer = '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。';

const form = reactive({
  frontNumbers: [] as number[],
  backNumbers: [] as number[],
  addon: false,
  hitLimit: 20,
});

const backtestPool = ref<BacktestPoolItem[]>([]);
const batchResults = ref<BatchBacktestResult[]>([]);
const expandedBatchResultIds = ref<Set<string>>(new Set());
const frontOptions = Array.from({ length: 35 }, (_, index) => index + 1);
const backOptions = Array.from({ length: 12 }, (_, index) => index + 1);
const canAddCurrentSet = computed(
  () => form.frontNumbers.length === 5 && form.backNumbers.length === 2,
);
const sampleSize = computed(() => String(lottery.backtest?.sample_size ?? 0));
const sampleRange = computed(() => {
  const result = lottery.backtest;
  if (!result) return '等待回测';
  return `${result.earliest_issue_no} - ${result.latest_issue_no}`;
});
const hitCount = computed(() => String(lottery.backtest?.hit_count ?? 0));
const hitRate = computed(() => {
  const result = lottery.backtest;
  if (!result?.sample_size) return '中奖期数 / 历史样本';
  return `${((result.hit_count / result.sample_size) * 100).toFixed(2)}%`;
});
const highestHitLabel = computed(() => lottery.backtest?.highest_hit?.match_key ?? '--');
const highestHitMeta = computed(() => lottery.backtest?.highest_hit?.tier_name ?? '暂无命中奖级');
const netFixedResult = computed(() => formatCurrency(lottery.backtest?.net_fixed_result ?? 0));
const costSummary = computed(() => {
  const result = lottery.backtest;
  if (!result) return '--';
  return `总成本 ${formatCurrency(result.total_cost)} / 固定奖回报 ${formatCurrency(result.fixed_prize_return)}`;
});
const visibleDistribution = computed(
  () => lottery.backtest?.distribution.filter((item) => item.count > 0).slice(0, 12) ?? [],
);
const batchSummary = computed(() => {
  if (!batchResults.value.length) return '--';
  const best = [...batchResults.value].sort(
    (left, right) => right.analysis.net_fixed_result - left.analysis.net_fixed_result,
  )[0];
  return `共 ${batchResults.value.length} 组，净值最高：${best.label} ${formatCurrency(best.analysis.net_fixed_result)}`;
});

async function handleBacktest(): Promise<void> {
  errorMessage.value = '';
  if (form.frontNumbers.length !== 5 || form.backNumbers.length !== 2) {
    errorMessage.value = '请先选择 5 个前区号码和 2 个后区号码。';
    return;
  }

  analyzing.value = true;
  try {
    await lottery.backtestNumbers({
      front_numbers: [...form.frontNumbers],
      back_numbers: [...form.backNumbers],
      addon: form.addon,
      hit_limit: form.hitLimit,
    });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '组合回测失败';
  } finally {
    analyzing.value = false;
  }
}

async function handleBatchBacktest(): Promise<void> {
  errorMessage.value = '';
  if (!backtestPool.value.length) {
    errorMessage.value = '请先加入至少一组号码到回测池。';
    return;
  }

  batchAnalyzing.value = true;
  try {
    const results: BatchBacktestResult[] = [];
    for (const item of backtestPool.value) {
      const analysis = await backtestNumbersRequest({
        front_numbers: [...item.frontNumbers],
        back_numbers: [...item.backNumbers],
        addon: form.addon,
        hit_limit: form.hitLimit,
      });
      results.push({ ...item, analysis });
    }
    batchResults.value = results;
    expandedBatchResultIds.value = new Set(results.slice(0, 1).map((item) => item.id));
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '批量回测失败';
  } finally {
    batchAnalyzing.value = false;
  }
}

function addCurrentToPool(): void {
  errorMessage.value = '';
  if (!canAddCurrentSet.value) {
    errorMessage.value = '请先选择 5 个前区号码和 2 个后区号码。';
    return;
  }
  const signature = buildPoolSignature(form.frontNumbers, form.backNumbers);
  if (
    backtestPool.value.some((item) =>
      buildPoolSignature(item.frontNumbers, item.backNumbers) === signature,
    )
  ) {
    errorMessage.value = '这组号码已经在回测池里。';
    return;
  }
  backtestPool.value.push({
    id: `${Date.now()}-${backtestPool.value.length + 1}`,
    label: `组合 ${backtestPool.value.length + 1}`,
    source: route.query.front || route.query.back ? '来自链接或当前选择' : '手动选择',
    frontNumbers: [...form.frontNumbers],
    backNumbers: [...form.backNumbers],
  });
}

function removePoolItem(id: string): void {
  backtestPool.value = backtestPool.value.filter((item) => item.id !== id);
  batchResults.value = batchResults.value.filter((item) => item.id !== id);
}

function normalizePoolLabel(item: BacktestPoolItem): void {
  const fallbackIndex = backtestPool.value.findIndex((poolItem) => poolItem.id === item.id) + 1;
  const fallbackLabel = `组合 ${fallbackIndex || backtestPool.value.length || 1}`;
  item.label = item.label.trim() || fallbackLabel;
}

function clearBacktestPool(): void {
  backtestPool.value = [];
  batchResults.value = [];
  expandedBatchResultIds.value = new Set();
  errorMessage.value = '';
  localStorage.removeItem(BACKTEST_STORAGE_KEY);
}

function toggleBatchDetails(id: string): void {
  const next = new Set(expandedBatchResultIds.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  expandedBatchResultIds.value = next;
}

function isBatchDetailsExpanded(id: string): boolean {
  return expandedBatchResultIds.value.has(id);
}

function exportBatchResultsCsv(): void {
  if (!batchResults.value.length) {
    errorMessage.value = '请先完成批量回测后再导出。';
    return;
  }

  const rows: Array<Array<number | string | null | undefined>> = [
    ['Home Analytics Platform', '大乐透组合回测'],
    ['导出时间', new Date().toLocaleString('zh-CN')],
    ['追加计算', form.addon ? '是' : '否'],
    ['命中明细上限', form.hitLimit],
    [],
    ['汇总'],
    ['组合', '号码', '中奖期数', '历史样本', '最高命中', '固定奖净值'],
  ];

  for (const item of batchResults.value) {
    rows.push([
      item.label,
      formatPoolNumbers(item),
      item.analysis.hit_count,
      item.analysis.sample_size,
      item.analysis.highest_hit?.match_key ?? '--',
      item.analysis.net_fixed_result,
    ]);
  }

  rows.push(
    [],
    ['命中明细'],
    ['组合', '期号', '开奖日期', '奖级', '命中结构', '前区命中', '后区命中', '固定奖金额'],
  );

  for (const item of batchResults.value) {
    if (!item.analysis.hits.length) {
      rows.push([item.label, '--', '--', '未命中奖级', '--', '--', '--', 0]);
      continue;
    }
    for (const hit of item.analysis.hits) {
      rows.push([
        item.label,
        hit.issue_no,
        hit.draw_date,
        hit.tier_name,
        hit.match_key,
        formatNumberList(hit.front_matches),
        formatNumberList(hit.back_matches),
        hit.is_floating ? '浮动奖未估算' : (hit.base_prize_amount ?? 0),
      ]);
    }
  }

  downloadTextFile(
    `hap-dlt-backtest-${new Date().toISOString().slice(0, 10)}.csv`,
    `\uFEFF${rows.map(formatCsvRow).join('\n')}`,
  );
}

function toggleNumber(area: 'front' | 'back', number: number): void {
  errorMessage.value = '';
  const current = area === 'front' ? form.frontNumbers : form.backNumbers;
  if (current.includes(number)) {
    setNumbers(
      area,
      current.filter((item) => item !== number),
    );
    return;
  }

  const limit = area === 'front' ? 5 : 2;
  if (current.length >= limit) {
    errorMessage.value = area === 'front' ? '前区最多选择 5 个号码。' : '后区最多选择 2 个号码。';
    return;
  }

  setNumbers(area, [...current, number].sort((left, right) => left - right));
}

function clearNumbers(area: 'front' | 'back'): void {
  setNumbers(area, []);
  errorMessage.value = '';
}

function setNumbers(area: 'front' | 'back', numbers: number[]): void {
  if (area === 'front') {
    form.frontNumbers = numbers;
  } else {
    form.backNumbers = numbers;
  }
}

function frontNumberClasses(number: number): string[] {
  return form.frontNumbers.includes(number) ? ['selected', 'front-selected'] : [];
}

function backNumberClasses(number: number): string[] {
  return form.backNumbers.includes(number) ? ['selected', 'back-selected'] : [];
}

function hydrateNumbersFromQuery(): void {
  const frontNumbers = parseQueryNumbers(route.query.front, 1, 35, 5);
  const backNumbers = parseQueryNumbers(route.query.back, 1, 12, 2);
  if (frontNumbers.length) {
    setNumbers('front', frontNumbers);
  }
  if (backNumbers.length) {
    setNumbers('back', backNumbers);
  }
  if (frontNumbers.length === 5 && backNumbers.length === 2) {
    const signature = buildPoolSignature(frontNumbers, backNumbers);
    if (!backtestPool.value.some((item) => buildPoolSignature(item.frontNumbers, item.backNumbers) === signature)) {
      addCurrentToPool();
    }
  }
}

function hydrateBacktestPreferences(): void {
  try {
    const raw = localStorage.getItem(BACKTEST_STORAGE_KEY);
    if (!raw) return;

    const parsed = JSON.parse(raw) as StoredBacktestPool;
    if (typeof parsed.addon === 'boolean') {
      form.addon = parsed.addon;
    }
    if (typeof parsed.hitLimit === 'number' && parsed.hitLimit >= 1 && parsed.hitLimit <= 100) {
      form.hitLimit = parsed.hitLimit;
    }
    if (Array.isArray(parsed.pool)) {
      const nextPool = parsed.pool
        .map(normalizeStoredPoolItem)
        .filter((item): item is BacktestPoolItem => item !== null);
      backtestPool.value = dedupeBacktestPool(nextPool);
    }
  } catch {
    localStorage.removeItem(BACKTEST_STORAGE_KEY);
  }
}

function persistBacktestPreferences(): void {
  if (!backtestPool.value.length) {
    localStorage.removeItem(BACKTEST_STORAGE_KEY);
    return;
  }

  const payload: StoredBacktestPool = {
    addon: form.addon,
    hitLimit: form.hitLimit,
    pool: backtestPool.value,
  };
  localStorage.setItem(BACKTEST_STORAGE_KEY, JSON.stringify(payload));
}

function normalizeStoredPoolItem(value: unknown, index: number): BacktestPoolItem | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Record<string, unknown>;
  const frontNumbers = parseQueryNumbers(item.frontNumbers, 1, 35, 5);
  const backNumbers = parseQueryNumbers(item.backNumbers, 1, 12, 2);
  if (frontNumbers.length !== 5 || backNumbers.length !== 2) return null;
  return {
    id: typeof item.id === 'string' && item.id ? item.id : `stored-${index + 1}`,
    label: typeof item.label === 'string' && item.label ? item.label : `组合 ${index + 1}`,
    source: typeof item.source === 'string' && item.source ? item.source : '本地保存',
    frontNumbers,
    backNumbers,
  };
}

function dedupeBacktestPool(items: BacktestPoolItem[]): BacktestPoolItem[] {
  const seen = new Set<string>();
  const uniqueItems: BacktestPoolItem[] = [];
  for (const item of items) {
    const signature = buildPoolSignature(item.frontNumbers, item.backNumbers);
    if (seen.has(signature)) continue;
    seen.add(signature);
    uniqueItems.push(item);
  }
  return uniqueItems;
}

function parseQueryNumbers(
  value: unknown,
  min: number,
  max: number,
  limit: number,
): number[] {
  const raw = Array.isArray(value) ? value.join(',') : String(value ?? '');
  return Array.from(
    new Set(
      raw
        .split(/[\s,，、]+/)
        .map((item) => Number.parseInt(item, 10))
        .filter((item) => Number.isFinite(item) && item >= min && item <= max),
    ),
  )
    .sort((left, right) => left - right)
    .slice(0, limit);
}

function formatCurrency(value: number): string {
  return `¥${value.toLocaleString('zh-CN')}`;
}

function formatCsvRow(row: Array<number | string | null | undefined>): string {
  return row.map(escapeCsvCell).join(',');
}

function escapeCsvCell(value: number | string | null | undefined): string {
  const raw = value == null ? '' : String(value);
  const safeValue = /^[=+\-@]/.test(raw) ? `'${raw}` : raw;
  return `"${safeValue.replaceAll('"', '""')}"`;
}

function downloadTextFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function formatPoolNumbers(item: BacktestPoolItem): string {
  return `${formatNumberList(item.frontNumbers)} + ${formatNumberList(item.backNumbers)}`;
}

function buildPoolSignature(frontNumbers: number[], backNumbers: number[]): string {
  return `${frontNumbers.join(',')}|${backNumbers.join(',')}`;
}

function formatNumberList(numbers: number[]): string {
  return numbers.length ? numbers.map((number) => String(number).padStart(2, '0')).join(' ') : '无';
}

watch(
  [backtestPool, () => form.addon, () => form.hitLimit],
  persistBacktestPreferences,
  { deep: true },
);

onMounted(() => {
  hydrateBacktestPreferences();
  hydrateNumbersFromQuery();
});
</script>

<style scoped>
.backtest-header {
  align-items: center;
}

.backtest-actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.back-link,
.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.backtest-alert,
.input-panel,
.pool-panel,
.batch-panel,
.backtest-metrics,
.selected-panel,
.hit-panel,
.distribution-panel,
.explain-panel,
.backtest-empty {
  margin-top: 16px;
}

.pool-actions,
.pool-balls {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pool-list {
  display: grid;
  gap: 10px;
}

.pool-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  grid-template-columns: 120px minmax(0, 1fr) auto;
  padding: 12px;
}

.pool-row > div:first-child {
  display: grid;
  gap: 4px;
}

.pool-label-input {
  max-width: 160px;
}

.pool-label-input :deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.36);
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.12) inset;
}

.pool-label-input :deep(.el-input__inner) {
  color: var(--color-text);
  font-weight: 700;
}

.pool-row span,
.batch-row span {
  color: var(--color-muted);
  font-size: 12px;
}

.batch-table {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  overflow: hidden;
}

.batch-row {
  align-items: center;
  display: grid;
  gap: 10px;
  grid-template-columns: 110px minmax(220px, 1fr) 110px 90px 110px;
  padding: 12px;
}

.batch-row + .batch-row {
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.batch-head {
  background: rgba(15, 23, 42, 0.52);
  font-weight: 700;
}

.batch-result-actions,
.batch-details-summary,
.batch-hit-main,
.batch-hit-balls {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.batch-result-actions {
  justify-content: space-between;
}

.batch-details {
  background: rgba(15, 23, 42, 0.28);
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 12px;
  padding: 12px;
}

.batch-details-summary,
.batch-hit-balls {
  color: var(--color-muted);
  font-size: 12px;
}

.batch-hit-list {
  display: grid;
  gap: 8px;
}

.batch-hit-card {
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  display: grid;
  gap: 8px;
  padding: 10px;
}

.batch-hit-main span {
  color: var(--color-muted);
  font-size: 12px;
}

.picker-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.number-picker {
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  padding: 12px;
}

.picker-header {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.picker-header h3 {
  font-size: 15px;
  margin: 0 0 4px;
}

.picker-header span,
.selected-line > span,
.hit-meta,
.methodology-item,
.distribution-item small {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.selected-line {
  display: grid;
  gap: 8px;
}

.selected-content,
.cost-grid,
.hit-list,
.methodology-list {
  display: grid;
  gap: 12px;
}

.selected-balls,
.ball-row,
.hit-balls,
.hit-topline,
.hit-meta {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hit-topline {
  justify-content: space-between;
}

.hit-topline div {
  display: grid;
  gap: 4px;
}

.hit-topline span {
  color: var(--color-muted);
  font-size: 13px;
}

.number-label {
  color: var(--color-muted);
  font-size: 12px;
}

.back-label {
  margin-left: 6px;
}

.cost-grid,
.distribution-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.cost-grid div,
.distribution-item,
.hit-card,
.methodology-item {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.cost-grid span,
.distribution-item span {
  color: var(--color-muted);
  display: block;
  font-size: 12px;
  margin-bottom: 6px;
}

.cost-grid strong,
.distribution-item strong {
  font-size: 18px;
}

.hit-card {
  display: grid;
  gap: 12px;
}

@media (max-width: 920px) {
  .backtest-header,
  .backtest-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .picker-grid,
  .pool-row,
  .batch-row,
  .cost-grid,
  .distribution-grid {
    grid-template-columns: 1fr;
  }

  .picker-header {
    align-items: stretch;
    flex-direction: column;
  }
}

</style>
