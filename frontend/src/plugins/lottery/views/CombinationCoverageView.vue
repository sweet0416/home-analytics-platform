<template>
  <div>
    <section class="page-header coverage-header">
      <div>
        <h1 class="page-title">组合覆盖</h1>
        <div class="page-subtitle">
          检查多组号码的分散度、重复率和覆盖结构，不用于预测未来开奖
        </div>
      </div>
      <div class="coverage-actions">
        <el-button plain @click="resetDefaults">恢复默认</el-button>
        <el-button type="primary" :loading="loading" @click="runAnalysis">分析覆盖</el-button>
      </div>
    </section>

    <DltModuleNav />

    <DisclaimerAlert
      :text="lottery.combinationCoverage?.disclaimer ?? fallbackDisclaimer"
      class="coverage-alert"
    />

    <section class="panel coverage-panel">
      <div class="panel-header">
        <h2 class="panel-title">组合输入</h2>
        <span class="panel-meta">选择一组后点击数字球；至少保留 2 组</span>
      </div>
      <div class="workspace">
        <div class="set-list">
          <article
            v-for="(item, index) in combinations"
            :key="item.id"
            class="set-row"
            :class="{ active: activeIndex === index }"
            @click="activeIndex = index"
          >
            <div class="set-title">
              <strong>第 {{ index + 1 }} 组</strong>
              <el-button
                text
                size="small"
                :disabled="combinations.length <= 2"
                @click.stop="removeCombination(index)"
              >
                删除
              </el-button>
            </div>
            <div class="number-line">
              <span>前区</span>
              <LotteryBall
                v-for="number in item.frontNumbers"
                :key="`front-${item.id}-${number}`"
                area="front"
                :value="number"
              />
            </div>
            <div class="number-line">
              <span>后区</span>
              <LotteryBall
                v-for="number in item.backNumbers"
                :key="`back-${item.id}-${number}`"
                area="back"
                :value="number"
              />
            </div>
          </article>
          <el-button plain class="add-button" :disabled="combinations.length >= 20" @click="addCombination">
            添加组合
          </el-button>
        </div>

        <div class="picker-panel">
          <div class="picker-header">
            <strong>编辑第 {{ activeIndex + 1 }} 组</strong>
            <span>前区 {{ activeCombination.frontNumbers.length }}/5，后区 {{ activeCombination.backNumbers.length }}/2</span>
          </div>
          <div class="picker-block">
            <span class="picker-label">前区</span>
            <button
              v-for="number in frontNumbers"
              :key="`pick-front-${number}`"
              class="pick-ball front"
              :class="{ selected: activeCombination.frontNumbers.includes(number) }"
              @click="toggleNumber('front', number)"
            >
              {{ formatNumber(number) }}
            </button>
          </div>
          <div class="picker-block">
            <span class="picker-label">后区</span>
            <button
              v-for="number in backNumbers"
              :key="`pick-back-${number}`"
              class="pick-ball back"
              :class="{ selected: activeCombination.backNumbers.includes(number) }"
              @click="toggleNumber('back', number)"
            >
              {{ formatNumber(number) }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <div class="grid metrics coverage-metrics">
      <MetricCard label="组合数量" :value="setCount" meta="参与分析" />
      <MetricCard label="前区覆盖" :value="frontCoverage" :meta="`${frontUnique} / 35`" />
      <MetricCard label="后区覆盖" :value="backCoverage" :meta="`${backUnique} / 12`" />
      <MetricCard label="最高相似" :value="maxJaccard" meta="Jaccard 越低越分散" />
    </div>

    <section v-if="analysis" class="panel coverage-panel">
      <div class="panel-header">
        <h2 class="panel-title">覆盖结构</h2>
        <span class="panel-meta">最大熵只衡量分散度，不改变单注概率</span>
      </div>
      <div class="coverage-grid">
        <InfoBlock label="前区重复位" :value="String(analysis.front_duplicate_slots)" meta="越少越分散" />
        <InfoBlock label="后区重复位" :value="String(analysis.back_duplicate_slots)" meta="后区更容易重复" />
        <InfoBlock label="前区熵" :value="formatPercent(analysis.front_entropy.normalized)" meta="相对 1-35" />
        <InfoBlock label="后区熵" :value="formatPercent(analysis.back_entropy.normalized)" meta="相对 1-12" />
        <InfoBlock label="三区覆盖" :value="zoneSummary" meta="1-12 / 13-24 / 25-35" />
        <InfoBlock label="尾数覆盖" :value="tailSummary" meta="不同尾数数量" />
        <InfoBlock label="奇偶结构" :value="paritySummary" meta="前区 / 后区" />
        <InfoBlock label="大小结构" :value="sizeSummary" meta="前区 / 后区" />
      </div>
    </section>

    <section v-if="analysis?.combinations.length" class="panel coverage-panel">
      <div class="panel-header">
        <h2 class="panel-title">组合明细</h2>
        <span class="panel-meta">逐组查看基础结构</span>
      </div>
      <div class="result-list">
        <article v-for="item in analysis.combinations" :key="item.rank" class="result-row">
          <span class="result-rank">第 {{ item.rank }} 组</span>
          <div class="number-line">
            <span>前区</span>
            <LotteryBall
              v-for="number in item.front_numbers"
              :key="`result-front-${item.rank}-${number}`"
              area="front"
              :value="number"
            />
            <span class="back-label">后区</span>
            <LotteryBall
              v-for="number in item.back_numbers"
              :key="`result-back-${item.rank}-${number}`"
              area="back"
              :value="number"
            />
          </div>
          <div class="pattern-row">
            <span>和值 {{ item.front_sum }}</span>
            <span>跨度 {{ item.front_span }}</span>
            <span>最小间距 {{ item.front_min_distance }}</span>
            <span>奇偶 {{ item.front_parity_pattern }}</span>
            <span>区间 {{ item.front_zone_pattern }}</span>
          </div>
        </article>
      </div>
    </section>

    <section v-if="topSimilarities.length" class="panel coverage-panel">
      <div class="panel-header">
        <h2 class="panel-title">相似度最高</h2>
        <span class="panel-meta">优先检查这些组合是否太像</span>
      </div>
      <div class="similarity-table">
        <div class="similarity-row table-head">
          <span>组合</span>
          <span>前区重合</span>
          <span>后区重合</span>
          <span>综合 Jaccard</span>
        </div>
        <div v-for="item in topSimilarities" :key="`${item.left_rank}-${item.right_rank}`" class="similarity-row">
          <span>第 {{ item.left_rank }} 组 + 第 {{ item.right_rank }} 组</span>
          <span>{{ item.front_overlap }}</span>
          <span>{{ item.back_overlap }}</span>
          <span>{{ item.combined_jaccard }}</span>
        </div>
      </div>
    </section>

    <LotteryExplanationPanel
      title="组合覆盖说明"
      subtitle="通俗版"
      :sections="explanationSections"
    />
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, defineComponent, h, ref } from 'vue';

