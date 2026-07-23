<template>
  <div>
    <section class="page-header randomness-header">
      <div>
        <h1 class="page-title">随机性体检</h1>
        <div class="page-subtitle">检查开奖序列的频率、熵、和值相关性和结构分布</div>
      </div>
      <div class="randomness-actions">
        <el-button type="primary" :loading="loading" @click="loadDiagnostics">刷新体检</el-button>
      </div>
    </section>

    <DltModuleNav />

    <section class="panel randomness-panel">
      <div class="panel-header">
        <h2 class="panel-title">体检参数</h2>
        <span class="panel-meta">结果用于观察随机序列特征，不用于预测</span>
      </div>
      <div class="diagnostic-form">
        <label>
          样本期数
          <el-input-number v-model="limit" :min="50" :max="2000" :step="50" />
        </label>
      </div>
    </section>

    <div class="grid metrics randomness-metrics">
      <MetricCard label="样本数量" :value="sampleSize" :meta="issueRange" />
      <MetricCard label="前区熵" :value="frontEntropy" :meta="frontEntropyMeta" />
      <MetricCard label="后区熵" :value="backEntropy" :meta="backEntropyMeta" />
      <MetricCard label="和值自相关" :value="sumCorrelation" meta="lag 1" />
    </div>

    <section v-if="diagnostics" class="panel randomness-panel">
      <div class="panel-header">
        <h2 class="panel-title">频率卡方体检</h2>
        <span class="panel-meta">p 值为近似计算，低 p 值只代表样本频率偏离较大</span>
      </div>
      <div class="frequency-grid">
        <article
          v-for="metric in frequencyMetrics"
          :key="metric.area"
          class="frequency-card"
        >
          <div class="frequency-head">
            <strong>{{ metric.area }}</strong>
            <span>{{ pValueLabel(metric.p_value) }}</span>
          </div>
          <div class="metric-line">
            <span>卡方</span>
            <strong>{{ metric.chi_square }}</strong>
          </div>
          <div class="metric-line">
            <span>p 值</span>
            <strong>{{ metric.p_value }}</strong>
          </div>
          <div class="metric-line">
            <span>自由度</span>
            <strong>{{ metric.degrees_of_freedom }}</strong>
          </div>
          <p>{{ metric.interpretation }}</p>
        </article>
      </div>
    </section>

    <section v-if="diagnostics" class="panel randomness-panel">
      <div class="panel-header">
        <h2 class="panel-title">最大偏差号码</h2>
        <span class="panel-meta">实际出现次数与理论均值的差</span>
      </div>
      <div class="deviation-grid">
        <article v-for="group in deviationGroups" :key="group.area" class="deviation-block">
          <h3>{{ group.area }}</h3>
          <div class="deviation-row deviation-head">
            <span>号码</span>
            <span>实际</span>
            <span>理论</span>
            <span>偏差</span>
          </div>
          <div
            v-for="item in group.items"
            :key="`${group.area}-${item.number}`"
            class="deviation-row"
          >
            <span>{{ formatNumber(item.number) }}</span>
            <span>{{ item.count }}</span>
            <span>{{ item.expected }}</span>
            <span :class="deltaClass(item.deviation)">{{ formatSigned(item.deviation) }}</span>
          </div>
        </article>
      </div>
    </section>

    <section v-if="diagnostics" class="panel randomness-panel">
      <div class="panel-header">
        <h2 class="panel-title">结构摘要</h2>
        <span class="panel-meta">和值、奇偶和前区相邻间距</span>
      </div>
      <div class="structure-grid">
        <div class="structure-card">
          <strong>前区和值</strong>
          <span>
            均值 {{ diagnostics.front_sum.average }} · 标准差 {{ diagnostics.front_sum.stddev }}
          </span>
          <span>范围 {{ diagnostics.front_sum.min }} - {{ diagnostics.front_sum.max }}</span>
        </div>
        <div class="structure-card">
          <strong>前区间距</strong>
          <span>
            均值 {{ diagnostics.front_gap_summary.average }} · 标准差 {{ diagnostics.front_gap_summary.stddev }}
          </span>
          <span>范围 {{ diagnostics.front_gap_summary.min }} - {{ diagnostics.front_gap_summary.max }}</span>
        </div>
        <div class="structure-card">
          <strong>奇偶高频</strong>
          <span>{{ topParityPattern }}</span>
          <span>只描述历史样本结构，不表示未来倾向</span>
        </div>
      </div>
    </section>

    <section v-if="diagnostics" class="panel randomness-panel">
      <div class="panel-header">
        <h2 class="panel-title">解释与风险</h2>
        <span class="panel-meta">避免把随机波动看成规律</span>
      </div>
      <ul class="note-list">
        <li v-for="note in diagnostics.notes" :key="note">{{ note }}</li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import MetricCard from '@/components/metric/MetricCard.vue';
