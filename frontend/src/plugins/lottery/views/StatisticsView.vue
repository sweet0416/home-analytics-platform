<template>
  <div>
    <section class="page-header statistics-header">
      <div>
        <h1 class="page-title">统计分析</h1>
        <div class="page-subtitle">频率、遗漏、和值、跨度、冷热和结构分布</div>
      </div>
      <div class="statistics-actions">
        <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
        <el-button :icon="Refresh" :loading="lottery.loading" @click="reloadStatistics">
          刷新
        </el-button>
      </div>
    </section>

    <div class="grid metrics statistics-metrics">
      <MetricCard label="样本期数" :value="sampleSize" :meta="sampleMeta" />
      <MetricCard label="最新期号" :value="latestIssue" meta="统计样本最新一期" />
      <MetricCard label="和值均值" :value="sumAverage" :meta="sumRange" />
      <MetricCard label="跨度均值" :value="spanAverage" :meta="spanRange" />
    </div>

    <section class="panel statistics-panel">
      <div class="panel-header">
        <h2 class="panel-title">冷热号码</h2>
        <span class="table-meta">按最近 {{ lottery.statistics?.sample_size ?? 0 }} 期计算</span>
      </div>
      <div class="panel-body hot-cold-grid">
        <NumberList title="前区热号" :numbers="lottery.statistics?.hot_numbers.front ?? []" />
        <NumberList title="前区冷号" :numbers="lottery.statistics?.cold_numbers.front ?? []" />
        <NumberList title="后区热号" :numbers="lottery.statistics?.hot_numbers.back ?? []" area="back" />
        <NumberList title="后区冷号" :numbers="lottery.statistics?.cold_numbers.back ?? []" area="back" />
      </div>
    </section>

    <section class="panel statistics-panel">
      <div class="panel-header">
        <h2 class="panel-title">结构分布</h2>
      </div>
      <div class="panel-body distribution-grid">
        <div class="distribution-block">
          <h3>奇偶</h3>
          <div v-for="item in lottery.statistics?.parity ?? []" :key="item.pattern" class="distribution-row">
            <span>{{ item.pattern }}</span>
            <strong>{{ item.count }}</strong>
          </div>
        </div>
        <div class="distribution-block">
          <h3>大小</h3>
          <div v-for="item in lottery.statistics?.size ?? []" :key="item.pattern" class="distribution-row">
            <span>{{ item.pattern }}</span>
            <strong>{{ item.count }}</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="panel statistics-panel">
      <div class="panel-header">
        <h2 class="panel-title">号码频次与遗漏</h2>
      </div>
      <div class="panel-body frequency-grid">
        <FrequencyTable title="前区" :numbers="lottery.statistics?.front_frequency ?? []" />
        <FrequencyTable title="后区" :numbers="lottery.statistics?.back_frequency ?? []" area="back" />
      </div>
    </section>

    <section class="panel statistics-panel">
      <div class="panel-header">
        <h2 class="panel-title">近期指标</h2>
        <span class="table-meta">最近 20 期</span>
      </div>
      <div class="panel-body">
        <el-table
          v-if="lottery.statistics?.recent_metrics.length"
          :data="lottery.statistics.recent_metrics"
          class="stats-table"
        >
          <el-table-column prop="issue_no" label="期号" width="110" />
          <el-table-column prop="front_sum" label="和值" width="100" />
          <el-table-column prop="front_span" label="跨度" width="100" />
          <el-table-column prop="front_parity_pattern" label="奇偶" width="120" />
          <el-table-column prop="front_size_pattern" label="大小" width="120" />
          <el-table-column prop="back_sum" label="后区和值" width="120" />
        </el-table>
        <EmptyState
          v-else
          title="暂无统计数据"
          description="请先同步大乐透历史开奖数据。"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, defineComponent, h, onMounted, type PropType } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import type { LotteryNumberFrequency } from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

type BallArea = 'front' | 'back';

const lottery = useLotteryStore();