import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import DltModuleNav from '@/plugins/lottery/components/DltModuleNav.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import LotteryExplanationPanel, {
  type LotteryExplanationSection,
} from '@/plugins/lottery/components/LotteryExplanationPanel.vue';
import { useLotteryStore } from '@/plugins/lottery/store';

type Area = 'front' | 'back';

interface EditableCombination {
  id: string;
  frontNumbers: number[];
  backNumbers: number[];
}

const defaultCombinations: EditableCombination[] = [
  { id: 'default-1', frontNumbers: [3, 9, 16, 22, 31], backNumbers: [4, 9] },
  { id: 'default-2', frontNumbers: [5, 11, 18, 26, 34], backNumbers: [2, 11] },
  { id: 'default-3', frontNumbers: [1, 13, 20, 27, 35], backNumbers: [6, 12] },
  { id: 'default-4', frontNumbers: [7, 14, 21, 28, 32], backNumbers: [1, 8] },
  { id: 'default-5', frontNumbers: [2, 10, 17, 24, 30], backNumbers: [3, 10] },
];

const lottery = useLotteryStore();
const fallbackDisclaimer = '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。';
const frontNumbers = Array.from({ length: 35 }, (_, index) => index + 1);
const backNumbers = Array.from({ length: 12 }, (_, index) => index + 1);
const combinations = ref<EditableCombination[]>(cloneDefaults());
const activeIndex = ref(0);
const loading = ref(false);

