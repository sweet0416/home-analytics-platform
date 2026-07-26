<template>
  <div>
    <section class="page-header decay-header">
      <div>
        <h1 class="page-title">指数衰减分析</h1>
        <div class="page-subtitle">让近期样本权重更高，观察号码短期变化和长期频率的差异</div>
      </div>
      <el-button type="primary" :loading="loading" @click="loadAnalysis">刷新分析</el-button>
    </section>

    <DltModuleNav />

    <section class="panel decay-panel">
      <div class="panel-header">
        <h2 class="panel-title">分析参数</h2>
        <span class="panel-meta">半衰期越小越看重近期，越容易受短期波动影响</span>
      </div>
      <div class="decay-form">
        <label>
          样本期数
          <el-input-number v-model="limit" :min="50" :max="2000" :step="50" />
        </label>
        <label>
          半衰期
          <el-input-number v-model="halfLife" :min="5" :max="500" :step="5" />
        </label>
        <label>
          展示数量
          <el-input-number v-model="top" :min="5" :max="20" :step="1" />
        </label>
      </div>
    </section>

    <div class="grid metrics decay-metrics">
      <MetricCard label="样本数量" :value="sampleSize" :meta="issueRange" />
      <MetricCard label="半衰期" :value="`${halfLifeValue} 期`" meta="距离越远权重越低" />
      <MetricCard label="前区有效权重" :value="frontWeight" meta="加权观察总量" />
      <MetricCard label="后区有效权重" :value="backWeight" meta="加权观察总量" />
    </div>

    <section v-if="analysis" class="panel decay-panel">
      <div class="panel-header">
        <h2 class="panel-title">快速读法</h2>
        <span class="panel-meta">{{ analysis.weight_formula }}</span>
      </div>
      <div class="reading-grid">
        <article class="reading-card">
          <strong>半衰期</strong>
          <span>半衰期 50 表示距离现在约 50 期的样本权重大约减半。</span>
        </article>
        <article class="reading-card">
          <strong>加权次数</strong>
          <span>不是实际出现次数，而是按距离现在远近折算后的历史强度。</span>
        </article>
        <article class="reading-card">
          <strong>排名变化</strong>
          <span>正数表示按近期权重看更靠前，负数表示更偏长期历史。</span>
        </article>
        <article class="reading-card">
          <strong>使用边界</strong>
          <span>它适合观察近期偏离，不表示下一期会补偿或延续。</span>
        </article>
      </div>
    </section>

    <section v-if="analysis" class="decay-grid">
      <DecayTable title="前区衰减排行" :items="analysis.front.numbers" />
      <DecayTable title="后区衰减排行" :items="analysis.back.numbers" />
      <DecayTable title="前区近期上升" :items="analysis.front.rising_numbers" />
      <DecayTable title="后区近期上升" :items="analysis.back.rising_numbers" />
    </section>

    <section v-if="analysis" class="panel decay-panel">
      <div class="panel-header">
        <h2 class="panel-title">解释与风险</h2>
        <span class="panel-meta">不要把短期偏移直接当成规律</span>
      </div>
      <ul class="note-list">
        <li v-for="note in analysis.notes" :key="note">{{ note }}</li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, defineComponent, h, onMounted, ref, type PropType } from 'vue';

import MetricCard from '@/components/metric/MetricCard.vue';
import DltModuleNav from '@/plugins/lottery/components/DltModuleNav.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import type { LotteryDecayNumber } from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const loading = ref(false);
const limit = ref(500);
const halfLife = ref(50);
const top = ref(10);

const analysis = computed(() => lottery.decayAnalysis);
const sampleSize = computed(() => String(analysis.value?.sample_size ?? 0));
const halfLifeValue = computed(() => analysis.value?.half_life ?? halfLife.value);
const issueRange = computed(() =>
  analysis.value
    ? `${analysis.value.earliest_issue_no ?? '--'} - ${analysis.value.latest_issue_no ?? '--'}`
    : '等待分析',
);
const frontWeight = computed(() =>
  analysis.value ? analysis.value.front.total_weight.toFixed(2) : '--',
);
const backWeight = computed(() =>
  analysis.value ? analysis.value.back.total_weight.toFixed(2) : '--',
);

