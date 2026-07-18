<template>
  <div>
    <section class="page-header draw-history-header">
      <div>
        <h1 class="page-title">历史开奖</h1>
        <div class="page-subtitle">开奖数据同步后在这里展示和追踪</div>
      </div>
      <div class="draw-countdown">
        <div>
          <span>下次开奖</span>
          <strong>{{ nextDrawDateTime }}</strong>
        </div>
        <div>
          <span>倒计时</span>
          <strong>{{ nextDrawCountdown }}</strong>
        </div>
        <small>周一 / 周三 / 周六 21:10</small>
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
        <div v-if="lottery.draws?.pagination.total" class="history-pagination">
          <el-pagination
            v-model:current-page="currentDrawPage"
            v-model:page-size="drawPageSize"
            :total="lottery.draws.pagination.total"
            :page-sizes="[20, 50, 100, 200]"
            background
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="handleDrawPageChange"
            @size-change="handleDrawPageSizeChange"
          />
        </div>
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
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="sync-detail">
                <div class="sync-detail-header">
                  <strong>同步明细</strong>
                  <span>
                    {{ syncDetailSummary(row) }}
                  </span>
                </div>
                <div v-if="row.details?.length" class="sync-detail-grid">
                  <div
                    v-for="group in syncDetailGroups(row)"
                    :key="group.action"
                    class="sync-detail-card"
                  >
                    <div class="sync-detail-card-title">
                      <el-tag :type="syncActionTagType(group.action)" effect="dark" size="small">
                        {{ syncActionLabel(group.action) }}
                      </el-tag>
                      <span>{{ group.items.length }} 期</span>
                    </div>
                    <div class="sync-issue-list">
                      <span
                        v-for="item in group.items"
                        :key="`${group.action}-${item.issue_no}`"
                        class="sync-issue-chip"
                      >
                        {{ item.issue_no }}
                        <small>{{ item.draw_date }}</small>
                      </span>
                    </div>
                  </div>
                </div>
                <EmptyState
                  v-else
                  title="这条旧同步记录没有保存期号明细"
                  description="从本次更新之后执行的同步或回填，会记录具体新增、更新和跳过的期号。"
                />
              </div>
            </template>
          </el-table-column>
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
              <div class="sync-counts">
                <el-tag size="small" type="success" effect="plain">
                  新 {{ row.inserted_count }}
                </el-tag>
                <el-tag size="small" type="warning" effect="plain">
                  更 {{ row.updated_count }}
                </el-tag>
                <el-tag size="small" type="info" effect="plain">
                  跳 {{ row.skipped_count }}
                </el-tag>
              </div>
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import type { LotterySyncRun, LotterySyncRunDetail } from '@/plugins/lottery/api';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import { lotterySyncSourceLabel } from '@/plugins/lottery/sourceLabels';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();
const now = ref(new Date());
const currentDrawPage = ref(1);
const drawPageSize = ref(20);
let countdownTimer: number | undefined;

const nextDrawAt = computed(() => calculateNextDltDraw(now.value));
const nextDrawDateTime = computed(() => formatDateTime(nextDrawAt.value.toISOString()));
const nextDrawCountdown = computed(() => formatCountdown(nextDrawAt.value.getTime() - now.value.getTime()));

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

function syncActionLabel(action: string): string {
  const labels: Record<string, string> = {
    inserted: '新增',
    updated: '更新',
    skipped: '跳过',
    failed: '失败',
  };
  return labels[action] ?? action;
}

function syncActionTagType(action: string): 'success' | 'warning' | 'danger' | 'info' {
  if (action === 'inserted') return 'success';
  if (action === 'updated') return 'warning';
  if (action === 'failed') return 'danger';
  return 'info';
}

function syncDetailSummary(row: LotterySyncRun): string {
  if (!row.details?.length) return '无期号明细';
  return `共 ${row.details.length} 期，新增 ${row.inserted_count}，更新 ${row.updated_count}，跳过 ${row.skipped_count}`;
}

