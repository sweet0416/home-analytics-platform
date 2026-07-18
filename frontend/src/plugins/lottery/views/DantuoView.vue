<template>
  <div>
    <section class="page-header dantuo-header">
      <div>
        <h1 class="page-title">胆拖辅助</h1>
        <div class="page-subtitle">点击号码生成胆码、拖码、杀号方案，并计算注数、成本和组合预览</div>
      </div>
      <div class="dantuo-actions">
        <el-checkbox v-model="form.addon">追加投注</el-checkbox>
        <el-input-number v-model="form.previewLimit" :min="1" :max="200" size="small" />
        <el-button type="primary" :loading="analyzing" @click="handleAnalyze">计算方案</el-button>
      </div>
    </section>

    <DisclaimerAlert :text="lottery.dantuo?.disclaimer ?? fallbackDisclaimer" />

    <el-alert
      v-if="errorMessage"
      class="dantuo-alert"
      type="warning"
      :title="errorMessage"
      :closable="false"
      show-icon
    />

    <section class="panel random-panel">
      <div class="panel-header">
        <h2 class="panel-title">历史随机生成</h2>
        <span class="panel-meta">按历史同期、近期热度和遗漏分数随机填入胆/拖，已选杀号会自动避开</span>
      </div>
      <div class="random-grid">
        <div class="random-item">
          <span>前区胆码</span>
          <el-input-number v-model="randomForm.frontDanCount" :min="0" :max="4" size="small" />
        </div>
        <div class="random-item">
          <span>前区拖码</span>
          <el-input-number v-model="randomForm.frontTuoCount" :min="1" :max="20" size="small" />
        </div>
        <div class="random-item">
          <span>后区胆码</span>
          <el-input-number v-model="randomForm.backDanCount" :min="0" :max="1" size="small" />
        </div>
        <div class="random-item">
          <span>后区拖码</span>
          <el-input-number v-model="randomForm.backTuoCount" :min="1" :max="10" size="small" />
        </div>
        <div class="random-item">
          <span>历史同期</span>
          <el-input-number v-model="randomForm.samePeriodCount" :min="1" :max="20" size="small" />
        </div>
        <div class="random-item">
          <span>近期样本</span>
          <el-input-number
            v-model="randomForm.sampleLimit"
            :min="50"
            :max="500"
            :step="50"
            size="small"
          />
        </div>
      </div>
      <div class="random-options">
        <el-checkbox v-model="randomForm.keepManualKill">保留杀号</el-checkbox>
        <el-checkbox v-model="randomForm.autoAnalyze">生成后自动计算</el-checkbox>
        <el-button type="primary" plain :loading="randomizing" @click="handleRandomDantuo">
          按历史数据随机
        </el-button>
      </div>
      <div class="random-hints">
        <span>建议：前区 1-2 胆 + 7-12 拖，后区 0-1 胆 + 3-6 拖。</span>
        <span>条件：前区胆+拖至少 5 个，后区胆+拖至少 2 个，胆和拖不会重复。</span>
      </div>
    </section>

    <section class="panel picker-panel">
      <div class="panel-header">
        <h2 class="panel-title">选号输入</h2>
        <span class="panel-meta">先选择要编辑的分组，再点击下方号码</span>
      </div>

      <div class="target-grid">
        <button
          v-for="target in selectionTargets"
          :key="`${target.area}-${target.bucket}`"
          type="button"
          class="target-button"
          :class="{ active: activeArea === target.area && activeBucket === target.bucket }"
          @click="setActiveTarget(target.area, target.bucket)"
        >
          <span>{{ target.label }}</span>
          <strong>{{ selectedCount(target.area, target.bucket) }}</strong>
          <small>{{ target.hint }}</small>
        </button>
      </div>

      <div class="number-board">
        <div class="board-header">
          <div>
            <h3>{{ activeAreaLabel }}号码</h3>
            <span>{{ activeTargetLabel }}：点击数字加入，再点一次移除</span>
          </div>
          <el-button plain size="small" @click="clearActiveBucket">清空当前分组</el-button>
        </div>
        <LotteryNumberBoard
          :area="activeArea"
          :numbers="activeNumbers"
          :columns="12"
          :tablet-columns="8"
          :mobile-columns="6"
          :classes-for-number="numberButtonClass"
          @toggle="toggleNumber"
        />
      </div>

      <div class="selected-grid">
        <PoolBlock title="前区胆码" area="front" :numbers="form.frontDan" />
        <PoolBlock title="前区拖码" area="front" :numbers="form.frontTuo" />
        <PoolBlock title="前区杀号" area="front" :numbers="form.frontKill" muted />
        <PoolBlock title="后区胆码" area="back" :numbers="form.backDan" />
        <PoolBlock title="后区拖码" area="back" :numbers="form.backTuo" />
        <PoolBlock title="后区杀号" area="back" :numbers="form.backKill" muted />
      </div>
    </section>

    <div class="grid metrics dantuo-metrics">
      <MetricCard label="总注数" :value="totalBets" meta="前区组合 x 后区组合" />
      <MetricCard label="普通成本" :value="baseCost" meta="每注 2 元" />
      <MetricCard label="追加成本" :value="addonCost" meta="追加每注 1 元" />
      <MetricCard label="合计成本" :value="totalCost" meta="本方案预算" />
    </div>

    <section v-if="lottery.dantuo" class="panel summary-panel">
      <div class="panel-header">
        <h2 class="panel-title">快速汇总</h2>
        <span class="panel-meta">{{ combinationSummary }}</span>
      </div>
      <div class="summary-grid">
        <PoolBlock title="前区胆码" area="front" :numbers="lottery.dantuo.front_dan" />
        <PoolBlock title="前区拖码" area="front" :numbers="lottery.dantuo.front_tuo" />
        <PoolBlock title="前区杀号" area="front" :numbers="lottery.dantuo.front_kill" muted />
        <PoolBlock title="后区胆码" area="back" :numbers="lottery.dantuo.back_dan" />
        <PoolBlock title="后区拖码" area="back" :numbers="lottery.dantuo.back_tuo" />
        <PoolBlock title="后区杀号" area="back" :numbers="lottery.dantuo.back_kill" muted />
      </div>
    </section>

    <section v-if="lottery.dantuo" class="panel preview-panel">
      <div class="panel-header">
        <h2 class="panel-title">组合预览</h2>
        <span class="panel-meta">最多展示 {{ lottery.dantuo.preview_limit }} 注</span>
      </div>
      <div v-if="lottery.dantuo.preview.length" class="preview-list">
        <div v-for="item in lottery.dantuo.preview" :key="item.rank" class="preview-row">
          <span class="preview-rank">#{{ item.rank }}</span>
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
          <span class="preview-meta">
            和值 {{ item.front_sum }} / 跨度 {{ item.front_span }} / {{ item.front_parity_pattern }}
          </span>
        </div>
      </div>
      <EmptyState
        v-else
        title="暂无组合"
        description="输入有效的胆码和拖码后，系统会展开可预览的组合。"
      />
    </section>

    <LotteryExplanationPanel
      v-if="lottery.dantuo"
      title="计算说明"
      subtitle="通俗解释"
      :sections="explanationSections"
    />

    <EmptyState
      v-if="!lottery.dantuo"
      class="dantuo-empty"
      title="先点击选择一组胆码和拖码"
      description="比如前区 1-2 个胆码、6-10 个拖码；后区 0-1 个胆码、3-5 个拖码。"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, reactive, ref } from 'vue';
