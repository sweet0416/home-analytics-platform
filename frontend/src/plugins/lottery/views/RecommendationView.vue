<template>
  <div>
    <section class="page-header recommendation-header">
      <div>
        <h1 class="page-title">选号推荐</h1>
        <div class="page-subtitle">
          结合历史同期、冷热遗漏、共现强度、结构均衡和组合覆盖生成参考组合
        </div>
      </div>
      <div class="recommendation-actions">
        <el-input
          v-model="targetIssueInput"
          class="issue-input"
          clearable
          placeholder="目标期号或后三位"
          @keyup.enter="reloadRecommendations"
        />
        <el-button
          type="primary"
          :icon="Refresh"
          :loading="recommendationLoading"
          @click="reloadRecommendations"
        >
          生成推荐
        </el-button>
      </div>
    </section>

    <DltModuleNav />

    <DisclaimerAlert
      :text="lottery.recommendations?.disclaimer ?? fallbackDisclaimer"
      class="recommendation-disclaimer"
    />

    <section class="panel control-panel">
      <div class="panel-header">
        <h2 class="panel-title">推荐参数</h2>
        <span class="panel-meta">参数越大，参考数据越多，计算也会稍慢</span>
      </div>
      <div class="strategy-reset-row">
        <el-button
          class="reset-strategy-button"
          size="small"
          :icon="Refresh"
          @click="resetStrategyWeights"
        >
          恢复默认值
        </el-button>
      </div>
      <div class="panel-body control-grid">
        <div class="control-item">
          <span>推荐组数</span>
          <el-input-number v-model="setCount" :min="1" :max="12" size="small" />
        </div>
        <div class="control-item">
          <span>历史同期</span>
          <el-input-number v-model="samePeriodCount" :min="1" :max="20" size="small" />
        </div>
        <div class="control-item">
          <span>近期样本</span>
          <el-input-number
            v-model="sampleLimit"
            :min="50"
            :max="500"
            :step="50"
            size="small"
          />
        </div>
      </div>
      <div class="strategy-grid">
        <div class="strategy-item">
          <div class="strategy-label">
            <span>历史同期权重</span>
            <strong>{{ samePeriodWeight }}</strong>
          </div>
          <el-slider v-model="samePeriodWeight" :min="0" :max="100" :step="5" />
          <p>越高越看重同序号往年重复出现过的号码。</p>
        </div>
        <div class="strategy-item">
          <div class="strategy-label">
            <span>近期热度权重</span>
            <strong>{{ frequencyWeight }}</strong>
          </div>
          <el-slider v-model="frequencyWeight" :min="0" :max="100" :step="5" />
          <p>越高越偏向最近样本里出现频率更高的号码。</p>
        </div>
        <div class="strategy-item">
          <div class="strategy-label">
            <span>遗漏权重</span>
            <strong>{{ missingWeight }}</strong>
          </div>
          <el-slider v-model="missingWeight" :min="0" :max="100" :step="5" />
          <p>越高越偏向较久没有出现、遗漏期数更高的号码。</p>
        </div>
        <div class="strategy-item">
          <div class="strategy-label">
            <span>结构均衡权重</span>
            <strong>{{ structureWeight }}</strong>
          </div>
          <el-slider v-model="structureWeight" :min="0" :max="100" :step="5" />
          <p>越高越看重和值、跨度、奇偶、区间和012路是否均衡。</p>
        </div>
        <div class="strategy-item">
          <div class="strategy-label">
            <span>共现权重</span>
            <strong>{{ coOccurrenceWeight }}</strong>
          </div>
          <el-slider v-model="coOccurrenceWeight" :min="0" :max="100" :step="5" />
          <p>越高越参考近期号码同期开奖关联，但会按随机期望校正。</p>
        </div>
        <div class="strategy-item">
          <div class="strategy-label">
            <span>覆盖分散权重</span>
            <strong>{{ coverageWeight }}</strong>
          </div>
          <el-slider v-model="coverageWeight" :min="0" :max="100" :step="5" />
          <p>越高越倾向让多组号码之间少重复，尤其减少后区重复。</p>
        </div>
      </div>
    </section>

    <div class="grid metrics recommendation-metrics">
      <MetricCard label="目标期号" :value="targetIssue" :meta="issueSuffix" />
      <MetricCard label="样本期数" :value="sampleSize" meta="用于冷热与遗漏统计" />
      <MetricCard label="同期窗口" :value="samePeriodWindow" meta="同序号历史开奖" />
      <MetricCard label="推荐组合" :value="recommendationCount" meta="每组 5 + 2" />
    </div>

    <section class="panel recommendation-panel">
      <div class="panel-header">
        <h2 class="panel-title">推荐号码</h2>
        <span class="panel-meta">按综合评分排序</span>
      </div>
      <div class="panel-body">
        <div v-if="lottery.recommendations?.recommendations.length" class="summary-block">
          <div class="summary-header">
            <div>
              <h3 class="summary-title">快速汇总</h3>
              <div class="summary-meta">五组集中查看，方便截图、抄写或对照筛选。</div>
            </div>
            <el-tag effect="dark" type="success">
              {{ recommendationCount }} 组
            </el-tag>
          </div>
          <div class="summary-list">
            <div
              v-for="item in lottery.recommendations.recommendations"
              :key="`summary-${item.rank}`"
              class="summary-row"
            >
              <span class="summary-rank">第 {{ item.rank }} 组</span>
              <div class="summary-numbers">
                <span class="number-label">前区</span>
                <LotteryBall
                  v-for="number in item.front_numbers"
                  :key="`summary-front-${item.rank}-${number}`"
                  area="front"
                  :value="number"
                />
                <span class="number-label back-label">后区</span>
                <LotteryBall
                  v-for="number in item.back_numbers"
                  :key="`summary-back-${item.rank}-${number}`"
                  area="back"
                  :value="number"
                />
              </div>
              <RouterLink :to="backtestRoute(item)" class="backtest-link">去回测</RouterLink>
            </div>
          </div>
        </div>

        <div v-if="lottery.recommendations?.recommendations.length" class="recommendation-list">
          <article
            v-for="item in lottery.recommendations.recommendations"
            :key="item.rank"
            class="recommendation-card"
          >
            <div class="card-topline">
              <div>
                <div class="card-rank">第 {{ item.rank }} 组</div>
                <div class="card-score">综合评分 {{ formatScore(item.score) }}</div>
              </div>
              <div class="card-actions">
                <el-tag effect="dark" type="info">
                  和值 {{ item.front_sum }} / 跨度 {{ item.front_span }}
                </el-tag>
                <RouterLink :to="backtestRoute(item)" class="backtest-link">去回测</RouterLink>
              </div>
            </div>

            <div class="number-row">
              <span class="number-label">前区</span>
              <LotteryBall
                v-for="number in item.front_numbers"
                :key="`front-${item.rank}-${number}`"
                area="front"
                :value="number"
              />
              <span class="number-label back-label">后区</span>
              <LotteryBall
                v-for="number in item.back_numbers"
                :key="`back-${item.rank}-${number}`"
                area="back"
                :value="number"
              />
            </div>

            <div class="pattern-row">
              <span>奇偶 {{ item.front_parity_pattern }}</span>
              <span>区间 {{ item.front_zone_pattern }}</span>
              <span>012路 {{ item.front_route012_pattern }}</span>
            </div>

            <div class="rationale-block">
              <div class="section-label">推荐依据</div>
              <ul>
                <li v-for="reason in item.rationale" :key="reason">{{ reason }}</li>
              </ul>
            </div>

            <div class="detail-grid">
              <div>
                <div class="section-label">前区重点号</div>
                <div class="detail-list">
                  <span
                    v-for="detail in topDetails(item.front_details)"
                    :key="`front-detail-${item.rank}-${detail.number}`"
                  >
                    {{ formatNumber(detail.number) }}：{{ detail.reasons[0] ?? '综合评分靠前' }}
                  </span>
                </div>
              </div>
              <div>
                <div class="section-label">后区重点号</div>
                <div class="detail-list">
                  <span
                    v-for="detail in topDetails(item.back_details)"
                    :key="`back-detail-${item.rank}-${detail.number}`"
                  >
                    {{ formatNumber(detail.number) }}：{{ detail.reasons[0] ?? '综合评分靠前' }}
                  </span>
                </div>
              </div>
            </div>
          </article>
        </div>

        <EmptyState
          v-else
          title="暂无推荐结果"
          description="请先同步大乐透历史开奖数据，或点击生成推荐重新计算。"
        />
      </div>
    </section>

    <LotteryExplanationPanel
      title="算法说明"
      subtitle="通俗版"
      :sections="explanationSections"
    />
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import DltModuleNav from '@/plugins/lottery/components/DltModuleNav.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import LotteryExplanationPanel, {
  type LotteryExplanationSection,
} from '@/plugins/lottery/components/LotteryExplanationPanel.vue';
import type {
  LotteryRecommendationNumberDetail,
  LotteryRecommendationSet,
} from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const defaultStrategyWeights = {
  same_period: 40,
  frequency: 20,
  missing: 15,
  structure: 10,
  co_occurrence: 10,
  coverage: 16,
} as const;
const targetIssueInput = ref('');
const setCount = ref(5);
const samePeriodCount = ref(10);
const sampleLimit = ref(200);
const samePeriodWeight = ref(defaultStrategyWeights.same_period);
const frequencyWeight = ref(defaultStrategyWeights.frequency);
const missingWeight = ref(defaultStrategyWeights.missing);
const structureWeight = ref(defaultStrategyWeights.structure);
const coOccurrenceWeight = ref(defaultStrategyWeights.co_occurrence);
const coverageWeight = ref(defaultStrategyWeights.coverage);
const recommendationLoading = ref(false);
const fallbackDisclaimer = '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。';

