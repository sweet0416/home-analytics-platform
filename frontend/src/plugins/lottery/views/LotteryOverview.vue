<template>
  <div>
    <section class="page-header">
      <div>
        <h1 class="page-title">超级大乐透</h1>
        <div class="page-subtitle">当前规则、开奖数据状态与基础分析入口</div>
      </div>
      <div class="lottery-tabs">
        <RouterLink to="/lottery/dlt">概览</RouterLink>
        <RouterLink to="/lottery/dlt/draws">历史开奖</RouterLink>
        <RouterLink to="/lottery/dlt/statistics">统计</RouterLink>
      </div>
    </section>

    <DisclaimerAlert v-if="lottery.disclaimer" :text="lottery.disclaimer" />

    <div class="grid metrics overview-metrics">
      <MetricCard
        label="前区"
        :value="frontRule"
        :meta="`${lottery.rule?.front.count ?? 5} 个号码`"
      />
      <MetricCard
        label="后区"
        :value="backRule"
        :meta="`${lottery.rule?.back.count ?? 2} 个号码`"
      />
      <MetricCard label="基本投注" :value="basePrice" meta="每注金额" />
      <MetricCard label="追加投注" :value="addonPrice" meta="仅参与浮动奖" />
    </div>

    <section class="panel rule-panel">
      <div class="panel-header">
        <h2 class="panel-title">当前规则版本</h2>
        <a v-if="lottery.rule?.official_url" :href="lottery.rule.official_url" target="_blank">
          官方来源
        </a>
      </div>
      <div class="panel-body">
        <div v-if="lottery.rule" class="tier-grid">
          <div v-for="tier in lottery.rule.prize_tiers" :key="`${tier.tier}-${tier.description}`">
            <strong>{{ tier.tier_name }}</strong>
            <span>{{ tier.description }}</span>
          </div>
        </div>
        <EmptyState v-else title="规则未加载" description="后端启动后会自动写入当前规则种子数据。" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import { useLotteryStore } from '@/plugins/lottery/store';

const lottery = useLotteryStore();

const frontRule = computed(() =>
  lottery.rule ? `${lottery.rule.front.min}-${lottery.rule.front.max}` : '--',
);
const backRule = computed(() =>
  lottery.rule ? `${lottery.rule.back.min}-${lottery.rule.back.max}` : '--',
);
const basePrice = computed(() => (lottery.rule ? `${lottery.rule.base_price} 元` : '--'));
const addonPrice = computed(() => (lottery.rule ? `${lottery.rule.addon_price} 元` : '--'));

onMounted(() => {
  void lottery.loadOverview();
});
</script>

<style scoped>
.overview-metrics {
  margin-top: 16px;
}

.lottery-tabs {
  display: flex;
  gap: 8px;
}

.lottery-tabs a {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 8px;
  color: var(--color-muted);
  padding: 8px 12px;
}

.lottery-tabs a.router-link-active {
  border-color: rgba(56, 189, 248, 0.5);
  color: var(--color-primary);
}

.rule-panel {
  margin-top: 16px;
}

.panel-header a {
  color: var(--color-primary);
  font-size: 13px;
}

.tier-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.tier-grid div {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 12px;
}

.tier-grid strong {
  display: block;
  margin-bottom: 6px;
}

.tier-grid span {
  color: var(--color-muted);
  font-size: 13px;
}

@media (max-width: 780px) {
  .tier-grid {
    grid-template-columns: 1fr;
  }
}
</style>

