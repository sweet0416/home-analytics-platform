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
        <div class="count-control">
          <span>显示</span>
          <el-input-number
            v-model="displayCount"
            :min="1"
            :max="20"
            :step="1"
            size="small"
            @change="reloadSamePeriod"
          />
          <span>期</span>
        </div>
        <el-button :icon="Refresh" :loading="lottery.loading" @click="reloadSamePeriod">
          查询
        </el-button>
      </div>
    </section>

    <DltModuleNav />

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
        <span class="table-meta">显示最近 {{ displayCount }} 期历史同期</span>
      </div>
      <div class="panel-body">
        <el-table
          v-if="lottery.samePeriod?.items.length"
          :data="lottery.samePeriod.items"
          class="same-period-table"
        >
          <el-table-column prop="draw.issue_no" label="期号" width="110" />
          <el-table-column prop="draw.draw_date" label="开奖日期" width="130" />
          <el-table-column label="前区" min-width="190">
            <template #default="{ row }">
              <div class="draw-line">
                <LotteryBall
                  v-for="number in row.draw.front_numbers"
                  :key="`${row.draw.issue_no}-front-${number}`"
                  :area="row.front_matches.includes(number) ? 'back' : 'front'"
                  :value="number"
                />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="后区" min-width="90">
            <template #default="{ row }">
              <div class="draw-line">
                <LotteryBall
                  v-for="number in row.draw.back_numbers"
                  :key="`${row.draw.issue_no}-back-${number}`"
                  area="back"
                  :value="number"
                />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="重合" width="110">
            <template #default="{ row }">
              <el-tag effect="dark" type="info">
                {{ row.front_match_count }} + {{ row.back_match_count }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="重合号码" min-width="210">
            <template #default="{ row }">
              <div class="match-summary">
                <span>前区：{{ formatMatches(row.front_matches) }}</span>
                <span>后区：{{ formatMatches(row.back_matches) }}</span>
              </div>
            </template>
          </el-table-column>
        </el-table>
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
import DltModuleNav from '@/plugins/lottery/components/DltModuleNav.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const targetIssueInput = ref('');
const displayCount = ref(10);

const targetIssue = computed(() => lottery.samePeriod?.target.issue_no ?? '--');
const targetDate = computed(() => lottery.samePeriod?.target.draw_date ?? '默认最新一期');
const issueSuffix = computed(() => lottery.samePeriod?.issue_suffix ?? '--');
const itemCount = computed(() => String(lottery.samePeriod?.items.length ?? 0));
const requestedCount = computed(() => `请求 ${lottery.samePeriod?.requested_count ?? 10} 期`);
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
    await lottery.loadSamePeriod(targetIssueInput.value.trim() || undefined, displayCount.value);
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

.count-control {
  align-items: center;
  color: var(--color-muted);
  display: flex;
  flex-shrink: 0;
  font-size: 13px;
  gap: 8px;
}

.count-control :deep(.el-input-number) {
  width: 96px;
}

.same-period-metrics,
.same-period-panel {
  margin-top: 16px;
}

.target-draw {
  display: grid;
  gap: 12px;
}

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

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.5);
  --el-table-text-color: var(--color-text);
  --el-table-header-text-color: var(--color-muted);
  --el-table-border-color: rgba(148, 163, 184, 0.14);
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

  .count-control {
    justify-content: space-between;
  }

  :deep(.el-table) {
    font-size: 12px;
  }
}
</style>
