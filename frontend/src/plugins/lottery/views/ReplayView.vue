<template>
  <div>
    <section class="page-header replay-header">
      <div>
        <h1 class="page-title">历史回放</h1>
        <div class="page-subtitle">只使用目标期之前的数据，验证策略是否优于随机基准</div>
      </div>
      <div class="replay-actions">
        <el-button :loading="loadingContext" @click="loadContext">检查边界</el-button>
        <el-button type="primary" :loading="running" @click="handleRunReplay">运行回放</el-button>
      </div>
    </section>

    <DltModuleNav />

    <DisclaimerAlert :text="lottery.replayRun?.disclaimer ?? fallbackDisclaimer" />

    <section class="panel replay-panel">
      <div class="panel-header">
        <h2 class="panel-title">回放参数</h2>
        <span class="panel-meta">目标期本身不会进入训练样本</span>
      </div>
      <div class="replay-form">
        <label>
          目标期号
          <el-input v-model="form.targetIssueNo" placeholder="例如 26080" />
        </label>
        <label>
          生成组数
          <el-input-number v-model="form.sets" :min="1" :max="12" />
        </label>
        <label>
          样本窗口
          <el-input-number v-model="form.sampleLimit" :min="20" :max="2000" :step="50" />
        </label>
        <label>
          历史同期
          <el-input-number v-model="form.samePeriodCount" :min="1" :max="20" />
        </label>
        <label>
          随机基准
          <el-input-number
            v-model="form.baselineSimulations"
            :min="100"
            :max="50000"
            :step="1000"
          />
        </label>
        <label>
          Seed
          <el-input v-model="form.seedText" placeholder="留空为随机" />
        </label>
      </div>
      <div class="weight-grid">
        <div v-for="item in weightItems" :key="item.key" class="weight-item">
          <div>
            <strong>{{ item.label }}</strong>
            <span>{{ item.value }}</span>
          </div>
          <el-slider v-model="form.weights[item.key]" :min="0" :max="100" :step="5" />
        </div>
      </div>
    </section>

    <div class="grid metrics replay-metrics">
      <MetricCard label="训练样本" :value="sampleSize" :meta="sampleRange" />
      <MetricCard label="截止期号" :value="cutoffIssue" :meta="cutoffDate" />
      <MetricCard label="防泄漏检查" :value="leakageStatus" :meta="leakageRule" />
      <MetricCard label="随机基准" :value="baselineValue" :meta="baselineMeta" />
    </div>

    <section v-if="warnings.length" class="panel warning-panel">
      <div class="panel-header">
        <h2 class="panel-title">风险提示</h2>
        <span class="panel-meta">这些提示不阻止实验，但会影响解释强度</span>
      </div>
      <div class="warning-list">
        <el-alert
          v-for="warning in warnings"
          :key="warning.code"
          type="warning"
          :closable="false"
          :title="warning.code"
          :description="warning.message"
          show-icon
        />
      </div>
    </section>

    <section v-if="samePeriodDeviation" class="panel replay-panel deviation-panel">
      <div class="panel-header">
        <h2 class="panel-title">历史同期偏离度</h2>
        <span class="panel-meta">
          同尾 {{ samePeriodDeviation.issue_suffix }} · 样本 {{ samePeriodDeviation.sample_size }}
        </span>
      </div>
      <div class="deviation-grid">
        <article v-for="item in deviationMetricItems" :key="item.key" class="deviation-card">
          <div class="deviation-card-head">
            <strong>{{ item.label }}</strong>
            <span :class="['deviation-level', deviationLevelClass(item.metric.level)]">
              {{ deviationLevelLabel(item.metric.level) }}
            </span>
          </div>
          <div class="deviation-value">{{ formatSigned(item.metric.deviation) }}</div>
          <div class="deviation-meta">
            本期 {{ item.metric.target_value }} · 历史均值 {{ item.metric.historical_average }}
          </div>
        </article>
        <article v-for="item in deviationPatternItems" :key="item.key" class="deviation-card">
          <div class="deviation-card-head">
            <strong>{{ item.label }}</strong>
            <span :class="['deviation-level', deviationLevelClass(item.metric.level)]">
              {{ deviationLevelLabel(item.metric.level) }}
            </span>
          </div>
          <div class="deviation-value">{{ item.metric.target_pattern }}</div>
          <div class="deviation-meta">
            历史高频 {{ item.metric.historical_top_pattern }}
            · 本结构占比 {{ formatPercent(item.metric.target_pattern_rate) }}
          </div>
        </article>
      </div>
      <ul class="deviation-notes">
        <li v-for="note in samePeriodDeviation.notes" :key="note">{{ note }}</li>
      </ul>
    </section>

    <section v-if="lottery.replayRun" class="panel replay-panel">
      <div class="panel-header">
        <h2 class="panel-title">回放结果 #{{ lottery.replayRun.run_id }}</h2>
        <span class="panel-meta">
          目标 {{ lottery.replayRun.target_issue_no }} · 截止 {{ lottery.replayRun.cutoff_issue_no }}
        </span>
      </div>
      <div class="target-line">
        <span>实际开奖</span>
        <div class="ball-row">
          <LotteryBall
            v-for="number in lottery.replayRun.target_draw.front_numbers"
            :key="`target-front-${number}`"
            area="front"
            :value="number"
          />
          <LotteryBall
            v-for="number in lottery.replayRun.target_draw.back_numbers"
            :key="`target-back-${number}`"
            area="back"
            :value="number"
          />
        </div>
      </div>
      <div class="replay-list">
        <article v-for="item in lottery.replayRun.generated_sets" :key="item.rank" class="replay-card">
          <div class="card-head">
            <strong>第 {{ item.rank }} 组</strong>
            <el-tag :type="item.prize_tier ? 'success' : 'info'" effect="dark">
              {{ item.prize_tier ? `${item.prize_tier} 等` : '未命中奖级' }}
            </el-tag>
          </div>
          <div class="ball-row">
            <LotteryBall
              v-for="number in item.front_numbers"
              :key="`front-${item.rank}-${number}`"
              area="front"
              :value="number"
            />
            <LotteryBall
              v-for="number in item.back_numbers"
              :key="`back-${item.rank}-${number}`"
              area="back"
              :value="number"
            />
          </div>
          <div class="hit-grid">
            <span>命中 {{ item.match_key }}</span>
            <span>随机分位 {{ formatPercentile(item.baseline_percentile) }}</span>
            <span>评分 {{ item.score }}</span>
          </div>
          <ul>
            <li v-for="reason in item.rationale.slice(0, 4)" :key="reason">{{ reason }}</li>
          </ul>
        </article>
      </div>
    </section>

    <LotteryExplanationPanel
      title="这页怎么看"
      subtitle="回放是为了检查策略稳定性，不是预测下一期"
      :sections="explanationSections"
    />
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';

