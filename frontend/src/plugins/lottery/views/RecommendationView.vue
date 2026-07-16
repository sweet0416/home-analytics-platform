<template>
  <div>
    <section class="page-header recommendation-header">
      <div>
        <h1 class="page-title">选号推荐</h1>
        <div class="page-subtitle">
          结合历史同期、冷热、遗漏、和值、跨度、奇偶和区间分布生成参考组合
        </div>
      </div>
      <div class="recommendation-actions">
        <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
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
          :loading="lottery.loading"
          @click="reloadRecommendations"
        >
          生成推荐
        </el-button>
      </div>
    </section>

    <DisclaimerAlert
      :text="lottery.recommendations?.disclaimer ?? fallbackDisclaimer"
      class="recommendation-disclaimer"
    />

    <section class="panel control-panel">
      <div class="panel-header">
        <h2 class="panel-title">推荐参数</h2>
        <span class="panel-meta">参数越大，参考数据越多，计算也会稍慢</span>
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
              <el-tag effect="dark" type="info">
                和值 {{ item.front_sum }} / 跨度 {{ item.front_span }}
              </el-tag>
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

    <section class="panel methodology-panel">
      <div class="panel-header">
        <h2 class="panel-title">算法说明</h2>
        <span class="panel-meta">通俗版</span>
      </div>
      <div class="panel-body">
        <div class="methodology-list">
          <div
            v-for="item in methodology"
            :key="item"
            class="methodology-item"
          >
            {{ item }}
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import type { LotteryRecommendationNumberDetail } from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const targetIssueInput = ref('');
const setCount = ref(5);
const samePeriodCount = ref(10);
const sampleLimit = ref(200);
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
        '再结合最近样本里的冷热程度、当前遗漏期数和号码分布，给每个号码打分。',
        '最后筛掉过于极端的和值、跨度、奇偶和区间结构，保留更均衡的组合。',
      ],
);

async function reloadRecommendations(): Promise<void> {
  lottery.loading = true;
  try {
    await lottery.loadRecommendations(
      targetIssueInput.value.trim() || undefined,
      setCount.value,
      samePeriodCount.value,
      sampleLimit.value,
    );
  } finally {
    lottery.loading = false;
  }
}

function formatNumber(value: number): string {
  return String(value).padStart(2, '0');
}

function formatScore(value: number): string {
  return value.toFixed(2);
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

.back-link,
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
.recommendation-panel,
.methodology-panel {
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

.recommendation-list {
  display: grid;
  gap: 14px;
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
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .control-item {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
