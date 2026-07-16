<template>
  <div>
    <section class="page-header recommendation-header">
      <div>
        <h1 class="page-title">选号推演</h1>
        <div class="page-subtitle">基于历史同期、近期频次、遗漏和结构分布生成候选组合</div>
      </div>
      <div class="recommendation-actions">
        <RouterLink to="/lottery/dlt/same-period" class="back-link">历史同期</RouterLink>
        <RouterLink to="/lottery/dlt/statistics" class="back-link">统计分析</RouterLink>
      </div>
    </section>

    <DisclaimerAlert
      :text="lottery.recommendation?.disclaimer || '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。'"
    />

    <section class="panel recommendation-panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">推演参数</h2>
          <div class="panel-hint">默认按下一期推演，也可以输入 080 或完整期号</div>
        </div>
        <el-button type="primary" :loading="loading" @click="loadRecommendation">生成五组</el-button>
      </div>
      <div class="panel-body controls-grid">
        <el-input v-model="issueInput" clearable placeholder="期号后三位或完整期号，例如 080" />
        <el-input-number v-model="setCount" :min="1" :max="12" />
        <el-input-number v-model="samePeriodCount" :min="1" :max="20" />
        <el-input-number v-model="sampleLimit" :min="50" :max="500" :step="50" />
        <div class="control-caption">候选组数</div>
        <div class="control-caption">历史同期数</div>
        <div class="control-caption">近期样本数</div>
      </div>
    </section>

    <section v-if="lottery.recommendation" class="grid metrics recommendation-metrics">
      <MetricCard
        label="目标期号"
        :value="lottery.recommendation.target_issue_no"
        :meta="`同期尾号 ${lottery.recommendation.issue_suffix}`"
      />
      <MetricCard
        label="同期样本"
        :value="String(lottery.recommendation.same_period_count)"
        :meta="`近期样本 ${lottery.recommendation.sample_size} 期`"
      />
      <MetricCard
        label="生成组数"
        :value="String(lottery.recommendation.recommendations.length)"
        meta="每组含完整依据"
      />
    </section>

    <section v-if="lottery.recommendation" class="panel recommendation-panel">
      <div class="panel-header">
        <h2 class="panel-title">历史同期重复号</h2>
        <span class="table-meta">按同期出现次数和综合分排序</span>
      </div>
      <div class="panel-body repeated-layout">
        <NumberScoreList
          title="前区重复号"
          :items="lottery.recommendation.same_period_repeated_front"
        />
        <NumberScoreList
          title="后区重复号"
          :items="lottery.recommendation.same_period_repeated_back"
          area="back"
        />
      </div>
    </section>

    <section v-if="lottery.recommendation" class="recommendation-list">
      <article
        v-for="item in lottery.recommendation.recommendations"
        :key="item.rank"
        class="recommendation-card"
      >
        <div class="recommendation-card-header">
          <div>
            <h2>第 {{ item.rank }} 组</h2>
            <span>综合分 {{ item.score.toFixed(2) }}</span>
          </div>
          <div class="structure-tags">
            <el-tag size="small">和值 {{ item.front_sum }}</el-tag>
            <el-tag size="small">跨度 {{ item.front_span }}</el-tag>
            <el-tag size="small">奇偶 {{ item.front_parity_pattern }}</el-tag>
            <el-tag size="small">三区 {{ item.front_zone_pattern }}</el-tag>
            <el-tag size="small">012路 {{ item.front_route012_pattern }}</el-tag>
          </div>
        </div>

        <div class="number-row">
          <LotteryBall
            v-for="number in item.front_numbers"
            :key="`front-${item.rank}-${number}`"
            :value="number"
            area="front"
          />
          <LotteryBall
            v-for="number in item.back_numbers"
            :key="`back-${item.rank}-${number}`"
            :value="number"
            area="back"
          />
        </div>

        <div class="rationale-box">
          <h3>依据说明</h3>
          <ul>
            <li v-for="reason in item.rationale" :key="reason">{{ reason }}</li>
          </ul>
        </div>

        <div class="detail-grid">
          <NumberScoreList title="前区号码依据" :items="item.front_details" compact />
          <NumberScoreList title="后区号码依据" :items="item.back_details" area="back" compact />
        </div>
      </article>
    </section>

    <EmptyState
      v-if="!loading && !lottery.recommendation"
      title="暂无选号推演"
      description="点击生成五组后，将根据历史同期和近期统计生成候选组合。"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref, type PropType } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/common/MetricCard.vue';

