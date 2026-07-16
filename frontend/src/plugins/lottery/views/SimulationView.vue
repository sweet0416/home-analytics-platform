<template>
  <div>
    <section class="page-header simulation-header">
      <div>
        <h1 class="page-title">模拟选号</h1>
        <div class="page-subtitle">
          用随机 Monte Carlo 抽样生成模拟组合，并观察号码频率是否接近理论概率
        </div>
      </div>
      <div class="simulation-actions">
        <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
        <el-button
          type="primary"
          :icon="Refresh"
          :loading="lottery.loading"
          @click="reloadSimulation"
        >
          开始模拟
        </el-button>
      </div>
    </section>

    <DisclaimerAlert
      :text="lottery.simulation?.disclaimer ?? fallbackDisclaimer"
      class="simulation-disclaimer"
    />

    <section class="panel control-panel">
      <div class="panel-header">
        <h2 class="panel-title">模拟参数</h2>
        <span class="panel-meta">随机种子可留空；填写后可复现同一批结果</span>
      </div>
      <div class="panel-body control-grid">
        <div class="control-item">
          <span>模拟次数</span>
          <el-input-number
            v-model="simulationCount"
            :min="100"
            :max="50000"
            :step="1000"
            size="small"
          />
        </div>
        <div class="control-item">
          <span>展示组数</span>
          <el-input-number v-model="setCount" :min="1" :max="20" size="small" />
        </div>
        <div class="control-item">
          <span>随机种子</span>
          <el-input
            v-model="seedInput"
            class="seed-input"
            clearable
            placeholder="可选"
            @keyup.enter="reloadSimulation"
          />
        </div>
      </div>
    </section>

    <div class="grid metrics simulation-metrics">
      <MetricCard label="模拟次数" :value="simulationTotal" meta="随机抽样轮数" />
      <MetricCard label="展示组合" :value="generatedCount" meta="模拟生成号码" />
      <MetricCard label="一等奖概率" :value="jackpotProbability" meta="官方规则组合数学" />
      <MetricCard label="随机种子" :value="seedLabel" meta="用于复现结果" />
    </div>

    <section class="panel generated-panel">
      <div class="panel-header">
        <h2 class="panel-title">模拟组合</h2>
        <span class="panel-meta">随机生成，不代表推荐</span>
      </div>
      <div class="panel-body">
        <div v-if="lottery.simulation?.generated_sets.length" class="summary-block">
          <div class="summary-header">
            <div>
              <h3 class="summary-title">快速汇总</h3>
              <div class="summary-meta">模拟号码集中查看，方便截图、抄写或对照筛选。</div>
            </div>
            <el-tag effect="dark" type="success">
              {{ generatedCount }} 组
            </el-tag>
          </div>
          <div class="summary-list">
            <div
              v-for="item in lottery.simulation.generated_sets"
              :key="`summary-${item.rank}`"
              class="summary-row"
            >
              <span class="summary-rank">第 {{ item.rank }} 组</span>
              <div class="summary-numbers">
                <span class="number-label">前区</span>
                <LotteryBall
                  v-for="number in item.front_numbers"
                  :key="`summary-front-${item.rank}-${number}`"
                  area="front"
                  :value="number"
                />
                <span class="number-label back-label">后区</span>
                <LotteryBall
                  v-for="number in item.back_numbers"
                  :key="`summary-back-${item.rank}-${number}`"
                  area="back"
                  :value="number"
                />
              </div>
            </div>
          </div>
        </div>

        <div v-if="lottery.simulation?.generated_sets.length" class="generated-list">
          <div
            v-for="item in lottery.simulation.generated_sets"
            :key="item.rank"
            class="generated-row"
          >
            <span class="generated-rank">第 {{ item.rank }} 组</span>
            <div class="number-row">
              <span class="number-label">前区</span>
              <LotteryBall
                v-for="number in item.front_numbers"
                :key="`front-${item.rank}-${number}`"
                area="front"
                :value="number"
              />
              <span class="number-label back-label">后区</span>
              <LotteryBall
                v-for="number in item.back_numbers"
                :key="`back-${item.rank}-${number}`"
                area="back"
                :value="number"
              />
            </div>
            <div class="pattern-row">
              <span>和值 {{ item.front_sum }}</span>
              <span>跨度 {{ item.front_span }}</span>
              <span>奇偶 {{ item.front_parity_pattern }}</span>
              <span>区间 {{ item.front_zone_pattern }}</span>
              <span>012路 {{ item.front_route012_pattern }}</span>
            </div>
          </div>
        </div>
        <EmptyState
          v-else
          title="暂无模拟结果"
          description="点击开始模拟后，会生成随机组合和号码频率。"
        />
      </div>
    </section>

    <section class="panel frequency-panel">
      <div class="panel-header">
        <h2 class="panel-title">频率观察</h2>
        <span class="panel-meta">出现次数越接近理论概率，随机模拟越稳定</span>
      </div>
      <div class="panel-body frequency-grid">
        <FrequencyList title="前区高频" :items="frontTop" />
        <FrequencyList title="后区高频" :items="backTop" />
      </div>
    </section>

    <section class="panel methodology-panel">
      <div class="panel-header">
        <h2 class="panel-title">模拟说明</h2>
        <span class="panel-meta">通俗版</span>
      </div>
      <div class="panel-body methodology-list">
        <div v-for="item in methodology" :key="item" class="methodology-item">
          {{ item }}
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, defineComponent, h, onMounted, ref, type PropType } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import type { LotterySimulationFrequency } from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const simulationCount = ref(10000);
const setCount = ref(5);
const seedInput = ref('');
const fallbackDisclaimer = '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。';

