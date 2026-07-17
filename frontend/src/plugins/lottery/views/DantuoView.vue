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
        <div class="number-grid" :class="activeArea">
          <button
            v-for="number in activeNumbers"
            :key="`${activeArea}-${number}`"
            type="button"
            class="number-button"
            :class="numberButtonClass(number)"
            @click="toggleNumber(number)"
          >
            {{ formatNumber(number) }}
          </button>
        </div>
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

    <section v-if="lottery.dantuo" class="panel explain-panel">
      <div class="panel-header">
        <h2 class="panel-title">计算说明</h2>
        <span class="panel-meta">通俗解释</span>
      </div>
      <div class="explain-grid">
        <div>
          <h3>怎么算出来的</h3>
          <ul>
            <li v-for="item in lottery.dantuo.methodology" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div>
          <h3>风险提醒</h3>
          <ul v-if="lottery.dantuo.warnings.length">
            <li v-for="item in lottery.dantuo.warnings" :key="item">{{ item }}</li>
          </ul>
          <p v-else>当前方案结构正常，但任何历史统计都不能代表未来开奖结果。</p>
        </div>
      </div>
    </section>

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
import { useLotteryStore } from '@/plugins/lottery/store';

type Area = 'front' | 'back';
type Bucket = 'dan' | 'tuo' | 'kill';

interface SelectionTarget {
  area: Area;
  bucket: Bucket;
  label: string;
  hint: string;
}

const lottery = useLotteryStore();
const analyzing = ref(false);
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

function numberButtonClass(number: number): Record<string, boolean> {
  const bucket = bucketForNumber(activeArea.value, number);
  return {
    selected: bucket !== null,
    active: bucket === activeBucket.value,
    dan: bucket === 'dan',
    tuo: bucket === 'tuo',
    kill: bucket === 'kill',
  };
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

function formatNumber(value: number): string {
  return String(value).padStart(2, '0');
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
.picker-panel,
.dantuo-metrics,
.summary-panel,
.preview-panel,
.explain-panel,
.dantuo-empty {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-primary);
  font-size: 13px;
}

.target-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.target-button,
.number-button {
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

.target-button:hover,
.number-button:hover {
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
.explain-panel li,
.explain-panel p,
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

.number-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(12, minmax(0, 1fr));
}

.number-button {
  aspect-ratio: 1;
  background: rgba(15, 23, 42, 0.7);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 760;
  min-width: 0;
}

.number-button.selected {
  transform: translateY(-1px);
}

.number-button.dan {
  background: rgba(56, 189, 248, 0.18);
  border-color: rgba(56, 189, 248, 0.7);
  color: #7dd3fc;
}

.number-button.tuo {
  background: rgba(34, 197, 94, 0.16);
  border-color: rgba(34, 197, 94, 0.58);
  color: #86efac;
}

.number-button.kill {
  background: rgba(248, 113, 113, 0.16);
  border-color: rgba(248, 113, 113, 0.58);
  color: #fca5a5;
  text-decoration: line-through;
}

.number-button.active {
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.1);
}

.selected-grid,
.summary-grid,
.explain-grid {
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

.explain-panel h3 {
  font-size: 15px;
  margin: 0 0 10px;
}

.explain-panel ul {
  margin: 0;
  padding-left: 18px;
}

@media (max-width: 1080px) {
  .target-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .number-grid {
    grid-template-columns: repeat(8, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .dantuo-header,
  .dantuo-actions,
  .board-header {
    align-items: stretch;
    flex-direction: column;
  }

  .target-grid,
  .selected-grid,
  .summary-grid,
  .explain-grid,
  .preview-row {
    grid-template-columns: 1fr;
  }

  .number-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}
</style>