import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import DltModuleNav from '@/plugins/lottery/components/DltModuleNav.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import LotteryExplanationPanel, {
  type LotteryExplanationSection,
} from '@/plugins/lottery/components/LotteryExplanationPanel.vue';
import type {
  LotterySamePeriodDeviationMetric,
  LotterySamePeriodDeviationPattern,
} from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

type WeightKey = 'same_period_weight' | 'frequency_weight' | 'missing_weight' | 'structure_weight';

const lottery = useLotteryStore();
const loadingContext = ref(false);
const running = ref(false);
const fallbackDisclaimer = '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。';

const form = reactive({
  targetIssueNo: '',
  sets: 5,
  sampleLimit: 500,
  samePeriodCount: 10,
  baselineSimulations: 10000,
  seedText: '20260723',
  weights: {
    same_period_weight: 45,
    frequency_weight: 25,
    missing_weight: 20,
    structure_weight: 10,
  } as Record<WeightKey, number>,
});

const weightItems = computed<Array<{ key: WeightKey; label: string; value: number }>>(() => [
  { key: 'same_period_weight', label: '历史同期', value: form.weights.same_period_weight },
  { key: 'frequency_weight', label: '频率', value: form.weights.frequency_weight },
  { key: 'missing_weight', label: '遗漏', value: form.weights.missing_weight },
  { key: 'structure_weight', label: '结构', value: form.weights.structure_weight },
]);

