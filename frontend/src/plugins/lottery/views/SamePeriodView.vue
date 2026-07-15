<template>
  <div>
    <section class="page-header same-period-header">
      <div>
        <h1 class="page-title">历史同期</h1>
        <div class="page-subtitle">按期号后三位对比往年同期开奖</div>
      </div>
      <div class="same-period-actions">
        <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
        <el-input
          v-model="targetIssueInput"
          class="issue-input"
          clearable
          placeholder="完整期号或后三位"
          @keyup.enter="reloadSamePeriod"
        />
        <el-button :icon="Refresh" :loading="lottery.loading" @click="reloadSamePeriod">
          查询
        </el-button>
      </div>
    </section>

    <div class="grid metrics same-period-metrics">
      <MetricCard label="目标期号" :value="targetIssue" :meta="targetDate" />
      <MetricCard label="同期序号" :value="issueSuffix" meta="期号后三位" />
      <MetricCard label="展示期数" :value="itemCount" :meta="requestedCount" />
      <MetricCard label="最高重合" :value="bestMatchValue" :meta="bestMatchMeta" />
    </div>

    <section class="panel same-period-panel">
      <div class="panel-header">
        <h2 class="panel-title">目标开奖号</h2>
        <span class="table-meta">用于计算历史同期重合</span>
      </div>
      <div class="panel-body target-draw">
        <div v-if="lottery.samePeriod" class="draw-line">
          <span class="draw-label">前区</span>
          <LotteryBall
            v-for="number in lottery.samePeriod.target.front_numbers"
            :key="`target-front-${number}`"
            area="front"
            :value="number"
          />
          <span class="draw-label back-label">后区</span>
          <LotteryBall
            v-for="number in lottery.samePeriod.target.back_numbers"
            :key="`target-back-${number}`"
            area="back"
            :value="number"
          />
        </div>
        <EmptyState
          v-else
          title="暂无同期数据"
          description="请先同步大乐透历史开奖数据。"
        />
      </div>
    </section>

    <section class="panel same-period-panel">
      <div class="panel-header">
        <h2 class="panel-title">历史同期列表</h2>
        <span class="table-meta">默认显示最近 5 期历史同期</span>
      </div>
      <div class="panel-body same-period-list">
        <article
          v-for="item in lottery.samePeriod?.items ?? []"
          :key="item.draw.issue_no"
          class="same-period-card"
        >
          <div class="card-head">
            <div>
              <strong>{{ item.draw.issue_no }}</strong>
              <span>{{ item.draw.draw_date }}</span>
            </div>
            <el-tag effect="dark" type="info">
              {{ item.front_match_count }} + {{ item.back_match_count }}
            </el-tag>
          </div>
          <div class="draw-line">
            <span class="draw-label">前区</span>
            <LotteryBall
              v-for="number in item.draw.front_numbers"
              :key="`${item.draw.issue_no}-front-${number}`"
              :area="item.front_matches.includes(number) ? 'back' : 'front'"
              :value="number"
            />
          </div>
          <div class="draw-line">
            <span class="draw-label">后区</span>
            <LotteryBall
              v-for="number in item.draw.back_numbers"
              :key="`${item.draw.issue_no}-back-${number}`"
              area="back"
              :value="number"
            />
          </div>
          <div class="match-summary">
            <span>前区重合：{{ formatMatches(item.front_matches) }}</span>
            <span>后区重合：{{ formatMatches(item.back_matches) }}</span>
          </div>
        </article>
        <EmptyState
          v-if="lottery.samePeriod && lottery.samePeriod.items.length === 0"
          title="暂无历史同期"
          description="当前数据库里还没有更早年份的同序号开奖。"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const targetIssueInput = ref('');

const targetIssue = computed(() => lottery.samePeriod?.target.issue_no ?? '--');
const targetDate = computed(() => lottery.samePeriod?.target.draw_date ?? '默认最新一期');
const issueSuffix = computed(() => lottery.samePeriod?.issue_suffix ?? '--');
const itemCount = computed(() => String(lottery.samePeriod?.items.length ?? 0));
const requestedCount = computed(() => `请求 ${lottery.samePeriod?.requested_count ?? 5} 期`);
const bestMatch = computed(() =>
  [...(lottery.samePeriod?.items ?? [])].sort(
    (left, right) =>
      right.front_match_count + right.back_match_count -
        (left.front_match_count + left.back_match_count) ||
      right.front_match_count - left.front_match_count,
  )[0] ?? null,
);
const bestMatchValue = computed(() =>
  bestMatch.value
    ? `${bestMatch.value.front_match_count}+${bestMatch.value.back_match_count}`
    : '--',
);
const bestMatchMeta = computed(() => bestMatch.value?.draw.issue_no ?? '暂无历史同期');

async function reloadSamePeriod(): Promise<void> {
  lottery.loading = true;
  try {
    await lottery.loadSamePeriod(targetIssueInput.value.trim() || undefined, 5);
  } finally {
    lottery.loading = false;
  }
}

function formatMatches(numbers: number[]): string {
  return numbers.length ? numbers.map((number) => String(number).padStart(2, '0')).join('、') : '无';
}

onMounted(() => {
  void reloadSamePeriod();
});
</script>

<style scoped>
.same-period-header {
  align-items: center;
}

.same-period-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 12px;
}

.back-link,
.table-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.issue-input {
  width: 180px;
}

.same-period-metrics,
.same-period-panel {
  margin-top: 16px;
}

.target-draw,
.same-period-list {
  display: grid;
  gap: 12px;
}

.same-period-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.same-period-card {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  min-width: 0;
  padding: 12px;
}

.card-head {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.card-head strong {
  display: block;
  font-size: 18px;
}

.card-head span,
.draw-label,
.match-summary {
  color: var(--color-muted);
  font-size: 12px;
}

.draw-line {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.back-label {
  margin-left: 8px;
}

.match-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 860px) {
  .same-period-header,
  .same-period-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .issue-input {
    width: 100%;
  }

  .same-period-list {
    grid-template-columns: 1fr;
  }
}
</style>
