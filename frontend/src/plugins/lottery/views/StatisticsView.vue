<template>
  <div>
    <section class="page-header">
      <div>
        <h1 class="page-title">统计分析</h1>
        <div class="page-subtitle">频率、遗漏、和值、跨度、冷热和共现分析</div>
      </div>
      <RouterLink to="/lottery/dlt" class="back-link">返回概览</RouterLink>
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2 class="panel-title">分析工作台</h2>
      </div>
      <div class="panel-body">
        <el-tabs model-value="frequency">
          <el-tab-pane label="频率" name="frequency" />
          <el-tab-pane label="遗漏" name="missing" />
          <el-tab-pane label="和值" name="sum" />
          <el-tab-pane label="跨度" name="span" />
          <el-tab-pane label="冷热" name="hot-cold" />
          <el-tab-pane label="共现" name="co-occurrence" />
        </el-tabs>
        <EmptyState
          title="统计 API 待接入"
          description="历史开奖同步稳定后，会逐项实现统计与图表 API。"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue';
</script>

<style scoped>
.back-link {
  color: var(--color-muted);
  font-size: 13px;
}
</style>