import type { PropType } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import LotteryExplanationPanel, {
  type LotteryExplanationSection,
} from '@/plugins/lottery/components/LotteryExplanationPanel.vue';
import LotteryNumberBoard from '@/plugins/lottery/components/LotteryNumberBoard.vue';
import {
  fetchRecommendationAnalysis,
  type LotteryRecommendationNumberDetail,
} from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

type Area = 'front' | 'back';
type Bucket = 'dan' | 'tuo' | 'kill';

interface SelectionTarget {
  area: Area;
  bucket: Bucket;
  label: string;
  hint: string;
}

interface WeightedNumber {
  number: number;
  weight: number;
}

const lottery = useLotteryStore();
const analyzing = ref(false);
const randomizing = ref(false);
const errorMessage = ref('');
const activeArea = ref<Area>('front');
const activeBucket = ref<Bucket>('dan');
const fallbackDisclaimer = '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。';

const form = reactive({
  frontDan: [] as number[],
  frontTuo: [] as number[],
  frontKill: [] as number[],
  backDan: [] as number[],
  backTuo: [] as number[],
  backKill: [] as number[],
  addon: false,
  previewLimit: 20,
});

const randomForm = reactive({
  frontDanCount: 1,
  frontTuoCount: 9,
  backDanCount: 1,
  backTuoCount: 4,
  samePeriodCount: 10,
  sampleLimit: 200,
  keepManualKill: true,
  autoAnalyze: true,
});

