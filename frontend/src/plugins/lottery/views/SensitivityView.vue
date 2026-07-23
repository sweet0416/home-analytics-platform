<template>
  <div>
    <section class="page-header sensitivity-header">
      <div>
        <h1 class="page-title">参数敏感度</h1>
        <div class="page-subtitle">检查窗口和权重变化后，策略表现是否稳定或疑似过拟合</div>
      </div>
      <div class="sensitivity-actions">
        <el-button type="primary" :loading="loading" @click="runAnalysis">运行分析</el-button>
      </div>
    </section>

    <DltModuleNav />

    <DisclaimerAlert :text="lottery.sensitivity?.disclaimer ?? fallbackDisclaimer" />

    <section class="panel sensitivity-panel">
      <div class="panel-header">
        <h2 class="panel-title">分析参数</h2>
        <span class="panel-meta">默认从目标期向前滚动 5 期，不写入回放记录</span>
      </div>
      <div class="sensitivity-form">
        <label>
          目标期号
          <el-input v-model="form.targetIssueNo" placeholder="例如 26082" />
        </label>
        <label>
          回放期数
          <el-input-number v-model="form.targetCount" :min="1" :max="20" />
        </label>
        <label>
          生成组数
          <el-input-number v-model="form.sets" :min="1" :max="12" />
        </label>
        <label>
          历史同期
          <el-input-number v-model="form.samePeriodCount" :min="1" :max="20" />
        </label>
        <label>
          随机基准
          <el-input-number v-model="form.baselineSimulations" :min="100" :max="20000" :step="500" />
        </label>
        <label>
          Seed
          <el-input v-model="form.seedText" placeholder="留空为随机" />
        </label>
      </div>
      <div class="window-list">
        <span>样本窗口</span>
        <el-checkbox-group v-model="form.sampleWindows">
          <el-checkbox-button v-for="window in windowOptions" :key="window" :label="window">
            {{ window }}
          </el-checkbox-button>
        </el-checkbox-group>
      </div>
    </section>

    <div class="grid metrics sensitivity-metrics">
      <MetricCard label="参数组合" :value="combinationCount" :meta="profileMeta" />
      <MetricCard label="最佳组合" :value="bestProfile" :meta="bestWindow" />
      <MetricCard label="稳定性" :value="stabilityLabel" :meta="positiveRate" />
      <MetricCard label="滚动期数" :value="targetCountValue" :meta="targetRangeMeta" />
    </div>

    <section v-if="lottery.sensitivity" class="panel sensitivity-panel">
      <div class="panel-header">
        <h2 class="panel-title">稳定性结论</h2>
        <span class="panel-meta">目标 {{ lottery.sensitivity.target_issue_nos.join(' / ') }}</span>
      </div>
      <div class="summary-band">
        <strong>{{ lottery.sensitivity.summary.stability_label }}</strong>
        <span>{{ lottery.sensitivity.summary.overfit_warning }}</span>
      </div>
    </section>

    <section v-if="lottery.sensitivity?.results.length" class="panel sensitivity-panel">
      <div class="panel-header">
        <h2 class="panel-title">参数组合表现</h2>
        <span class="panel-meta">按平均分超过随机基准的幅度排序</span>
      </div>
      <div class="result-table">
        <div class="result-row result-head">
          <span>画像</span>
          <span>窗口</span>
          <span>均分差</span>
          <span>多期胜率</span>
          <span>最佳命中</span>
          <span>随机分位</span>
          <span>提示</span>
        </div>
        <article
          v-for="item in lottery.sensitivity.results"
          :key="`${item.profile_name}-${item.sample_window}`"
          class="result-row"
        >
          <span>{{ item.profile_name }}</span>
          <span>{{ item.sample_window }}</span>
          <span :class="scoreDeltaClass(item.average_score_delta)">
            {{ formatSigned(item.average_score_delta) }}
          </span>
          <span>{{ formatPercent(item.positive_target_rate) }}</span>
          <span>{{ item.best_match_key ?? '--' }}</span>
          <span>{{ formatPercent(item.best_baseline_percentile) }}</span>
          <span>{{ item.warning }}</span>
        </article>
      </div>
    </section>

    <section v-if="topResult" class="panel sensitivity-panel">
      <div class="panel-header">
        <h2 class="panel-title">当前最佳样本</h2>
        <span class="panel-meta">
          {{ topResult.profile_name }} · 窗口 {{ topResult.sample_window }}
        </span>
      </div>
      <div class="ball-row">
        <LotteryBall
          v-for="number in topResult.best_front_numbers"
          :key="`best-front-${number}`"
          area="front"
          :value="number"
        />
        <LotteryBall
          v-for="number in topResult.best_back_numbers"
          :key="`best-back-${number}`"
          area="back"
          :value="number"
        />
      </div>
    </section>

    <LotteryExplanationPanel
      title="这页怎么看"
      subtitle="敏感度分析是为了识别不稳定参数，不是预测下一期"
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
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const loading = ref(false);
const fallbackDisclaimer = '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。';
const windowOptions = [50, 100, 200, 500];