const sampleSize = computed(() => String(lottery.replayContext?.sample_size ?? lottery.replayRun?.sample_size ?? 0));
const sampleRange = computed(() => {
  const range = lottery.replayContext?.available_range;
  if (!range?.earliest_issue_no && !range?.latest_issue_no) return '等待检查';
  return `${range.earliest_issue_no ?? '--'} - ${range.latest_issue_no ?? '--'}`;
});
const cutoffIssue = computed(() =>
  lottery.replayContext?.cutoff?.issue_no ?? lottery.replayRun?.cutoff_issue_no ?? '--',
);
const cutoffDate = computed(() =>
  lottery.replayContext?.cutoff?.draw_date ?? lottery.replayRun?.cutoff_draw_date ?? '目标期之前',
);
const leakageStatus = computed(() => {
  const check = lottery.replayRun?.leakage_check ?? lottery.replayContext?.leakage_check;
  if (!check) return '未检查';
  return check.passed ? '通过' : '失败';
});
const leakageRule = computed(() =>
  lottery.replayRun?.leakage_check.rule ?? lottery.replayContext?.leakage_check.rule ?? '训练数据 < 目标期',
);
const baselineValue = computed(() =>
  lottery.replayRun ? `${lottery.replayRun.baseline.simulations}` : String(form.baselineSimulations),
);
const baselineMeta = computed(() => {
  if (!lottery.replayRun) return '随机抽样次数';
  return `均值 ${lottery.replayRun.baseline.average_score} · 中奖率 ${formatPercentile(lottery.replayRun.baseline.any_prize_rate)}`;
});
const warnings = computed(() => lottery.replayRun?.warnings ?? lottery.replayContext?.warnings ?? []);
const samePeriodDeviation = computed(
  () => lottery.replayRun?.same_period_deviation ?? lottery.replayContext?.same_period_deviation ?? null,
);
const deviationMetricItems = computed<
  Array<{ key: string; label: string; metric: LotterySamePeriodDeviationMetric }>
>(() => {
  const deviation = samePeriodDeviation.value;
  if (!deviation) return [];
  return [
    { key: 'front-repeat', label: '前区重复', metric: deviation.front_repeat },
    { key: 'back-repeat', label: '后区重复', metric: deviation.back_repeat },
    { key: 'front-sum', label: '前区和值', metric: deviation.front_sum },
    { key: 'front-span', label: '前区跨度', metric: deviation.front_span },
  ];
});
const deviationPatternItems = computed<
  Array<{ key: string; label: string; metric: LotterySamePeriodDeviationPattern }>
>(() => {
  const deviation = samePeriodDeviation.value;
  if (!deviation) return [];
  return [
    { key: 'front-zone', label: '三区结构', metric: deviation.front_zone },
    { key: 'front-route012', label: '012路结构', metric: deviation.front_route012 },
  ];
});

const explanationSections: LotteryExplanationSection[] = [
  {
    title: '防未来数据泄漏',
    items: [
      '目标期开奖本身不会进入训练样本。',
      '训练样本最后一期会显示为截止期号。',
      '如果后端发现训练样本包含目标期或之后期号，会直接报错。',
    ],
  },
  {
    title: '随机基准',
    items: [
      '随机基准用于回答策略结果是否只是普通随机波动。',
      '随机分位越高，只代表这一次回放相对随机样本更靠前。',
      '单次回放不能证明策略长期有效。',
    ],
  },
  {
    title: '历史同期偏离',
    items: [
      '最近开奖是否偏离历史同期，需要用重复数、和值、跨度和结构距离验证。',
      '本页先保证回放边界正确，后续可以扩展同期偏离度。',
      '偏离不等于下一期会回归，只能作为样本结构观察。',
    ],
  },
];

onMounted(() => {
  const latestIssue = lottery.draws?.items[0]?.issue_no;
  if (latestIssue && !form.targetIssueNo) {
    form.targetIssueNo = latestIssue;
  }
  void lottery.loadOverview().then(() => {
    if (!form.targetIssueNo && lottery.draws?.items[0]?.issue_no) {
      form.targetIssueNo = lottery.draws.items[0].issue_no;
    }
  });
});