const selectionTargets: SelectionTarget[] = [
  { area: 'front', bucket: 'dan', label: '前区胆码', hint: '最多 4 个' },
  { area: 'front', bucket: 'tuo', label: '前区拖码', hint: '补足 5 个前区' },
  { area: 'front', bucket: 'kill', label: '前区杀号', hint: '从前区排除' },
  { area: 'back', bucket: 'dan', label: '后区胆码', hint: '最多 1 个' },
  { area: 'back', bucket: 'tuo', label: '后区拖码', hint: '补足 2 个后区' },
  { area: 'back', bucket: 'kill', label: '后区杀号', hint: '从后区排除' },
];

const totalBets = computed(() => String(lottery.dantuo?.total_bets ?? 0));
const baseCost = computed(() => formatCurrency(lottery.dantuo?.base_cost ?? 0));
const addonCost = computed(() => formatCurrency(lottery.dantuo?.addon_cost ?? 0));
const totalCost = computed(() => formatCurrency(lottery.dantuo?.total_cost ?? 0));
const activeNumbers = computed(() =>
  activeArea.value === 'front'
    ? Array.from({ length: 35 }, (_, index) => index + 1)
    : Array.from({ length: 12 }, (_, index) => index + 1),
);
const activeAreaLabel = computed(() => (activeArea.value === 'front' ? '前区' : '后区'));
const activeTargetLabel = computed(
  () =>
    selectionTargets.find(
      (target) => target.area === activeArea.value && target.bucket === activeBucket.value,
    )?.label ?? '',
);
const combinationSummary = computed(() => {
  const result = lottery.dantuo;
  if (!result) return '--';
  return `前区 ${result.front_combination_count} 种 x 后区 ${result.back_combination_count} 种`;
});
const explanationSections = computed<LotteryExplanationSection[]>(() => {
  const result = lottery.dantuo;
  return [
    {
      title: '怎么算出来的',
      items: result?.methodology.length
        ? result.methodology
        : [
            '胆码会固定出现在每一注里，拖码会参与组合展开。',
            '系统按前区组合数乘以后区组合数计算总注数。',
            '追加投注会在普通投注成本基础上按每注增加 1 元计算。',
          ],
    },
    {
      title: '历史随机怎么理解',
      items: [
        '历史随机会参考历史同期、近期热度和遗漏分数，再随机挑出胆、拖号码。',
        '已选择的杀号会自动避开，避免生成后又被你手动排除。',
        '前区会尽量避免号码过度集中在同一个区间，后区会避免胆拖重复。',
      ],
    },
    {
      title: '风险提醒',
      items: result?.warnings.length
        ? result.warnings
        : ['当前方案结构正常，但任何历史统计都不能代表未来开奖结果。'],
    },
  ];
});

async function handleAnalyze(): Promise<void> {
  errorMessage.value = '';
  analyzing.value = true;
  try {
    await lottery.analyzeDantuo({
      front_dan: [...form.frontDan],
      front_tuo: [...form.frontTuo],
      front_kill: [...form.frontKill],
      back_dan: [...form.backDan],
      back_tuo: [...form.backTuo],
      back_kill: [...form.backKill],
      addon: form.addon,
      preview_limit: form.previewLimit,
    });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '胆拖方案计算失败';
  } finally {
    analyzing.value = false;
  }
}

