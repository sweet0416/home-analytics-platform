<template>
  <div>
    <section class="page-header dantuo-header">
      <div>
        <h1 class="page-title">胆拖辅助</h1>
        <div class="page-subtitle">用胆码、拖码、杀号快速计算注数、成本和组合预览</div>
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

    <section class="panel dantuo-form-panel">
      <div class="panel-header">
        <h2 class="panel-title">选号输入</h2>
        <span class="panel-meta">支持空格、逗号、顿号分隔</span>
      </div>
      <div class="dantuo-form-grid">
        <NumberInput
          v-model="form.frontDan"
          label="前区胆码"
          hint="每一注都会包含，最多 4 个"
          placeholder="如 03 09"
        />
        <NumberInput
          v-model="form.frontTuo"
          label="前区拖码"
          hint="从拖码里补足前区 5 个"
          placeholder="如 05 10 16 22 29 30"
        />
        <NumberInput
          v-model="form.frontKill"
          label="前区杀号"
          hint="从可选池中排除"
          placeholder="如 01 02"
        />
        <NumberInput
          v-model="form.backDan"
          label="后区胆码"
          hint="每一注都会包含，最多 1 个"
          placeholder="如 10"
        />
        <NumberInput
          v-model="form.backTuo"
          label="后区拖码"
          hint="从拖码里补足后区 2 个"
          placeholder="如 01 03 11 12"
        />
        <NumberInput
          v-model="form.backKill"
          label="后区杀号"
          hint="从可选池中排除"
          placeholder="如 02"
        />
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
      title="先输入一组胆码和拖码"
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

const lottery = useLotteryStore();
const analyzing = ref(false);
const errorMessage = ref('');
const fallbackDisclaimer = '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。';

const form = reactive({
  frontDan: '',
  frontTuo: '',
  frontKill: '',
  backDan: '',
  backTuo: '',
  backKill: '',
  addon: false,
  previewLimit: 20,
});

const totalBets = computed(() => String(lottery.dantuo?.total_bets ?? 0));
const baseCost = computed(() => formatCurrency(lottery.dantuo?.base_cost ?? 0));
const addonCost = computed(() => formatCurrency(lottery.dantuo?.addon_cost ?? 0));
const totalCost = computed(() => formatCurrency(lottery.dantuo?.total_cost ?? 0));
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
      front_dan: parseNumbers(form.frontDan),
      front_tuo: parseNumbers(form.frontTuo),
      front_kill: parseNumbers(form.frontKill),
      back_dan: parseNumbers(form.backDan),
      back_tuo: parseNumbers(form.backTuo),
      back_kill: parseNumbers(form.backKill),
      addon: form.addon,
      preview_limit: form.previewLimit,
    });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '胆拖方案计算失败';
  } finally {
    analyzing.value = false;
  }
}

function parseNumbers(value: string): number[] {
  return Array.from(
    new Set(
      value
        .split(/[\s,，、]+/)
        .map((item) => Number.parseInt(item, 10))
        .filter((item) => Number.isFinite(item)),
    ),
  ).sort((left, right) => left - right);
}

function formatCurrency(value: number): string {
  return `¥${value.toLocaleString('zh-CN')}`;
}

const NumberInput = defineComponent({
  props: {
    modelValue: {
      type: String,
      required: true,
    },
    label: {
      type: String,
      required: true,
    },
    hint: {
      type: String,
      required: true,
    },
    placeholder: {
      type: String,
      required: true,
    },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () =>
      h('label', { class: 'number-input' }, [
        h('span', { class: 'number-input-label' }, props.label),
        h('span', { class: 'number-input-hint' }, props.hint),
        h('input', {
          value: props.modelValue,
          placeholder: props.placeholder,
          onInput: (event: Event) => {
            emit('update:modelValue', (event.target as HTMLInputElement).value);
          },
        }),
      ]);
  },
});

const PoolBlock = defineComponent({
  props: {
    title: {
      type: String,
      required: true,
    },
    area: {
      type: String as PropType<'front' | 'back'>,
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
          : h('div', { class: 'pool-empty' }, '未填写'),
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
.dantuo-form-panel,
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

.dantuo-form-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.number-input {
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  display: grid;
  gap: 8px;
  padding: 12px;
}

.number-input-label {
  font-weight: 700;
}

.number-input-hint,
.pool-empty,
.preview-meta,
.explain-panel li,
.explain-panel p {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}

.number-input input {
  background: rgba(15, 23, 42, 0.74);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 8px;
  color: var(--color-text);
  font: inherit;
  outline: none;
  padding: 10px 11px;
}

.number-input input:focus {
  border-color: rgba(56, 189, 248, 0.65);
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.12);
}

.summary-grid,
.explain-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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

@media (max-width: 920px) {
  .dantuo-header,
  .dantuo-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .dantuo-form-grid,
  .summary-grid,
  .explain-grid,
  .preview-row {
    grid-template-columns: 1fr;
  }
}
</style>