async function loadContext(): Promise<void> {
  if (!form.targetIssueNo.trim()) {
    ElMessage.warning('请先输入目标期号');
    return;
  }
  loadingContext.value = true;
  try {
    await lottery.loadReplayContext(form.targetIssueNo.trim(), form.sampleLimit);
  } finally {
    loadingContext.value = false;
  }
}

async function handleRunReplay(): Promise<void> {
  if (!form.targetIssueNo.trim()) {
    ElMessage.warning('请先输入目标期号');
    return;
  }
  running.value = true;
  try {
    await lottery.runReplay({
      target_issue_no: form.targetIssueNo.trim(),
      sets: form.sets,
      sample_limit: form.sampleLimit,
      same_period_count: form.samePeriodCount,
      baseline_simulations: form.baselineSimulations,
      seed: parseSeed(),
      strategy: { ...form.weights },
    });
    ElMessage.success('历史回放完成');
  } finally {
    running.value = false;
  }
}

function parseSeed(): number | null {
  const value = form.seedText.trim();
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

function formatPercentile(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatSigned(value: number): string {
  if (value > 0) return `+${value}`;
  return String(value);
}

function deviationLevelLabel(level: string): string {
  const labels: Record<string, string> = {
    low: '接近',
    medium: '中等偏离',
    high: '明显偏离',
    common: '常见',
    uncommon: '少见',
    not_seen: '未出现',
    sample_limited: '样本少',
  };
  return labels[level] ?? level;
}

function deviationLevelClass(level: string): string {
  if (['high', 'not_seen'].includes(level)) return 'is-high';
  if (['medium', 'uncommon', 'sample_limited'].includes(level)) return 'is-medium';
  return 'is-low';
}
</script>

<style scoped>
.replay-header,
.replay-actions {
  align-items: center;
}

.replay-actions {
  display: flex;
  flex-shrink: 0;
  gap: 12px;
}

.replay-panel,
.replay-metrics,
.warning-panel {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.replay-form,
.weight-grid,
.replay-list {
  display: grid;
  gap: 12px;
}

.replay-form {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.replay-form label {
  color: var(--color-muted);
  display: grid;
  font-size: 12px;
  gap: 8px;
}

.weight-grid {
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 16px;
  padding-top: 16px;
}

.weight-item {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.weight-item div {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.weight-item span {
  color: var(--color-primary);
  font-weight: 700;
}

.warning-list {
  display: grid;
  gap: 10px;
}

.deviation-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.deviation-card {
  background: rgba(15, 23, 42, 0.38);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 8px;
  padding: 12px;
}

.deviation-card-head {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.deviation-level {
  border-radius: 999px;
  font-size: 12px;
  padding: 3px 8px;
}

.deviation-level.is-low {
  background: rgba(34, 197, 94, 0.14);
  color: #86efac;
}

.deviation-level.is-medium {
  background: rgba(245, 158, 11, 0.14);
  color: #fcd34d;
}

.deviation-level.is-high {
  background: rgba(248, 113, 113, 0.16);
  color: #fca5a5;
}

.deviation-value {
  color: var(--color-text);
  font-size: 24px;
  font-weight: 800;
}

.deviation-meta,
.deviation-notes {
  color: var(--color-muted);
  font-size: 13px;
}

.deviation-notes {
  display: grid;
  gap: 6px;
  margin: 12px 0 0;
  padding-left: 18px;
}

.target-line,
.card-head,
.hit-grid {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: space-between;
}

.target-line {
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  margin-bottom: 14px;
  padding-bottom: 14px;
}

.target-line span,
.hit-grid,
.replay-card li {
  color: var(--color-muted);
  font-size: 13px;
}

.ball-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.replay-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.replay-card {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  padding: 14px;
}

.replay-card ul {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 18px;
}

.hit-grid {
  justify-content: flex-start;
}

@media (max-width: 1180px) {
  .replay-form,
  .weight-grid,
  .deviation-grid,
  .replay-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .replay-header,
  .replay-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .replay-form,
  .weight-grid,
  .deviation-grid,
  .replay-list {
    grid-template-columns: 1fr;
  }
}
</style>
