<template>
  <RevealContent as="section" class="panel fund-panel" :delay="368">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">底层资产穿透</h2>
        <span class="panel-meta">按当前基金仓位汇总最近公开披露的前十大股票，识别重复暴露</span>
      </div>
      <div class="lookthrough-actions">
        <el-select v-model="staleAfterDays" class="freshness-select" @change="loadLookthrough">
          <el-option label="超过 90 天视为过期" :value="90" />
          <el-option label="超过 180 天视为过期" :value="180" />
          <el-option label="超过 365 天视为过期" :value="365" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadLookthrough">
          刷新
        </el-button>
        <el-button type="primary" :loading="syncing" @click="syncDisclosures">
          同步披露
        </el-button>
      </div>
    </div>

    <div class="panel-body">
      <div v-if="lookthrough" class="lookthrough-content">
        <div class="lookthrough-summary">
          <div>
            <span>组合覆盖率</span>
            <strong :class="coverageClass">{{ formatPercent(lookthrough.coverage_weight) }}</strong>
          </div>
          <div>
            <span>已披露股票暴露</span>
            <strong>{{ formatPercent(lookthrough.disclosed_weight) }}</strong>
          </div>
          <div>
            <span>有效披露基金</span>
            <strong>{{ lookthrough.current_disclosure_count }}/{{ lookthrough.fund_count }}</strong>
          </div>
          <div>
            <span>统计日期</span>
            <strong>{{ lookthrough.as_of_date }}</strong>
          </div>
        </div>

        <div v-if="lookthrough.assets.length" class="asset-table">
          <div class="asset-row table-head">
            <span>底层资产</span>
            <span>代码</span>
            <span>组合估算权重</span>
            <span>重复出现</span>
            <span>暴露结构</span>
          </div>
          <div
            v-for="asset in lookthrough.assets"
            :key="asset.asset_code"
            class="asset-row"
          >
            <strong>{{ asset.asset_name }}</strong>
            <span>{{ asset.asset_code }}</span>
            <span>{{ formatPercent(asset.portfolio_weight) }}</span>
            <span>{{ asset.fund_count }} 只基金</span>
            <span class="bar-track">
              <span class="bar-fill" :style="barStyle(asset.portfolio_weight)" />
            </span>
          </div>
        </div>
        <EmptyState
          v-else
          title="还没有可聚合的有效披露"
          description="点击“同步披露”获取当前持仓基金最近公开的季度前十大股票。"
        />

        <div class="snapshot-list">
          <div
            v-for="snapshot in lookthrough.snapshots"
            :key="snapshot.fund_code"
            class="snapshot-item"
          >
            <div>
              <strong>{{ snapshot.fund_name }}</strong>
              <small>{{ snapshot.fund_code }} · 仓位 {{ formatPercent(snapshot.allocation_weight) }}</small>
            </div>
            <div class="snapshot-meta">
              <span>{{ snapshotDateText(snapshot) }}</span>
              <span :class="['snapshot-status', `is-${snapshot.status}`]">
                {{ snapshotStatusText(snapshot.status) }}
              </span>
            </div>
          </div>
        </div>

        <p class="lookthrough-note">{{ lookthrough.warning }}</p>
      </div>
    </div>
  </RevealContent>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref, watch } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  fetchFundLookthrough,
  syncFundLookthrough,
  type FundLookthrough,
  type FundLookthroughSnapshot,
} from '@/plugins/fund/api';

const props = defineProps<{
  refreshKey: number;
}>();

const staleAfterDays = ref(180);
const lookthrough = ref<FundLookthrough | null>(null);
const loading = ref(false);
const syncing = ref(false);

const coverageClass = computed(() => {
  const coverage = Number(lookthrough.value?.coverage_weight);
  if (coverage >= 0.8) return 'is-good';
  if (coverage < 0.5) return 'is-warning';
  return '';
});

async function loadLookthrough(): Promise<void> {
  loading.value = true;
  try {
    lookthrough.value = await fetchFundLookthrough(staleAfterDays.value);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '底层资产穿透加载失败');
  } finally {
    loading.value = false;
  }
}