const targetIssue = computed(() => lottery.recommendations?.target_issue_no ?? '--');
const issueSuffix = computed(() =>
  lottery.recommendations?.issue_suffix
    ? `同期序号 ${lottery.recommendations.issue_suffix}`
    : '默认下一期',
);
const sampleSize = computed(() => String(lottery.recommendations?.sample_size ?? 0));
const samePeriodWindow = computed(() =>
  `${lottery.recommendations?.same_period_count ?? samePeriodCount.value} 期`,
);
const recommendationCount = computed(() =>
  String(lottery.recommendations?.recommendations.length ?? 0),
);
const methodology = computed(() =>
  lottery.recommendations?.methodology.length
    ? lottery.recommendations.methodology
    : [
        '先找到目标期号对应的历史同期，观察同序号开奖里反复出现的号码。',
        '再结合最近样本里的冷热程度、当前遗漏期数和共现强度，给每个号码打分。',
        '最后筛掉过于极端的和值、跨度、奇偶和区间结构，并让多组组合尽量分散。',
      ],
);
const explanationSections = computed<LotteryExplanationSection[]>(() => [
  {
    title: '它主要看什么',
    items: methodology.value,
  },
  {
    title: '参数怎么理解',
    items: [
      '历史同期越高，越偏向目标期号同序号附近往年反复出现的号码。',
      '近期热度越高，越偏向最近样本中出现次数靠前的号码。',
      '遗漏权重越高，越偏向较久没有出现的号码；结构权重越高，越避免过于极端的组合。',
      '共现权重越高，越参考近期同期开奖关联；覆盖分散越高，越避免多组号码互相太像。',
    ],
  },
  {
    title: '不要误读',
    items: [
      '综合评分只是历史统计口径下的排序，不是中奖概率排序。',
      '同一组号码即使评分较高，也不代表下一期更容易开出。',
      '推荐结果适合拿去回测、对照和娱乐，不适合作为确定性预测。',
    ],
  },
]);