const analysis = computed(() => lottery.combinationCoverage);
const activeCombination = computed(() => combinations.value[activeIndex.value] ?? combinations.value[0]);
const setCount = computed(() => String(analysis.value?.set_count ?? combinations.value.length));
const frontUnique = computed(() => String(analysis.value?.front_unique_count ?? '--'));
const backUnique = computed(() => String(analysis.value?.back_unique_count ?? '--'));
const frontCoverage = computed(() =>
  analysis.value ? formatPercent(analysis.value.front_coverage_rate) : '--',
);
const backCoverage = computed(() =>
  analysis.value ? formatPercent(analysis.value.back_coverage_rate) : '--',
);
const maxJaccard = computed(() => String(analysis.value?.max_jaccard ?? '--'));
const topSimilarities = computed(() => analysis.value?.pairwise_similarity.slice(0, 8) ?? []);
const zoneSummary = computed(() => {
  const value = analysis.value?.zone_coverage;
  return value ? `${value.zone_1_12}/${value.zone_13_24}/${value.zone_25_35}` : '--';
});
const tailSummary = computed(() => {
  const value = analysis.value?.tail_coverage;
  return value ? `前 ${value.front_unique_tails} / 后 ${value.back_unique_tails}` : '--';
});
const paritySummary = computed(() => {
  const value = analysis.value?.parity_coverage;
  return value ? `${value.front_odd}:${value.front_even} / ${value.back_odd}:${value.back_even}` : '--';
});
const sizeSummary = computed(() => {
  const value = analysis.value?.size_coverage;
  return value ? `${value.front_small}:${value.front_large} / ${value.back_small}:${value.back_large}` : '--';
});
const explanationSections = computed<LotteryExplanationSection[]>(() => [
  {
    title: '它解决什么',
    items: [
      '多组号码如果大量重复，看起来买了很多组，实际覆盖面可能很窄。',
      '组合覆盖会把这些号码当作样本集合，检查它们是否足够分散。',
      '这适合在选号推荐、模拟选号、胆拖结果之后做二次体检。',
    ],
  },
  {
    title: '指标怎么看',
    items: [
      '覆盖率表示这批组合触达了多少不同号码；重复位表示号码被反复占用的槽位。',
      'Jaccard 表示两组号码有多相似，越高越像，越低越分散。',
      '熵越高说明分布越分散，但样本组数少时不要过度解读。',
    ],
  },
  {
    title: '不要误读',
    items: [
      '最大熵不能提高单注中奖概率，只能帮助观察多组组合的覆盖结构。',
      '覆盖面更广不等于更容易中奖，只代表这批样本更分散。',
      '它应和历史回放、随机基准、组合回测一起看，避免只凭感觉判断。',
    ],
  },
]);

const InfoBlock = defineComponent({
  name: 'InfoBlock',
  props: {
    label: { type: String, required: true },
    value: { type: String, required: true },
    meta: { type: String, required: true },
  },
  setup(props) {
    return () =>
      h('div', { class: 'info-block' }, [
        h('span', props.label),
        h('strong', props.value),
        h('small', props.meta),
      ]);
  },
});

function cloneDefaults(): EditableCombination[] {
  return defaultCombinations.map((item) => ({
    id: `${item.id}-${Date.now()}`,
    frontNumbers: [...item.frontNumbers],
    backNumbers: [...item.backNumbers],
  }));
}