async function handleRandomDantuo(): Promise<void> {
  errorMessage.value = '';
  const validationMessage = validateRandomForm();
  if (validationMessage) {
    errorMessage.value = validationMessage;
    return;
  }

  randomizing.value = true;
  try {
    const analysis = await fetchRecommendationAnalysis(
      undefined,
      8,
      randomForm.samePeriodCount,
      randomForm.sampleLimit,
    );
    const frontWeightedNumbers = buildWeightedNumbers(
      'front',
      35,
      randomForm.keepManualKill ? form.frontKill : [],
      analysis.same_period_repeated_front,
      analysis.recommendations.flatMap((item) => item.front_details),
    );
    const backWeightedNumbers = buildWeightedNumbers(
      'back',
      12,
      randomForm.keepManualKill ? form.backKill : [],
      analysis.same_period_repeated_back,
      analysis.recommendations.flatMap((item) => item.back_details),
    );

    const frontNumbers = pickBalancedFrontNumbers(
      frontWeightedNumbers,
      randomForm.frontDanCount + randomForm.frontTuoCount,
    );
    const backNumbers = pickWeightedNumbers(
      backWeightedNumbers,
      randomForm.backDanCount + randomForm.backTuoCount,
    );

    form.frontDan = frontNumbers.slice(0, randomForm.frontDanCount).sort(sortNumbers);
    form.frontTuo = frontNumbers.slice(randomForm.frontDanCount).sort(sortNumbers);
    form.backDan = backNumbers.slice(0, randomForm.backDanCount).sort(sortNumbers);
    form.backTuo = backNumbers.slice(randomForm.backDanCount).sort(sortNumbers);
    if (!randomForm.keepManualKill) {
      form.frontKill = [];
      form.backKill = [];
    }
    activeArea.value = 'front';
    activeBucket.value = 'dan';
    if (randomForm.autoAnalyze) {
      await handleAnalyze();
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '历史随机生成失败';
  } finally {
    randomizing.value = false;
  }
}

function validateRandomForm(): string {
  const frontKillCount = randomForm.keepManualKill ? form.frontKill.length : 0;
  const backKillCount = randomForm.keepManualKill ? form.backKill.length : 0;
  if (randomForm.frontDanCount + randomForm.frontTuoCount < 5) {
    return '前区胆码和拖码合计至少需要 5 个。';
  }
  if (randomForm.backDanCount + randomForm.backTuoCount < 2) {
    return '后区胆码和拖码合计至少需要 2 个。';
  }
  if (randomForm.frontDanCount + randomForm.frontTuoCount > 35 - frontKillCount) {
    return '前区可选号码不足，请减少胆码/拖码数量或清理部分杀号。';
  }
  if (randomForm.backDanCount + randomForm.backTuoCount > 12 - backKillCount) {
    return '后区可选号码不足，请减少胆码/拖码数量或清理部分杀号。';
  }
  return '';
}

function setActiveTarget(area: Area, bucket: Bucket): void {
  activeArea.value = area;
  activeBucket.value = bucket;
  errorMessage.value = '';
}

function toggleNumber(number: number): void {
  errorMessage.value = '';
  const current = getBucket(activeArea.value, activeBucket.value);
  if (current.includes(number)) {
    setBucket(activeArea.value, activeBucket.value, current.filter((item) => item !== number));
    return;
  }

  if (activeBucket.value === 'dan') {
    const limit = activeArea.value === 'front' ? 4 : 1;
    if (current.length >= limit) {
      errorMessage.value =
        activeArea.value === 'front' ? '前区胆码最多选择 4 个。' : '后区胆码最多选择 1 个。';
      return;
    }
  }

  removeFromArea(activeArea.value, number);
  setBucket(activeArea.value, activeBucket.value, [...current, number].sort((a, b) => a - b));
}

function clearActiveBucket(): void {
  setBucket(activeArea.value, activeBucket.value, []);
  errorMessage.value = '';
}

function selectedCount(area: Area, bucket: Bucket): string {
  return String(getBucket(area, bucket).length);
}

function numberButtonClass(number: number): string[] {
  const bucket = bucketForNumber(activeArea.value, number);
  return [
    bucket !== null ? 'selected' : '',
    bucket === activeBucket.value ? 'active' : '',
    bucket ?? '',
  ].filter(Boolean);
}

function bucketForNumber(area: Area, number: number): Bucket | null {
  if (getBucket(area, 'dan').includes(number)) return 'dan';
  if (getBucket(area, 'tuo').includes(number)) return 'tuo';
  if (getBucket(area, 'kill').includes(number)) return 'kill';
  return null;
}

function removeFromArea(area: Area, number: number): void {
  for (const bucket of ['dan', 'tuo', 'kill'] as Bucket[]) {
    setBucket(
      area,
      bucket,
      getBucket(area, bucket).filter((item) => item !== number),
    );
  }
}

function getBucket(area: Area, bucket: Bucket): number[] {
  if (area === 'front' && bucket === 'dan') return form.frontDan;
  if (area === 'front' && bucket === 'tuo') return form.frontTuo;
  if (area === 'front' && bucket === 'kill') return form.frontKill;
  if (area === 'back' && bucket === 'dan') return form.backDan;
  if (area === 'back' && bucket === 'tuo') return form.backTuo;
  return form.backKill;
}

function setBucket(area: Area, bucket: Bucket, value: number[]): void {
  if (area === 'front' && bucket === 'dan') form.frontDan = value;
  else if (area === 'front' && bucket === 'tuo') form.frontTuo = value;
  else if (area === 'front' && bucket === 'kill') form.frontKill = value;
  else if (area === 'back' && bucket === 'dan') form.backDan = value;
  else if (area === 'back' && bucket === 'tuo') form.backTuo = value;
  else form.backKill = value;
}

function buildWeightedNumbers(
  area: Area,
  maxNumber: number,
  excludedNumbers: number[],
  samePeriodDetails: LotteryRecommendationNumberDetail[],
  recommendationDetails: LotteryRecommendationNumberDetail[],
): WeightedNumber[] {
  const excluded = new Set(excludedNumbers);
  const scoreMap = new Map<number, number>();
  for (const detail of [...samePeriodDetails, ...recommendationDetails]) {
    const current = scoreMap.get(detail.number) ?? 0;
    const samePeriodBoost = detail.same_period_hits * (area === 'front' ? 12 : 10);
    const missingBoost = Math.min(detail.current_missing, area === 'front' ? 20 : 10) * 0.35;
    scoreMap.set(
      detail.number,
      Math.max(current, detail.score + samePeriodBoost + missingBoost),
    );
  }

  return Array.from({ length: maxNumber }, (_, index) => index + 1)
    .filter((number) => !excluded.has(number))
    .map((number) => ({
      number,
      weight: Math.max(1, scoreMap.get(number) ?? 8),
    }));
}

function pickBalancedFrontNumbers(pool: WeightedNumber[], count: number): number[] {
  let best = pickWeightedNumbers(pool, count);
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const candidate = pickWeightedNumbers(pool, count);
    if (isBalancedFront(candidate)) return candidate;
    if (frontBalancePenalty(candidate) < frontBalancePenalty(best)) {
      best = candidate;
    }
  }
  return best;
}