async function reloadRecommendations(): Promise<void> {
  recommendationLoading.value = true;
  try {
    await lottery.loadRecommendations(
      targetIssueInput.value.trim() || undefined,
      setCount.value,
      samePeriodCount.value,
      sampleLimit.value,
      {
        same_period: samePeriodWeight.value,
        frequency: frequencyWeight.value,
        missing: missingWeight.value,
        structure: structureWeight.value,
        co_occurrence: coOccurrenceWeight.value,
        coverage: coverageWeight.value,
      },
    );
  } finally {
    recommendationLoading.value = false;
  }
}

function resetStrategyWeights(): void {
  samePeriodWeight.value = defaultStrategyWeights.same_period;
  frequencyWeight.value = defaultStrategyWeights.frequency;
  missingWeight.value = defaultStrategyWeights.missing;
  structureWeight.value = defaultStrategyWeights.structure;
  coOccurrenceWeight.value = defaultStrategyWeights.co_occurrence;
  coverageWeight.value = defaultStrategyWeights.coverage;
}

function formatNumber(value: number): string {
  return String(value).padStart(2, '0');
}

function formatScore(value: number): string {
  return value.toFixed(2);
}

function backtestRoute(item: LotteryRecommendationSet): {
  path: string;
  query: Record<string, string>;
} {
  return {
    path: '/lottery/dlt/backtest',
    query: {
      front: item.front_numbers.join(','),
      back: item.back_numbers.join(','),
    },
  };
}

