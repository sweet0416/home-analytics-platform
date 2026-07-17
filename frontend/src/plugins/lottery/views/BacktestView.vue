<template>
  <div>
    <section class="page-header backtest-header">
      <div>
        <h1 class="page-title">组合回测</h1>
        <div class="page-subtitle">把一组 5+2 放回历史开奖里验证命中表现</div>
      </div>
      <div class="backtest-actions">
        <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
        <el-checkbox v-model="form.addon">按追加成本计算</el-checkbox>
        <el-input-number v-model="form.hitLimit" :min="1" :max="100" size="small" />
        <el-button type="primary" :loading="analyzing" @click="handleBacktest">开始回测</el-button>
      </div>
    </section>

    <DisclaimerAlert :text="lottery.backtest?.disclaimer ?? fallbackDisclaimer" />

    <el-alert
      v-if="errorMessage"
      class="backtest-alert"
      type="warning"
      :title="errorMessage"
      :closable="false"
      show-icon
    />

    <section class="panel input-panel">
      <div class="panel-header">
        <h2 class="panel-title">回测输入</h2>
        <span class="panel-meta">前区 5 个，后区 2 个，支持空格、逗号、顿号分隔</span>
      </div>
      <div class="input-grid">
        <NumberInput
          v-model="form.frontNumbers"
          label="前区号码"
          hint="必须填写 5 个不重复号码，范围 01-35"
          placeholder="如 03 09 16 24 30"
        />
        <NumberInput
          v-model="form.backNumbers"
          label="后区号码"
          hint="必须填写 2 个不重复号码，范围 01-12"
          placeholder="如 03 10"
        />
      </div>
    </section>

    <div class="grid metrics backtest-metrics">
      <MetricCard label="历史样本" :value="sampleSize" :meta="sampleRange" />
      <MetricCard label="中奖期数" :value="hitCount" :meta="hitRate" />
      <MetricCard label="最高命中" :value="highestHitLabel" :meta="highestHitMeta" />
      <MetricCard label="固定奖净值" :value="netFixedResult" meta="不含浮动奖估算" />
    </div>

    <section v-if="lottery.backtest" class="panel selected-panel">
      <div class="panel-header">
        <h2 class="panel-title">快速汇总</h2>
        <span class="panel-meta">{{ costSummary }}</span>
      </div>
      <div class="selected-content">
        <div class="selected-balls">
          <span class="number-label">前区</span>
          <LotteryBall
            v-for="number in lottery.backtest.front_numbers"
            :key="`front-${number}`"
            area="front"
            :value="number"
          />
          <span class="number-label back-label">后区</span>
          <LotteryBall
            v-for="number in lottery.backtest.back_numbers"
            :key="`back-${number}`"
            area="back"
            :value="number"
          />
        </div>
        <div class="cost-grid">
          <div>
            <span>普通成本</span>
            <strong>{{ formatCurrency(lottery.backtest.base_cost) }}</strong>
          </div>
          <div>
            <span>追加成本</span>
            <strong>{{ formatCurrency(lottery.backtest.addon_cost) }}</strong>
          </div>
          <div>
            <span>固定奖回报</span>
            <strong>{{ formatCurrency(lottery.backtest.fixed_prize_return) }}</strong>
          </div>
          <div>
            <span>浮动奖命中</span>
            <strong>{{ lottery.backtest.floating_hit_count }} 次</strong>
          </div>
        </div>
      </div>
    </section>

    <section v-if="lottery.backtest" class="panel hit-panel">
      <div class="panel-header">
        <h2 class="panel-title">命中明细</h2>
        <span class="panel-meta">最多展示 {{ lottery.backtest.hit_preview_limit }} 条，按奖级优先排序</span>
      </div>
      <div v-if="lottery.backtest.hits.length" class="hit-list">
        <article v-for="hit in lottery.backtest.hits" :key="hit.issue_no" class="hit-card">
          <div class="hit-topline">
            <div>
              <strong>{{ hit.issue_no }}</strong>
              <span>{{ hit.draw_date }}</span>
            </div>
            <el-tag effect="dark" :type="hit.prize_tier <= 3 ? 'success' : 'info'">
              {{ hit.tier_name }} / {{ hit.match_key }}
            </el-tag>
          </div>
          <div class="hit-balls">
            <span class="number-label">开奖前区</span>
            <LotteryBall
              v-for="number in hit.draw_front_numbers"
              :key="`${hit.issue_no}-front-${number}`"
              area="front"
              :value="number"
            />
            <span class="number-label back-label">开奖后区</span>
            <LotteryBall
              v-for="number in hit.draw_back_numbers"
              :key="`${hit.issue_no}-back-${number}`"
              area="back"
              :value="number"
            />
          </div>
          <div class="hit-meta">
            <span>前区命中 {{ formatNumberList(hit.front_matches) }}</span>
            <span>后区命中 {{ formatNumberList(hit.back_matches) }}</span>
            <span>
              {{ hit.is_floating ? '浮动奖，未估算金额' : `固定奖 ${formatCurrency(hit.base_prize_amount ?? 0)}` }}
            </span>
          </div>
        </article>
      </div>
      <EmptyState
        v-else
        title="历史未命中奖级"
        description="这组号码在当前历史库中没有命中过官方奖级。"
      />
    </section>

    <section v-if="lottery.backtest" class="panel distribution-panel">
      <div class="panel-header">
        <h2 class="panel-title">命中分布</h2>
        <span class="panel-meta">每一种前区+后区命中结构出现过多少次</span>
      </div>
      <div class="distribution-grid">
        <div
          v-for="item in visibleDistribution"
          :key="item.match_key"
          class="distribution-item"
        >
          <strong>{{ item.match_key }}</strong>
          <span>{{ item.count }} 期</span>
          <small>{{ item.tier_name }}</small>
        </div>
      </div>
    </section>

    <section v-if="lottery.backtest" class="panel explain-panel">
      <div class="panel-header">
        <h2 class="panel-title">回测说明</h2>
        <span class="panel-meta">通俗解释</span>
      </div>
      <div class="methodology-list">
        <div v-for="item in lottery.backtest.methodology" :key="item" class="methodology-item">
          {{ item }}
        </div>
      </div>
    </section>

    <EmptyState
      v-if="!lottery.backtest"
      class="backtest-empty"
      title="输入一组号码开始回测"
      description="回测只说明这组号码在历史上表现如何，不代表未来更容易开奖。"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, reactive, ref } from 'vue';

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
  frontNumbers: '',
  backNumbers: '',
  addon: false,
  hitLimit: 20,
});

