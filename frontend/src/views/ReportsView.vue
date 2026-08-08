<template>
  <div class="reports-page">
    <RevealContent as="section" class="page-header" :delay="20">
      <div>
        <h1 class="page-title">Reports</h1>
        <div class="page-subtitle">
          集中查看基金日报、历史快照、变化洞察和推送状态
        </div>
      </div>
      <div class="page-header-meta">数据来自已保存的持仓与净值记录</div>
    </RevealContent>

    <FundDailyReport :refresh-key="refreshKey" />

    <RevealContent as="section" class="panel report-capabilities" :delay="120">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">报告能力</h2>
          <span class="panel-meta">当前报告中心的接入范围</span>
        </div>
      </div>
      <div class="panel-body capability-grid">
        <article class="capability-item is-ready">
          <strong>基金日报</strong>
          <span>已接入持仓、净值、风险和变化洞察。</span>
          <em>已启用</em>
        </article>
        <article class="capability-item is-ready">
          <strong>AI 摘要</strong>
          <span>通过已配置的 Webhook 生成结构化日报摘要。</span>
          <em>按配置启用</em>
        </article>
        <article class="capability-item is-ready">
          <strong>Bark 推送</strong>
          <span>将基金日报推送到已配置的 Bark 通道。</span>
          <em>已接入</em>
        </article>
        <article class="capability-item">
          <strong>Excel / CSV / PDF</strong>
          <span>统一导出任务和报告归档将在下一阶段接入。</span>
          <em>规划中</em>
        </article>
      </div>
    </RevealContent>
  </div>
</template>

<script setup lang="ts">
import RevealContent from '@/components/common/RevealContent.vue';
import FundDailyReport from '@/plugins/fund/components/FundDailyReport.vue';

const refreshKey = 0;
</script>

<style scoped>
.reports-page {
  display: grid;
  gap: 18px;
}

.page-header-meta {
  align-self: end;
  color: var(--color-muted);
  font-size: 12px;
}

.capability-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.capability-item {
  display: grid;
  gap: 7px;
  min-width: 0;
  border: 1px solid var(--color-border-soft);
  border-radius: 8px;
  padding: 14px;
}

.capability-item strong {
  color: var(--color-text);
  font-size: 14px;
}

.capability-item span {
  color: var(--color-muted);
  font-size: 12px;
  line-height: 1.6;
}

.capability-item em {
  color: var(--color-muted);
  font-size: 11px;
  font-style: normal;
}

.capability-item.is-ready {
  border-color: rgba(74, 222, 128, 0.26);
}

.capability-item.is-ready em {
  color: var(--color-success);
}

@media (max-width: 900px) {
  .capability-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .page-header-meta {
    display: none;
  }

  .capability-grid {
    grid-template-columns: 1fr;
  }
}
</style>