async function syncDisclosures(): Promise<void> {
  syncing.value = true;
  try {
    const result = await syncFundLookthrough();
    if (result.failed) {
      ElMessage.warning(`披露同步完成：成功 ${result.succeeded}，失败 ${result.failed}`);
    } else {
      ElMessage.success(`已同步 ${result.succeeded} 只基金的披露快照`);
    }
    await loadLookthrough();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '基金披露同步失败');
  } finally {
    syncing.value = false;
  }
}

function formatPercent(value: string): string {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : '--';
}

function barStyle(value: string): Record<string, string> {
  const numeric = Number(value);
  const width = Number.isFinite(numeric) ? Math.min(numeric * 500, 100) : 0;
  return { width: `${width}%` };
}

function snapshotStatusText(status: FundLookthroughSnapshot['status']): string {
  if (status === 'current') return '有效';
  if (status === 'stale') return '已过期';
  return '未同步';
}

function snapshotDateText(snapshot: FundLookthroughSnapshot): string {
  if (!snapshot.report_date) return '暂无披露';
  return `${snapshot.report_period} · ${snapshot.report_date} · ${snapshot.holding_count} 项`;
}

onMounted(() => {
  void loadLookthrough();
});

watch(
  () => props.refreshKey,
  () => {
    void loadLookthrough();
  },
);
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.panel-meta,
.lookthrough-note {
  color: var(--color-muted);
  font-size: 12px;
}

.lookthrough-actions {
  align-items: center;
  display: flex;
  gap: 8px;
}

.freshness-select {
  width: 196px;
}

.lookthrough-content {
  display: grid;
  gap: 16px;
}

.lookthrough-summary {
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding-bottom: 14px;
}

.lookthrough-summary div {
  display: grid;
  gap: 5px;
}

.lookthrough-summary span,
.snapshot-item small {
  color: var(--color-muted);
  font-size: 12px;
}

.lookthrough-summary strong {
  color: var(--color-text);
  font-size: 15px;
}

.asset-table {
  display: grid;
}

.asset-row {
  align-items: center;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: grid;
  font-size: 13px;
  gap: 12px;
  grid-template-columns: 1.4fr 0.8fr 0.9fr 0.8fr 1.2fr;
  min-height: 44px;
  padding: 6px 0;
}

.table-head {
  color: var(--color-muted);
  font-size: 12px;
}

.bar-track {
  background: rgba(148, 163, 184, 0.14);
  display: block;
  height: 6px;
  overflow: hidden;
  width: 100%;
}

.bar-fill {
  background: #38bdf8;
  display: block;
  height: 100%;
}

.snapshot-list {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.snapshot-item {
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.14);
  display: flex;
  justify-content: space-between;
  min-height: 58px;
  padding: 10px 12px;
}

.snapshot-item > div:first-child {
  display: grid;
  gap: 4px;
}

.snapshot-meta {
  align-items: flex-end;
  color: var(--color-muted);
  display: grid;
  font-size: 12px;
  gap: 5px;
  justify-items: end;
}

.snapshot-status {
  font-weight: 600;
}

.is-current,
.is-good {
  color: #22c55e !important;
}

.is-stale,
.is-warning {
  color: #f59e0b !important;
}

.is-missing {
  color: #94a3b8;
}

.lookthrough-note {
  line-height: 1.6;
  margin: 0;
}

@media (max-width: 860px) {
  .lookthrough-summary,
  .snapshot-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .asset-row {
    grid-template-columns: 1.2fr 0.8fr 0.8fr;
  }

  .asset-row > :nth-child(4),
  .asset-row > :nth-child(5) {
    display: none;
  }
}

@media (max-width: 640px) {
  .panel-header,
  .lookthrough-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .freshness-select {
    width: 100%;
  }

  .lookthrough-summary,
  .snapshot-list {
    grid-template-columns: 1fr;
  }

  .snapshot-item {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .snapshot-meta {
    align-items: start;
    justify-items: start;
  }
}
</style>