function syncDetailGroups(row: LotterySyncRun): Array<{
  action: string;
  items: LotterySyncRunDetail[];
}> {
  const order = ['inserted', 'updated', 'skipped', 'failed'];
  return order
    .map((action) => ({
      action,
      items: row.details.filter((item) => item.action === action),
    }))
    .filter((group) => group.items.length > 0);
}

function calculateNextDltDraw(current: Date): Date {
  const drawWeekdays = [1, 3, 6];
  const drawHour = 21;
  const drawMinute = 10;

  for (let offset = 0; offset <= 7; offset += 1) {
    const candidate = new Date(current);
    candidate.setDate(current.getDate() + offset);
    candidate.setHours(drawHour, drawMinute, 0, 0);
    if (drawWeekdays.includes(candidate.getDay()) && candidate.getTime() > current.getTime()) {
      return candidate;
    }
  }

  const fallback = new Date(current);
  fallback.setDate(current.getDate() + 1);
  fallback.setHours(drawHour, drawMinute, 0, 0);
  return fallback;
}

function formatCountdown(milliseconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const clock = [hours, minutes, seconds].map((item) => String(item).padStart(2, '0')).join(':');
  return days > 0 ? `${days}天 ${clock}` : clock;
}

async function handleDrawPageChange(page: number): Promise<void> {
  currentDrawPage.value = page;
  await lottery.loadDraws(currentDrawPage.value, drawPageSize.value);
}

async function handleDrawPageSizeChange(pageSize: number): Promise<void> {
  drawPageSize.value = pageSize;
  currentDrawPage.value = 1;
  await lottery.loadDraws(currentDrawPage.value, drawPageSize.value);
}

onMounted(() => {
  void lottery.loadOverview();
  countdownTimer = window.setInterval(() => {
    now.value = new Date();
  }, 1000);
});

onBeforeUnmount(() => {
  if (countdownTimer !== undefined) {
    window.clearInterval(countdownTimer);
  }
});
</script>

<style scoped>
.history-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 12px;
}

.draw-history-header {
  align-items: center;
  flex-wrap: wrap;
}

.draw-countdown {
  border: 1px solid rgba(56, 189, 248, 0.24);
  border-radius: 8px;
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(2, minmax(130px, 1fr));
  min-width: min(420px, 100%);
  padding: 10px 12px;
}

.draw-countdown div {
  display: grid;
  gap: 4px;
}

.draw-countdown span,
.draw-countdown small {
  color: var(--color-muted);
  font-size: 12px;
}

.draw-countdown strong {
  font-size: 15px;
  font-weight: 720;
  line-height: 1.3;
}

.draw-countdown small {
  grid-column: 1 / -1;
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

.history-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  overflow-x: auto;
}

.sync-history-panel {
  margin-top: 16px;
}

.sync-counts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sync-detail {
  background: rgba(15, 23, 42, 0.36);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  margin: 4px 0;
  padding: 14px;
}

.sync-detail-header {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: space-between;
}

.sync-detail-header span {
  color: var(--color-muted);
  font-size: 13px;
}

.sync-detail-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.sync-detail-card {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 12px;
}

.sync-detail-card-title {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.sync-detail-card-title span {
  color: var(--color-muted);
  font-size: 12px;
}

.sync-issue-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sync-issue-chip {
  background: rgba(2, 6, 23, 0.36);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  color: var(--color-text);
  display: grid;
  font-size: 12px;
  gap: 2px;
  min-width: 74px;
  padding: 7px 8px;
}

.sync-issue-chip small {
  color: var(--color-muted);
  font-size: 11px;
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
  .draw-history-header {
    align-items: stretch;
    flex-direction: column;
  }

  .history-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .draw-countdown {
    grid-template-columns: 1fr;
  }

  .sync-detail-grid {
    grid-template-columns: 1fr;
  }

  .history-pagination {
    justify-content: flex-start;
  }
}
</style>