const sampleSize = computed(() => String(lottery.backtest?.sample_size ?? 0));
const sampleRange = computed(() => {
  const result = lottery.backtest;
  if (!result) return '等待回测';
  return `${result.earliest_issue_no} - ${result.latest_issue_no}`;
});
const hitCount = computed(() => String(lottery.backtest?.hit_count ?? 0));
const hitRate = computed(() => {
  const result = lottery.backtest;
  if (!result?.sample_size) return '中奖期数 / 历史样本';
  return `${((result.hit_count / result.sample_size) * 100).toFixed(2)}%`;
});
const highestHitLabel = computed(() => lottery.backtest?.highest_hit?.match_key ?? '--');
const highestHitMeta = computed(() => lottery.backtest?.highest_hit?.tier_name ?? '暂无命中奖级');
const netFixedResult = computed(() => formatCurrency(lottery.backtest?.net_fixed_result ?? 0));
const costSummary = computed(() => {
  const result = lottery.backtest;
  if (!result) return '--';
  return `总成本 ${formatCurrency(result.total_cost)} / 固定奖回报 ${formatCurrency(result.fixed_prize_return)}`;
});
const visibleDistribution = computed(
  () => lottery.backtest?.distribution.filter((item) => item.count > 0).slice(0, 12) ?? [],
);

async function handleBacktest(): Promise<void> {
  errorMessage.value = '';
  analyzing.value = true;
  try {
    await lottery.backtestNumbers({
      front_numbers: parseNumbers(form.frontNumbers),
      back_numbers: parseNumbers(form.backNumbers),
      addon: form.addon,
      hit_limit: form.hitLimit,
    });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '组合回测失败';
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

function formatNumberList(numbers: number[]): string {
  return numbers.length ? numbers.map((number) => String(number).padStart(2, '0')).join(' ') : '无';
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
</script>

<style scoped>
.backtest-header {
  align-items: center;
}

.backtest-actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.back-link,
.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.backtest-alert,
.input-panel,
.backtest-metrics,
.selected-panel,
.hit-panel,
.distribution-panel,
.explain-panel,
.backtest-empty {
  margin-top: 16px;
}

.input-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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
.hit-meta,
.methodology-item,
.distribution-item small {
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

.selected-content,
.cost-grid,
.hit-list,
.methodology-list {
  display: grid;
  gap: 12px;
}

.selected-balls,
.hit-balls,
.hit-topline,
.hit-meta {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hit-topline {
  justify-content: space-between;
}

.hit-topline div {
  display: grid;
  gap: 4px;
}

.hit-topline span {
  color: var(--color-muted);
  font-size: 13px;
}

.number-label {
  color: var(--color-muted);
  font-size: 12px;
}

.back-label {
  margin-left: 6px;
}

.cost-grid,
.distribution-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.cost-grid div,
.distribution-item,
.hit-card,
.methodology-item {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.cost-grid span,
.distribution-item span {
  color: var(--color-muted);
  display: block;
  font-size: 12px;
  margin-bottom: 6px;
}

.cost-grid strong,
.distribution-item strong {
  font-size: 18px;
}

.hit-card {
  display: grid;
  gap: 12px;
}

@media (max-width: 920px) {
  .backtest-header,
  .backtest-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .input-grid,
  .cost-grid,
  .distribution-grid {
    grid-template-columns: 1fr;
  }
}
</style>