function formatNumber(value: number): string {
  return String(value).padStart(2, '0');
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function toggleNumber(area: Area, number: number): void {
  const item = activeCombination.value;
  const key = area === 'front' ? 'frontNumbers' : 'backNumbers';
  const limit = area === 'front' ? 5 : 2;
  const current = item[key];
  if (current.includes(number)) {
    item[key] = current.filter((value) => value !== number);
    return;
  }
  if (current.length >= limit) {
    ElMessage.warning(`${area === 'front' ? '前区' : '后区'}最多选择 ${limit} 个号码`);
    return;
  }
  item[key] = [...current, number].sort((left, right) => left - right);
}

function addCombination(): void {
  combinations.value.push({
    id: `custom-${Date.now()}`,
    frontNumbers: [],
    backNumbers: [],
  });
  activeIndex.value = combinations.value.length - 1;
}

function removeCombination(index: number): void {
  if (combinations.value.length <= 2) return;
  combinations.value.splice(index, 1);
  activeIndex.value = Math.min(activeIndex.value, combinations.value.length - 1);
}

function resetDefaults(): void {
  combinations.value = cloneDefaults();
  activeIndex.value = 0;
  lottery.combinationCoverage = null;
}

async function runAnalysis(): Promise<void> {
  const invalidIndex = combinations.value.findIndex(
    (item) => item.frontNumbers.length !== 5 || item.backNumbers.length !== 2,
  );
  if (invalidIndex >= 0) {
    activeIndex.value = invalidIndex;
    ElMessage.warning(`第 ${invalidIndex + 1} 组需要选择 5 个前区和 2 个后区`);
    return;
  }
  loading.value = true;
  try {
    await lottery.analyzeCombinationCoverage({
      combinations: combinations.value.map((item) => ({
        front_numbers: item.frontNumbers,
        back_numbers: item.backNumbers,
      })),
    });
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '组合覆盖分析失败');
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.coverage-header,
.coverage-actions {
  align-items: center;
}

.coverage-actions {
  display: flex;
  flex-shrink: 0;
  gap: 10px;
}

.coverage-alert,
.coverage-panel,
.coverage-metrics {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.workspace {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.1fr);
}

.set-list,
.result-list {
  display: grid;
  gap: 10px;
}

.set-row,
.result-row {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  cursor: pointer;
  display: grid;
  gap: 8px;
  padding: 12px;
}

.set-row.active {
  background: rgba(34, 211, 238, 0.08);
  border-color: rgba(34, 211, 238, 0.42);
}

.set-title,
.picker-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.set-title strong,
.picker-header strong,
.result-rank {
  color: var(--color-text);
}

.picker-header span,
.number-line span,
.pattern-row span {
  color: var(--color-muted);
  font-size: 12px;
}

.number-line,
.pattern-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.back-label {
  margin-left: 8px;
}

.add-button {
  width: 100%;
}

.picker-panel {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 14px;
  padding: 14px;
}

.picker-block {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.picker-label {
  color: var(--color-muted);
  flex-basis: 100%;
  font-size: 12px;
}

.pick-ball {
  border-radius: 999px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 750;
  height: 28px;
  width: 28px;
}

.pick-ball.front {
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.22);
  color: #7dd3fc;
}

.pick-ball.back {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.24);
  color: #fbbf24;
}

.pick-ball.selected {
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.08), 0 0 18px rgba(34, 211, 238, 0.22);
  transform: translateY(-1px);
}

.coverage-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.info-block {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 12px;
}

.info-block span,
.info-block small {
  color: var(--color-muted);
  font-size: 12px;
}

.info-block strong {
  color: var(--color-text);
  font-size: 18px;
}

.similarity-table {
  display: grid;
  gap: 8px;
}

.similarity-row {
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  display: grid;
  gap: 8px;
  grid-template-columns: 1.5fr repeat(3, 0.8fr);
  padding: 10px 12px;
}

.similarity-row span {
  color: var(--color-muted);
  font-size: 13px;
}

.table-head {
  background: rgba(15, 23, 42, 0.45);
  font-weight: 700;
}

@media (max-width: 900px) {
  .coverage-header,
  .coverage-actions,
  .set-title,
  .picker-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .workspace,
  .coverage-grid {
    grid-template-columns: 1fr;
  }

  .similarity-row {
    grid-template-columns: 1fr;
  }
}
</style>