const DecayTable = defineComponent({
  name: 'DecayTable',
  props: {
    title: { type: String, required: true },
    items: { type: Array as PropType<LotteryDecayNumber[]>, required: true },
  },
  setup(props) {
    return () =>
      h('article', { class: 'panel decay-table-panel' }, [
        h('div', { class: 'panel-header' }, [
          h('h2', { class: 'panel-title' }, props.title),
          h('span', { class: 'panel-meta' }, '衰减排行 / 普通排行对比'),
        ]),
        h('div', { class: 'decay-table' }, [
          h('div', { class: 'decay-row decay-row-head' }, [
            h('span', '号码'),
            h('span', '加权'),
            h('span', '占比'),
            h('span', '普通'),
            h('span', '衰减'),
            h('span', '变化'),
          ]),
          ...props.items.map((item) =>
            h('div', { class: 'decay-row', key: item.number }, [
              h(LotteryBall, { value: item.number, area: props.title.includes('后区') ? 'back' : 'front' }),
              h('strong', item.weighted_count.toFixed(2)),
              h('span', `${(item.weighted_share * 100).toFixed(2)}%`),
              h('span', `#${item.raw_rank}`),
              h('span', `#${item.weighted_rank}`),
              h('span', { class: rankDeltaClass(item.rank_delta) }, formatRankDelta(item.rank_delta)),
            ]),
          ),
        ]),
      ]);
  },
});

onMounted(() => {
  void loadAnalysis();
});

async function loadAnalysis(): Promise<void> {
  loading.value = true;
  try {
    await lottery.loadDecayAnalysis(limit.value, halfLife.value, top.value);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '指数衰减分析失败');
  } finally {
    loading.value = false;
  }
}

function formatRankDelta(value: number): string {
  if (value > 0) return `+${value}`;
  return String(value);
}

function rankDeltaClass(value: number): string {
  if (value > 0) return 'rank-up';
  if (value < 0) return 'rank-down';
  return 'rank-flat';
}
</script>

<style scoped>
.decay-header {
  align-items: center;
}

.decay-panel,
.decay-metrics,
.decay-grid {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.decay-form,
.reading-grid,
.decay-grid {
  display: grid;
  gap: 12px;
}

.decay-form {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.decay-form label {
  color: var(--color-muted);
  display: grid;
  font-size: 12px;
  gap: 8px;
}

.reading-grid,
.decay-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.reading-card {
  background: rgba(15, 23, 42, 0.22);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 8px;
  padding: 14px;
}

.reading-card strong {
  color: var(--color-text);
}

.reading-card span,
.note-list {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.7;
}

.decay-table-panel {
  margin: 0;
}

.decay-table {
  display: grid;
  gap: 8px;
  overflow-x: auto;
}

.decay-row {
  align-items: center;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: grid;
  gap: 16px;
  grid-template-columns: 64px 92px 92px 78px 78px 76px;
  min-width: 620px;
  padding: 8px 0;
}

.decay-row span,
.decay-row strong {
  color: var(--color-muted);
  font-size: 13px;
}

.decay-row > span,
.decay-row > strong {
  display: block;
  min-width: 0;
}

.decay-row > .lottery-ball {
  justify-self: start;
}

.decay-row-head span {
  color: var(--color-text);
  font-weight: 700;
}

.rank-up {
  color: #86efac !important;
  font-weight: 700;
}

.rank-down {
  color: #fca5a5 !important;
}

.rank-flat {
  color: var(--color-muted) !important;
}

.note-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
}

@media (max-width: 960px) {
  .reading-grid,
  .decay-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .decay-header {
    align-items: stretch;
    flex-direction: column;
  }

  .decay-form {
    grid-template-columns: 1fr;
  }
}
</style>