const form = reactive({
  targetIssueNo: '',
  targetCount: 5,
  sets: 5,
  samePeriodCount: 10,
  baselineSimulations: 1000,
  seedText: '20260723',
  sampleWindows: [50, 100, 200, 500],
});

const topResult = computed(() => lottery.sensitivity?.results[0] ?? null);
const combinationCount = computed(() => String(lottery.sensitivity?.combination_count ?? 0));
const profileMeta = computed(() =>
  lottery.sensitivity ? `${lottery.sensitivity.profile_count} 个权重画像` : '等待运行',
);
const bestProfile = computed(() => lottery.sensitivity?.summary.best_profile_name ?? '--');
const bestWindow = computed(() =>
  lottery.sensitivity?.summary.best_sample_window
    ? `窗口 ${lottery.sensitivity.summary.best_sample_window}`
    : '等待运行',
);
const stabilityLabel = computed(() => lottery.sensitivity?.summary.stability_label ?? '--');
const positiveRate = computed(() =>
  lottery.sensitivity
    ? `优于随机 ${formatPercent(lottery.sensitivity.summary.positive_delta_rate)}`
    : '等待运行',
);
const baselineValue = computed(() =>
  lottery.sensitivity ? String(lottery.sensitivity.baseline.simulations) : String(form.baselineSimulations),
);
const baselineMeta = computed(() =>
  lottery.sensitivity
    ? `均值 ${lottery.sensitivity.baseline.average_score}`
    : '随机抽样次数',
);
const targetCountValue = computed(() =>
  String(lottery.sensitivity?.evaluated_target_count ?? form.targetCount),
);
const targetRangeMeta = computed(() =>
  lottery.sensitivity?.target_issue_nos.length
    ? lottery.sensitivity.target_issue_nos.join(' / ')
    : '最近目标期',
);

const explanationSections: LotteryExplanationSection[] = [
  {
    title: '为什么要做敏感度',
    items: [
      '如果结论只在某一个窗口或权重下好看，可能只是参数偶然性。',
      '稳定结果应该在多个相近参数下不至于完全反转。',
      '默认会连续检查最近多期，减少单期偶然性影响。',
    ],
  },
  {
    title: '如何读均分差',
    items: [
      '均分差大于 0 表示该组合平均命中分高于随机基准均值。',
      '多期胜率表示该参数组合在多少目标期上超过随机均值。',
      '随机分位只表示当前回放结果相对随机样本的位置。',
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

async function runAnalysis(): Promise<void> {
  if (!form.targetIssueNo.trim()) {
    ElMessage.warning('请先输入目标期号');
    return;
  }
  if (!form.sampleWindows.length) {
    ElMessage.warning('请至少选择一个样本窗口');
    return;
  }
  loading.value = true;
  try {
    await lottery.analyzeSensitivity({
      target_issue_no: form.targetIssueNo.trim(),
      target_count: form.targetCount,
      sets: form.sets,
      same_period_count: form.samePeriodCount,
      sample_windows: [...form.sampleWindows].sort((left, right) => left - right),
      weight_profiles: [],
      baseline_simulations: form.baselineSimulations,
      seed: parseSeed(),
    });
    ElMessage.success('参数敏感度分析完成');
  } finally {
    loading.value = false;
  }
}

function parseSeed(): number | null {
  const value = form.seedText.trim();
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatSigned(value: number): string {
  if (value > 0) return `+${value}`;
  return String(value);
}

function scoreDeltaClass(value: number): string {
  if (value > 0) return 'is-positive';
  if (value < 0) return 'is-negative';
  return '';
}
</script>

<style scoped>
.sensitivity-header,
.sensitivity-actions {
  align-items: center;
}

.sensitivity-actions {
  display: flex;
  flex-shrink: 0;
  gap: 12px;
}

.sensitivity-panel,
.sensitivity-metrics {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.sensitivity-form {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.sensitivity-form label {
  color: var(--color-muted);
  display: grid;
  font-size: 12px;
  gap: 8px;
}

.window-list {
  align-items: center;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  color: var(--color-muted);
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
}

.summary-band {
  background: rgba(56, 189, 248, 0.09);
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 8px;
  display: grid;
  gap: 8px;
  padding: 14px;
}

.summary-band strong {
  color: var(--color-primary);
  font-size: 20px;
}

.summary-band span,
.result-row span {
  color: var(--color-muted);
  font-size: 13px;
}

.result-table {
  display: grid;
  gap: 8px;
}

.result-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  grid-template-columns: 1.2fr 0.7fr 0.7fr 0.8fr 0.8fr 0.8fr 1fr;
  padding: 10px 12px;
}

.result-head {
  background: rgba(15, 23, 42, 0.48);
  font-weight: 700;
}

.is-positive {
  color: #86efac !important;
}

.is-negative {
  color: #fca5a5 !important;
}

.ball-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 1180px) {
  .sensitivity-form,
  .result-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .sensitivity-header,
  .sensitivity-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .sensitivity-form,
  .result-row {
    grid-template-columns: 1fr;
  }
}
</style>
