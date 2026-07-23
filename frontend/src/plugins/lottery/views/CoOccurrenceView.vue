<template>
  <div>
    <section class="page-header co-header">
      <div>
        <h1 class="page-title">共现网络</h1>
        <div class="page-subtitle">观察号码同期开奖的关联强度，并与随机期望对比</div>
      </div>
      <div class="co-actions">
        <el-button type="primary" :loading="loading" @click="loadData">刷新分析</el-button>
      </div>
    </section>

    <DltModuleNav />

    <section class="panel co-panel">
      <div class="panel-header">
        <h2 class="panel-title">分析参数</h2>
        <span class="panel-meta">lift 大于 1 表示实际共现次数高于随机期望</span>
      </div>
      <div class="co-form">
        <label>
          区域
          <el-segmented v-model="area" :options="areaOptions" />
        </label>
        <label>
          样本期数
          <el-input-number v-model="limit" :min="50" :max="2000" :step="50" />
        </label>
        <label>
          展示边数
          <el-input-number v-model="top" :min="5" :max="100" :step="5" />
        </label>
      </div>
    </section>

    <div class="grid metrics co-metrics">
      <MetricCard label="样本数量" :value="sampleSize" :meta="issueRange" />
      <MetricCard label="网络节点" :value="nodeCount" :meta="areaLabel" />
      <MetricCard label="展示关联" :value="edgeCount" :meta="`Top ${top}`" />
      <MetricCard label="最高 lift" :value="maxLift" meta="相对随机期望" />
    </div>

    <section v-if="analysis?.edges.length" class="panel co-panel">
      <div class="panel-header">
        <h2 class="panel-title">最强共现关联</h2>
        <span class="panel-meta">按 lift 和共现次数排序</span>
      </div>
      <div class="edge-table">
        <div class="edge-row edge-head">
          <span>号码组合</span>
          <span>实际</span>
          <span>期望</span>
          <span>lift</span>
          <span>z-score</span>
        </div>
        <article v-for="edge in analysis.edges" :key="`${edge.source}-${edge.target}`" class="edge-row">
          <span class="pair">{{ formatNode(edge.source) }} + {{ formatNode(edge.target) }}</span>
          <span>{{ edge.count }}</span>
          <span>{{ edge.expected }}</span>
          <span :class="liftClass(edge.lift)">{{ edge.lift }}</span>
          <span>{{ edge.z_score }}</span>
        </article>
      </div>
    </section>

    <section v-if="topNodes.length" class="panel co-panel">
      <div class="panel-header">
        <h2 class="panel-title">高频节点</h2>
        <span class="panel-meta">节点大小暂用出现次数衡量</span>
      </div>
      <div class="node-grid">
        <article v-for="node in topNodes" :key="node.id" class="node-card">
          <strong>{{ formatNumber(node.number) }}</strong>
          <span>{{ areaName(node.area) }}</span>
          <small>{{ node.count }} 次</small>
        </article>
      </div>
    </section>

    <section v-if="analysis" class="panel co-panel">
      <div class="panel-header">
        <h2 class="panel-title">解释与风险</h2>
        <span class="panel-meta">避免把共现误读为预测规则</span>
      </div>
      <ul class="note-list">
        <li v-for="note in analysis.notes" :key="note">{{ note }}</li>
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

type CoArea = 'front' | 'back' | 'cross';

const lottery = useLotteryStore();
const loading = ref(false);
const area = ref<CoArea>('front');
const limit = ref(500);
const top = ref(30);
const areaOptions = [
  { label: '前区', value: 'front' },
  { label: '后区', value: 'back' },
  { label: '跨区', value: 'cross' },
];

const analysis = computed(() => lottery.coOccurrence);
const sampleSize = computed(() => String(analysis.value?.sample_size ?? 0));
const issueRange = computed(() =>
  analysis.value
    ? `${analysis.value.earliest_issue_no ?? '--'} - ${analysis.value.latest_issue_no ?? '--'}`
    : '等待分析',
);
const nodeCount = computed(() => String(analysis.value?.nodes.length ?? 0));
const edgeCount = computed(() => String(analysis.value?.edges.length ?? 0));
const maxLift = computed(() =>
  analysis.value?.edges.length ? String(analysis.value.edges[0].lift) : '--',
);
const areaLabel = computed(() => areaName(area.value));
const topNodes = computed(() => analysis.value?.nodes.slice(0, 18) ?? []);

onMounted(() => {
  void loadData();
});

async function loadData(): Promise<void> {
  loading.value = true;
  try {
    await lottery.loadCoOccurrence(area.value, limit.value, top.value);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '共现分析失败');
  } finally {
    loading.value = false;
  }
}

function areaName(value: string): string {
  if (value === 'back') return '后区';
  if (value === 'cross') return '跨区';
  return '前区';
}

function formatNumber(value: number): string {
  return String(value).padStart(2, '0');
}

function formatNode(value: string): string {
  const [nodeArea, number] = value.split('-');
  return `${areaName(nodeArea)} ${formatNumber(Number(number))}`;
}

function liftClass(value: number): string {
  if (value >= 1.5) return 'is-high';
  if (value >= 1.1) return 'is-medium';
  return 'is-low';
}
</script>

<style scoped>
.co-header,
.co-actions {
  align-items: center;
}

.co-actions {
  display: flex;
  flex-shrink: 0;
  gap: 12px;
}

.co-panel,
.co-metrics {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.co-form {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.co-form label {
  color: var(--color-muted);
  display: grid;
  font-size: 12px;
  gap: 8px;
}

.edge-table {
  display: grid;
  gap: 8px;
}

.edge-row {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  grid-template-columns: 1.6fr repeat(4, 0.7fr);
  padding: 10px 12px;
}

.edge-row span {
  color: var(--color-muted);
  font-size: 13px;
}

.edge-row .pair {
  color: var(--color-text);
  font-weight: 700;
}

.edge-head {
  background: rgba(15, 23, 42, 0.48);
  font-weight: 700;
}

.node-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.node-card {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 4px;
  padding: 12px;
}

.node-card strong {
  color: var(--color-primary);
  font-size: 20px;
}

.node-card span,
.node-card small,
.note-list {
  color: var(--color-muted);
  font-size: 13px;
}

.note-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
}

.is-high {
  color: #fca5a5 !important;
}

.is-medium {
  color: #fcd34d !important;
}

.is-low {
  color: #86efac !important;
}

@media (max-width: 960px) {
  .co-form,
  .edge-row,
  .node-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .co-header,
  .co-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