function pickWeightedNumbers(pool: WeightedNumber[], count: number): number[] {
  const remaining = [...pool];
  const selected: number[] = [];
  while (selected.length < count && remaining.length > 0) {
    const totalWeight = remaining.reduce((sum, item) => sum + item.weight, 0);
    let cursor = Math.random() * totalWeight;
    const selectedIndex = remaining.findIndex((item) => {
      cursor -= item.weight;
      return cursor <= 0;
    });
    const index = selectedIndex >= 0 ? selectedIndex : remaining.length - 1;
    const [picked] = remaining.splice(index, 1);
    selected.push(picked.number);
  }
  return selected.sort(sortNumbers);
}

function isBalancedFront(numbers: number[]): boolean {
  if (numbers.length < 5) return true;
  const zones = frontZoneCounts(numbers);
  const oddCount = numbers.filter((number) => number % 2 === 1).length;
  return Math.max(...zones) <= Math.max(4, Math.ceil(numbers.length * 0.65))
    && oddCount > 0
    && oddCount < numbers.length;
}

function frontBalancePenalty(numbers: number[]): number {
  const zones = frontZoneCounts(numbers);
  const oddCount = numbers.filter((number) => number % 2 === 1).length;
  return Math.max(...zones) * 2 + Math.abs(oddCount - numbers.length / 2);
}

