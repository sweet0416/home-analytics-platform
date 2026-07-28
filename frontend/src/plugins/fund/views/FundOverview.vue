<template>
  <div>
    <RevealContent as="section" class="page-header" :delay="20">
      <div>
        <h1 class="page-title">Fund</h1>
        <div class="page-subtitle">ETF、QDII、资产配置和收益分析模块</div>
      </div>
    </RevealContent>

    <div class="grid metrics">
      <MetricCard label="Plugin" :value="statusLabel" meta="Fund module" :delay="80" />
      <MetricCard label="Data Source" :value="dataSourceLabel" meta="行情源" :delay="140" />
      <MetricCard label="Storage" :value="storageLabel" meta="数据库模型" :delay="200" />
      <MetricCard label="Version" :value="fundStatus?.version ?? '--'" meta="Plugin release" :delay="260" />
    </div>

    <RevealContent as="section" class="panel fund-panel" :delay="320">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">基金模块路线图</h2>
          <span class="panel-meta">{{ fundStatus?.description ?? '正在加载基金插件状态' }}</span>
        </div>
      </div>
      <div class="panel-body">
        <div v-if="isLoading" class="fund-loading">加载中...</div>
        <div v-else-if="errorMessage" class="fund-error">{{ errorMessage }}</div>
        <div v-else class="fund-roadmap">
          <div v-for="module in fundStatus?.modules ?? []" :key="module.code" class="roadmap-item">
            <div>
              <strong>{{ module.name }}</strong>
              <p>{{ module.description }}</p>
            </div>
            <span class="status-pill">{{ statusText(module.status) }}</span>
          </div>
        </div>
      </div>
    </RevealContent>

    <RevealContent as="section" class="panel fund-panel" :delay="380">
      <div class="panel-header">
        <h2 class="panel-title">下一步</h2>
      </div>
      <div class="panel-body">
        <p class="next-step">{{ fundStatus?.next_step ?? '等待后端基金插件状态接口返回。' }}</p>
      </div>
    </RevealContent>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import RevealContent from '@/components/common/RevealContent.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import { fetchFundStatus, type FundStatus } from '@/plugins/fund/api';

const fundStatus = ref<FundStatus | null>(null);
const isLoading = ref(false);
const errorMessage = ref('');

const labelMap: Record<string, string> = {
  scaffolded: '已接入',
  planned: '规划中',
  not_configured: '未配置',
  not_created: '未创建',
};

const statusText = (status: string): string => labelMap[status] ?? status;

const statusLabel = computed(() => statusText(fundStatus.value?.status ?? 'planned'));
const dataSourceLabel = computed(() => statusText(fundStatus.value?.data_source_status ?? 'not_configured'));
const storageLabel = computed(() => statusText(fundStatus.value?.storage_status ?? 'not_created'));

onMounted(async () => {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    fundStatus.value = await fetchFundStatus();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '基金模块状态加载失败';
  } finally {
    isLoading.value = false;
  }
});
</script>

<style scoped>
.fund-panel {
  margin-top: 16px;
}

.fund-roadmap {
  display: grid;
  gap: 10px;
}

.roadmap-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.32);
  padding: 14px;
}

.roadmap-item strong {
  color: var(--color-text);
  font-size: 14px;
}

.roadmap-item p,
.next-step,
.fund-loading,
.fund-error {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.7;
  margin: 6px 0 0;
}

.status-pill {
  border: 1px solid rgba(56, 189, 248, 0.34);
  border-radius: 999px;
  color: #7dd3fc;
  flex: 0 0 auto;
  font-size: 12px;
  padding: 4px 9px;
}

.fund-error {
  color: #fca5a5;
}

@media (max-width: 720px) {
  .roadmap-item {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
