<template>
  <div>
    <section class="page-header">
      <div>
        <h1 class="page-title">历史开奖</h1>
        <div class="page-subtitle">官方开奖数据同步后将在这里展示</div>
      </div>
      <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2 class="panel-title">开奖列表</h2>
        <span class="table-meta">共 {{ lottery.draws?.pagination.total ?? 0 }} 期</span>
      </div>
      <div class="panel-body">
        <el-table v-if="lottery.draws?.items.length" :data="lottery.draws.items" class="draw-table">
          <el-table-column prop="issue_no" label="期号" width="120" />
          <el-table-column prop="draw_date" label="开奖日期" width="130" />
          <el-table-column label="前区">
            <template #default="{ row }">
              <div class="ball-row">
                <LotteryBall v-for="number in row.front_numbers" :key="number" :value="number" area="front" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="后区">
            <template #default="{ row }">
              <div class="ball-row">
                <LotteryBall v-for="number in row.back_numbers" :key="number" :value="number" area="back" />
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="sales_amount" label="销售额" width="140" />
          <el-table-column prop="pool_amount" label="奖池" width="140" />
        </el-table>
        <EmptyState
          v-else
          title="暂无开奖数据"
          description="Phase 8 会接入官方数据同步任务，数据入库后自动显示。"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();

onMounted(() => {
  void lottery.loadOverview();
});
</script>

<style scoped>
.back-link,
.table-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.ball-row {
  display: flex;
  gap: 6px;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(15, 23, 42, 0.5);
  --el-table-text-color: var(--color-text);
  --el-table-header-text-color: var(--color-muted);
  --el-table-border-color: rgba(148, 163, 184, 0.14);
}
</style>