function frontZoneCounts(numbers: number[]): [number, number, number] {
  return [
    numbers.filter((number) => number <= 12).length,
    numbers.filter((number) => number >= 13 && number <= 24).length,
    numbers.filter((number) => number >= 25).length,
  ];
}

function sortNumbers(left: number, right: number): number {
  return left - right;
}

function formatCurrency(value: number): string {
  return `¥${value.toLocaleString('zh-CN')}`;
}

const PoolBlock = defineComponent({
  props: {
    title: {
      type: String,
      required: true,
    },
    area: {
      type: String as PropType<Area>,
      required: true,
    },
    numbers: {
      type: Array as PropType<number[]>,
      required: true,
    },
    muted: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    return () =>
      h('div', { class: ['pool-block', props.muted ? 'pool-muted' : ''] }, [
        h('div', { class: 'pool-title' }, props.title),
        props.numbers.length
          ? h(
              'div',
              { class: 'ball-row' },
              props.numbers.map((number) =>
                h(LotteryBall, {
                  key: `${props.area}-${props.title}-${number}`,
                  area: props.area,
                  value: number,
                }),
              ),
            )
          : h('div', { class: 'pool-empty' }, '未选择'),
      ]);
  },
});
</script>

<style scoped>
.dantuo-header {
  align-items: center;
}

.dantuo-actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.dantuo-alert,
.random-panel,
.picker-panel,
.dantuo-metrics,
.summary-panel,
.preview-panel,
.dantuo-empty {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-primary);
  font-size: 13px;
}

.random-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.random-item {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  color: var(--color-muted);
  display: grid;
  gap: 8px;
  padding: 12px;
}

.random-item span {
  font-size: 12px;
}

.random-options {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 12px;
}

.random-hints {
  color: var(--color-muted);
  display: grid;
  gap: 4px;
  font-size: 12px;
  line-height: 1.55;
  margin-top: 10px;
}

.target-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.target-button {
  border: 1px solid rgba(148, 163, 184, 0.16);
  color: var(--color-text);
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    transform 0.18s ease;
}

.target-button {
  background: rgba(15, 23, 42, 0.44);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  min-height: 92px;
  padding: 12px;
  text-align: left;
}

.target-button:hover {
  border-color: rgba(56, 189, 248, 0.48);
}

.target-button.active {
  background: rgba(56, 189, 248, 0.14);
  border-color: rgba(56, 189, 248, 0.62);
}

.target-button strong {
  color: var(--color-primary);
  font-size: 22px;
}

.target-button small,
.pool-empty,
.preview-meta,
.board-header span {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.number-board {
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
}

.board-header {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.board-header h3 {
  font-size: 16px;
  margin: 0 0 4px;
}

.selected-grid,
.summary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 14px;
}

.pool-block {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 12px;
}

.pool-muted {
  opacity: 0.78;
}

.pool-title {
  color: var(--color-muted);
  font-size: 12px;
}

.ball-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preview-list {
  display: grid;
  gap: 10px;
}

.preview-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  grid-template-columns: 48px minmax(0, 1fr) minmax(180px, auto);
  padding: 10px 12px;
}

.preview-rank {
  color: var(--color-primary);
  font-weight: 700;
}

@media (max-width: 1080px) {
  .random-grid,
  .target-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

}

@media (max-width: 720px) {
  .dantuo-header,
  .dantuo-actions,
  .random-options,
  .board-header {
    align-items: stretch;
    flex-direction: column;
  }

  .random-grid,
  .target-grid,
  .selected-grid,
  .summary-grid,
  .preview-row {
    grid-template-columns: 1fr;
  }

}
</style>