const sampleSize = computed(() => String(lottery.statistics?.sample_size ?? 0));
const sampleMeta = computed(() => `请求最近 ${lottery.statistics?.requested_limit ?? 100} 期`);
const latestIssue = computed(() => lottery.statistics?.latest_issue_no ?? '--');
const sumAverage = computed(() => formatMetric(lottery.statistics?.sum.average));
const spanAverage = computed(() => formatMetric(lottery.statistics?.span.average));
const sumRange = computed(() => formatRange(lottery.statistics?.sum.min, lottery.statistics?.sum.max));
const spanRange = computed(() => formatRange(lottery.statistics?.span.min, lottery.statistics?.span.max));

const NumberList = defineComponent({
  name: 'NumberList',
  props: {
    area: {
      default: 'front',
      type: String as PropType<BallArea>,
    },
    numbers: {
      required: true,
      type: Array as PropType<LotteryNumberFrequency[]>,
    },
    title: {
      required: true,
      type: String,
    },
  },
  setup(props) {
    return () =>
      h('div', { class: 'number-list' }, [
        h('h3', props.title),
        h(
          'div',
          { class: 'number-list-body' },
          props.numbers.map((item) =>
            h('div', { class: 'number-chip', key: item.number }, [
              h(LotteryBall, { area: props.area, value: item.number }),
              h('span', `出现 ${item.count}`),
              h('small', `遗漏 ${item.missing}`),
            ]),
          ),
        ),
      ]);
  },
});

const FrequencyTable = defineComponent({
  name: 'FrequencyTable',
  props: {
    area: {
      default: 'front',
      type: String as PropType<BallArea>,
    },
    numbers: {
      required: true,
      type: Array as PropType<LotteryNumberFrequency[]>,
    },
    title: {
      required: true,
      type: String,
    },
  },
  setup(props) {
    return () =>
      h('div', { class: 'frequency-table' }, [
        h('h3', props.title),
        h(
          'div',
          { class: 'frequency-table-body' },
          props.numbers.map((item) =>
            h('div', { class: 'frequency-row', key: item.number }, [
              h(LotteryBall, { area: props.area, value: item.number }),
              h('span', `出现 ${item.count}`),
              h('strong', `遗漏 ${item.missing}`),
            ]),
          ),
        ),
      ]);
  },
});

function formatMetric(value: number | null | undefined): string {
  return value === null || value === undefined ? '--' : String(value);
}

function formatRange(min: number | null | undefined, max: number | null | undefined): string {
  if (min === null || min === undefined || max === null || max === undefined) return '暂无范围';
  return `${min} - ${max}`;
}

async function reloadStatistics(): Promise<void> {
  lottery.loading = true;
  try {
    await lottery.loadStatistics();
  } finally {
    lottery.loading = false;
  }
}

onMounted(() => {
  void reloadStatistics();
});
</script>

<style scoped>
.statistics-header {
  align-items: center;
}

.statistics-actions {
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

.statistics-metrics,
.statistics-panel {
  margin-top: 16px;
}

.hot-cold-grid,
.distribution-grid,
.frequency-grid {
  display: grid;
  gap: 12px;
}

.hot-cold-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.distribution-grid,
.frequency-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.number-list,
.distribution-block,
.frequency-table {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  min-width: 0;
  padding: 12px;
}

.number-list h3,
.distribution-block h3,
.frequency-table h3 {
  margin: 0 0 12px;
  font-size: 14px;
}

.number-list-body {
  display: grid;
  gap: 8px;
}

.number-chip,
.frequency-row,
.distribution-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.number-chip span,
.frequency-row span,
.distribution-row span {
  color: var(--color-muted);
  font-size: 12px;
}

.number-chip small {
  color: var(--color-muted);
  font-size: 11px;
  margin-left: auto;
}

.distribution-row,
.frequency-row {
  justify-content: space-between;
}

.frequency-table-body {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.5);
  --el-table-text-color: var(--color-text);
  --el-table-header-text-color: var(--color-muted);
  --el-table-border-color: rgba(148, 163, 184, 0.14);
}

@media (max-width: 1180px) {
  .hot-cold-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .statistics-header,
  .statistics-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .hot-cold-grid,
  .distribution-grid,
  .frequency-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .frequency-table-body {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
