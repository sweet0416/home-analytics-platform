<template>
  <div>
    <section class="page-header">
      <div>
        <h1 class="page-title">历史开奖</h1>
        <div class="page-subtitle">开奖数据同步后在这里展示和追踪</div>
      </div>
      <div class="history-actions">
        <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
        <el-button
          type="primary"
          :icon="Refresh"
          :loading="lottery.syncing"
          @click="lottery.syncNow"
        >
          同步
        </el-button>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2 class="panel-title">开奖记录</h2>
        <span class="table-meta">共 {{ lottery.draws?.pagination.total ?? 0 }} 期</span>
      </div>
      <div class="panel-body">
        <el-table v-if="lottery.draws?.items.length" :data="lottery.draws.items" class="draw-table">
          <el-table-column prop="issue_no" label="期号" width="120" />
          <el-table-column prop="draw_date" label="开奖日期" width="130" />
          <el-table-column label="前区" min-width="190">
            <template #default="{ row }">
              <div class="ball-row">
                <LotteryBall
                  v-for="number in row.front_numbers"
                  :key="number"
                  :value="number"
                  area="front"
                />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="后区" min-width="90">
            <template #default="{ row }">
              <div class="ball-row">
                <LotteryBall
                  v-for="number in row.back_numbers"
                  :key="number"
                  :value="number"
                  area="back"
                />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="销售额" width="150">
            <template #default="{ row }">{{ formatMoney(row.sales_amount) }}</template>
          </el-table-column>
          <el-table-column label="奖池" width="150">
            <template #default="{ row }">{{ formatMoney(row.pool_amount) }}</template>
          </el-table-column>
        </el-table>
        <EmptyState
          v-else
          title="暂无开奖数据"
          description="点击同步后会优先从官方来源获取数据，异常时自动使用备用源。"
        />
      </div>
    </section>

    <section class="panel sync-history-panel">
      <div class="panel-header">
        <h2 class="panel-title">同步历史</h2>
        <span class="table-meta">最近 {{ lottery.syncRuns?.items.length ?? 0 }} 次</span>
      </div>
      <div class="panel-body">
        <el-table
          v-if="lottery.syncRuns?.items.length"
          :data="lottery.syncRuns.items"
          class="draw-table"
        >
          <el-table-column prop="run_id" label="任务" width="90" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="syncTagType(row.status)" effect="dark">
                {{ syncStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sync_type" label="类型" width="110" />
          <el-table-column label="数据源" min-width="170">
            <template #default="{ row }">{{ lotterySyncSourceLabel(row.source) }}</template>
          </el-table-column>
          <el-table-column label="完成时间" min-width="180">
            <template #default="{ row }">{{ formatDateTime(row.finished_at) }}</template>
          </el-table-column>
          <el-table-column prop="latest_issue_no" label="最新期号" width="120" />
          <el-table-column label="新增/更新/跳过" width="150">
            <template #default="{ row }">
              {{ row.inserted_count }}/{{ row.updated_count }}/{{ row.skipped_count }}
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误" min-width="180" />
        </el-table>
        <EmptyState
          v-else
          title="暂无同步记录"
          description="手动或自动同步执行后会在这里记录任务结果。"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { onMounted } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import { lotterySyncSourceLabel } from '@/plugins/lottery/sourceLabels';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();

function formatMoney(value: string | null): string {
  if (!value) return '--';
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}

function formatDateTime(value: string | null): string {
  if (!value) return '--';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function syncStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    running: '同步中',
    success: '成功',
    partial_success: '部分成功',
    failed: '失败',
  };
  return labels[status] ?? status;
}

function syncTagType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'success') return 'success';
  if (status === 'partial_success') return 'warning';
  if (status === 'failed') return 'danger';
  return 'info';
}

onMounted(() => {
  void lottery.loadOverview();
});
</script>

<style scoped>
.history-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-link,
.table-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.ball-row {
  display: flex;
  gap: 6px;
}

.sync-history-panel {
  margin-top: 16px;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.5);
  --el-table-text-color: var(--color-text);
  --el-table-header-text-color: var(--color-muted);
  --el-table-border-color: rgba(148, 163, 184, 0.14);
}

@media (max-width: 720px) {
  .history-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