const simulationTotal = computed(() => String(lottery.simulation?.simulations ?? 0));
const generatedCount = computed(() => String(lottery.simulation?.generated_sets.length ?? 0));
const jackpotProbability = computed(
  () => lottery.simulation?.theoretical.jackpot_probability ?? '1 / 21425712',
);
const seedLabel = computed(() => {
  if (!lottery.simulation) return '--';
  return lottery.simulation.seed === null ? '随机' : String(lottery.simulation.seed);
});
const frontTop = computed(() => lottery.simulation?.front_frequency.slice(0, 12) ?? []);
const backTop = computed(() => lottery.simulation?.back_frequency.slice(0, 8) ?? []);
const methodology = computed(() =>
  lottery.simulation?.methodology.length
    ? lottery.simulation.methodology
    : [
        '前区每次从 1-35 中随机抽 5 个，后区每次从 1-12 中随机抽 2 个。',
        '模拟次数越多，单个号码的出现频率越接近理论概率。',
        '模拟选号只是帮助理解随机性，不会提高未来中奖概率。',
      ],
);

const FrequencyList = defineComponent({
  props: {
    title: {
      type: String,
      required: true,
    },
    items: {
      type: Array as PropType<LotterySimulationFrequency[]>,
      required: true,
    },
  },
  setup(props) {
    return () =>
      h('div', { class: 'frequency-card' }, [
        h('div', { class: 'frequency-title' }, props.title),
        h(
          'div',
          { class: 'frequency-list' },
          props.items.map((item) =>
            h('div', { class: 'frequency-item', key: item.number }, [
              h('span', { class: 'frequency-number' }, formatNumber(item.number)),
              h('span', `${item.count} 次`),
              h(
                'span',
                `${formatPercent(item.frequency)} / 偏差 ${formatSignedPercent(item.deviation)}`,
              ),
            ]),
          ),
        ),
      ]);
  },
});

async function reloadSimulation(): Promise<void> {
  lottery.loading = true;
  try {
    await lottery.loadSimulation(simulationCount.value, setCount.value, parseSeed());
  } finally {
    lottery.loading = false;
  }
}

function parseSeed(): number | undefined {
  const value = seedInput.value.trim();
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : undefined;
}

function formatNumber(value: number): string {
  return String(value).padStart(2, '0');
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function formatSignedPercent(value: number): string {
  const formatted = formatPercent(Math.abs(value));
  return value >= 0 ? `+${formatted}` : `-${formatted}`;
}

onMounted(() => {
  void reloadSimulation();
});
</script>

<style scoped>
.simulation-header {
  align-items: center;
}

.simulation-actions {
  align-items: center;
  display: flex;
  flex-shrink: 0;
  gap: 12px;
}

.back-link,
.panel-meta,
.number-label,
.pattern-row {
  color: var(--color-muted);
  font-size: 13px;
}

.simulation-disclaimer,
.control-panel,
.simulation-metrics,
.generated-panel,
.frequency-panel,
.methodology-panel {
  margin-top: 16px;
}

.control-grid,
.frequency-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.frequency-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.control-item {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  color: var(--color-muted);
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 12px;
}

.seed-input {
  max-width: 160px;
}

.generated-list {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.generated-row {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 12px;
}

.generated-rank {
  font-weight: 700;
}

.number-row,
.pattern-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pattern-row {
  gap: 12px;
}

.back-label {
  margin-left: 8px;
}

.summary-block {
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.36);
  display: grid;
  gap: 12px;
  padding: 14px;
}

.summary-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.summary-title {
  font-size: 15px;
  margin: 0;
}

.summary-meta {
  color: var(--color-muted);
  font-size: 12px;
  margin-top: 4px;
}

.summary-list {
  display: grid;
  gap: 10px;
}

.summary-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  grid-template-columns: 86px minmax(0, 1fr);
  padding: 12px;
}

.summary-rank {
  font-weight: 700;
}

.summary-numbers {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.frequency-card {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.frequency-title {
  font-weight: 700;
  margin-bottom: 10px;
}

.frequency-list {
  display: grid;
  gap: 8px;
}

.frequency-item {
  align-items: center;
  color: var(--color-muted);
  display: grid;
  font-size: 12px;
  gap: 8px;
  grid-template-columns: 38px 70px minmax(0, 1fr);
}

.frequency-number {
  color: var(--color-text);
  font-weight: 700;
}

.methodology-list {
  display: grid;
  gap: 10px;
}

.methodology-item {
  border-left: 3px solid rgba(56, 189, 248, 0.55);
  color: var(--color-muted);
  line-height: 1.65;
  padding-left: 12px;
}

@media (max-width: 860px) {
  .simulation-header,
  .simulation-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .control-grid,
  .frequency-grid,
  .summary-row {
    grid-template-columns: 1fr;
  }

  .control-item {
    align-items: stretch;
    flex-direction: column;
  }

  .seed-input {
    max-width: none;
  }
}
</style>