import DltModuleNav from '@/plugins/lottery/components/DltModuleNav.vue';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const loading = ref(false);
const limit = ref(500);

const diagnostics = computed(() => lottery.randomnessDiagnostics);
const sampleSize = computed(() => String(diagnostics.value?.sample_size ?? 0));
const issueRange = computed(() =>
  diagnostics.value
    ? `${diagnostics.value.earliest_issue_no ?? '--'} - ${diagnostics.value.latest_issue_no ?? '--'}`
    : '等待体检',
);
const frontEntropy = computed(() =>
  diagnostics.value ? `${(diagnostics.value.front_frequency.entropy.normalized * 100).toFixed(1)}%` : '--',
);
const backEntropy = computed(() =>
  diagnostics.value ? `${(diagnostics.value.back_frequency.entropy.normalized * 100).toFixed(1)}%` : '--',
);
const frontEntropyMeta = computed(() =>
  diagnostics.value
    ? `${diagnostics.value.front_frequency.entropy.value} / ${diagnostics.value.front_frequency.entropy.max}`
    : '等待体检',
);
const backEntropyMeta = computed(() =>
  diagnostics.value
    ? `${diagnostics.value.back_frequency.entropy.value} / ${diagnostics.value.back_frequency.entropy.max}`
    : '等待体检',
);
const sumCorrelation = computed(() =>
  diagnostics.value?.front_sum_autocorrelation.value === null
    || diagnostics.value?.front_sum_autocorrelation.value === undefined
    ? '--'
    : String(diagnostics.value.front_sum_autocorrelation.value),
);
const frequencyMetrics = computed(() =>
  diagnostics.value ? [diagnostics.value.front_frequency, diagnostics.value.back_frequency] : [],
);
const deviationGroups = computed(() =>
  diagnostics.value
    ? [
        { area: '前区', items: diagnostics.value.front_frequency.top_deviations },
        { area: '后区', items: diagnostics.value.back_frequency.top_deviations },
      ]
    : [],
);
const topParityPattern = computed(() => {
  const first = diagnostics.value?.front_parity_distribution[0];
  return first ? `${first.pattern} · ${first.count} 期` : '--';
});

onMounted(() => {
  void loadDiagnostics();
});

async function loadDiagnostics(): Promise<void> {
  loading.value = true;
  try {
    await lottery.loadRandomnessDiagnostics(limit.value);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '随机性体检失败');
  } finally {
    loading.value = false;
  }
}

function pValueLabel(value: number): string {
  if (value < 0.01) return '偏离较大';
  if (value < 0.05) return '需要关注';
  return '未见强偏离';
}

function formatNumber(value: number): string {
  return String(value).padStart(2, '0');
}

function formatSigned(value: number): string {
  if (value > 0) return `+${value}`;
  return String(value);
}

function deltaClass(value: number): string {
  if (value > 0) return 'is-positive';
  if (value < 0) return 'is-negative';
  return '';
}
</script>

<style scoped>
.randomness-header,
.randomness-actions {
  align-items: center;
}

.randomness-actions {
  display: flex;
  flex-shrink: 0;
  gap: 12px;
}

.randomness-panel,
.randomness-metrics {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.diagnostic-form {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.diagnostic-form label {
  color: var(--color-muted);
  display: grid;
  font-size: 12px;
  gap: 8px;
}

.frequency-grid,
.deviation-grid,
.structure-grid {
  display: grid;
  gap: 12px;
}

.frequency-grid,
.deviation-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.structure-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.frequency-card,
.deviation-block,
.structure-card {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 14px;
}

.frequency-head,
.metric-line,
.deviation-row {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.frequency-head span {
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 700;
}

.frequency-card p,
.metric-line span,
.deviation-row span,
.structure-card span,
.note-list {
  color: var(--color-muted);
  font-size: 13px;
}

.deviation-block h3 {
  font-size: 15px;
  margin: 0;
}

.deviation-head {
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  padding-bottom: 8px;
}

.structure-card strong {
  color: var(--color-text);
}

.note-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
}

.is-positive {
  color: #86efac !important;
}

.is-negative {
  color: #fca5a5 !important;
}

@media (max-width: 960px) {
  .frequency-grid,
  .deviation-grid,
  .structure-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .randomness-header,
  .randomness-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .diagnostic-form {
    grid-template-columns: 1fr;
  }
}
</style>