function topDetails(
  details: LotteryRecommendationNumberDetail[],
): LotteryRecommendationNumberDetail[] {
  return [...details].sort((left, right) => right.score - left.score).slice(0, 3);
}

onMounted(() => {
  void reloadRecommendations();
});
</script>

<style scoped>
.recommendation-header {
  align-items: center;
}

.recommendation-actions {
  align-items: center;
  display: flex;
  flex-shrink: 0;
  gap: 12px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.issue-input {
  width: 190px;
}

.recommendation-disclaimer,
.control-panel,
.recommendation-metrics,
.recommendation-panel {
  margin-top: 16px;
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.control-item {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  color: var(--color-muted);
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 12px;
}

.strategy-reset-row {
  display: flex;
  justify-content: flex-end;
  margin: 10px 0 0;
}

.reset-strategy-button {
  border-color: rgba(148, 163, 184, 0.28);
}

.strategy-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.strategy-item {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 12px;
}

.strategy-label {
  align-items: center;
  color: var(--color-text);
  display: flex;
  font-size: 13px;
  justify-content: space-between;
}

.strategy-label strong {
  color: var(--color-primary);
}

.strategy-item p {
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
}

.recommendation-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.recommendation-card {
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.36);
  display: grid;
  gap: 14px;
  padding: 14px;
}

.card-topline,
.card-actions,
.number-row,
.pattern-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.card-topline {
  justify-content: space-between;
}

.card-actions {
  justify-content: flex-end;
}

.backtest-link {
  border: 1px solid rgba(56, 189, 248, 0.34);
  border-radius: 8px;
  color: var(--color-primary);
  font-size: 12px;
  padding: 6px 10px;
}

.card-rank {
  font-size: 16px;
  font-weight: 720;
}

.card-score,
.number-label,
.section-label,
.pattern-row,
.detail-list {
  color: var(--color-muted);
  font-size: 12px;
}

.back-label {
  margin-left: 8px;
}

.pattern-row {
  gap: 12px;
}

.rationale-block ul {
  color: var(--color-text);
  display: grid;
  gap: 6px;
  line-height: 1.6;
  margin: 8px 0 0;
  padding-left: 18px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-list {
  display: grid;
  gap: 6px;
  line-height: 1.55;
  margin-top: 8px;
}

.summary-block {
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.36);
  display: grid;
  gap: 12px;
  padding: 14px;
}

.summary-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.summary-title {
  font-size: 15px;
  margin: 0;
}

.summary-meta {
  color: var(--color-muted);
  font-size: 12px;
  margin-top: 4px;
}

.summary-list {
  display: grid;
  gap: 10px;
}

.summary-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  grid-template-columns: 86px minmax(0, 1fr) auto;
  padding: 12px;
}

.summary-rank {
  font-weight: 700;
}

.summary-numbers {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.methodology-list {
  display: grid;
  gap: 10px;
}

.methodology-item {
  border-left: 3px solid rgba(56, 189, 248, 0.55);
  color: var(--color-muted);
  line-height: 1.65;
  padding-left: 12px;
}

@media (max-width: 860px) {
  .recommendation-header,
  .recommendation-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .issue-input {
    width: 100%;
  }

  .control-grid,
  .strategy-grid,
  .detail-grid,
  .summary-row {
    grid-template-columns: 1fr;
  }

  .control-item {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