import type { LotteryRecommendationNumber } from '../api';
import DisclaimerAlert from '../components/DisclaimerAlert.vue';
import LotteryBall from '../components/LotteryBall.vue';
import { useLotteryStore } from '../store';

const lottery = useLotteryStore();
const loading = ref(false);
const issueInput = ref('');
const setCount = ref(5);
const samePeriodCount = ref(10);
const sampleLimit = ref(200);

const normalizedIssueInput = computed(() => {
  const value = issueInput.value.trim();
  return value.length ? value : undefined;
});

async function loadRecommendation(): Promise<void> {
  loading.value = true;
  try {
    await lottery.loadRecommendation(
      normalizedIssueInput.value,
      setCount.value,
      samePeriodCount.value,
      sampleLimit.value,
    );
  } finally {
    loading.value = false;
  }
}

const NumberScoreList = defineComponent({
  props: {
    title: { type: String, required: true },
    items: {
      type: Array as PropType<LotteryRecommendationNumber[]>,
      required: true,
    },
    area: {
      type: String as PropType<'front' | 'back'>,
      default: 'front',
    },
    compact: { type: Boolean, default: false },
  },
  setup(props) {
    return () =>
      h('div', { class: ['number-score-list', { compact: props.compact }] }, [
        h('h3', props.title),
        h(
          'div',
          { class: 'number-score-items' },
          props.items.map((item) =>
            h('div', { class: 'number-score-item', key: item.number }, [
              h(LotteryBall, { value: item.number, area: props.area }),
              h('div', [
                h('strong', item.score.toFixed(1)),
                h(
                  'small',
                  [
                    `同期 ${item.same_period_hits}`,
                    `频次 ${item.recent_frequency}`,
                    `遗漏 ${item.current_missing}`,
                  ].join(' · '),
                ),
              ]),
            ]),
          ),
        ),
      ]);
  },
});

onMounted(() => {
  void loadRecommendation();
});
</script>

<style scoped>
.recommendation-header {
  gap: 16px;
}

.recommendation-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.recommendation-panel,
.recommendation-metrics {
  margin-top: 16px;
}

.panel-hint {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 12px;
}

.controls-grid {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) repeat(3, 150px);
  gap: 10px;
}

.control-caption {
  color: var(--color-muted);
  font-size: 12px;
}

.repeated-layout,
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.recommendation-list {
  display: grid;
  gap: 16px;
  margin-top: 16px;
}

.recommendation-card {
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.52);
  padding: 16px;
}

.recommendation-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.recommendation-card-header h2 {
  margin: 0;
  font-size: 18px;
}

.recommendation-card-header span {
  color: var(--color-muted);
  font-size: 13px;
}

.structure-tags {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.number-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin: 16px 0;
}

.rationale-box {
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 8px;
  background: rgba(56, 189, 248, 0.08);
  margin-bottom: 14px;
  padding: 12px 14px;
}

.rationale-box h3,
.number-score-list h3 {
  margin: 0 0 8px;
  color: var(--color-text);
  font-size: 14px;
}

.rationale-box ul {
  margin: 0;
  padding-left: 18px;
  color: var(--color-muted);
  line-height: 1.7;
}

.number-score-list {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.34);
  padding: 12px;
}

.number-score-list.compact {
  padding: 10px;
}

.number-score-items {
  display: grid;
  gap: 8px;
}

.number-score-item {
  display: flex;
  align-items: center;
  gap: 9px;
}

.number-score-item strong {
  display: block;
  color: var(--color-text);
}

.number-score-item small {
  display: block;
  color: var(--color-muted);
  font-size: 12px;
}

@media (max-width: 920px) {
  .controls-grid,
  .repeated-layout,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .recommendation-card-header {
    display: grid;
  }

  .structure-tags {
    justify-content: flex-start;
  }
}
</style>
