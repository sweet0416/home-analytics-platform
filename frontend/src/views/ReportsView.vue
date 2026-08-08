<template>
  <div class="reports-page">
    <RevealContent as="section" class="page-header" :delay="20">
      <div>
        <h1 class="page-title">Reports</h1>
        <div class="page-subtitle">
          集中查看基金日报、历史快照、变化洞察和推送状态
        </div>
      </div>
      <div class="page-header-actions">
        <div class="page-header-meta">数据来自已保存的持仓与净值记录</div>
        <div class="page-header-buttons">
          <el-button plain @click="printReport">打印 / 保存 PDF</el-button>
          <el-button type="primary" plain @click="downloadSnapshotCsv">导出快照 CSV</el-button>
        </div>
      </div>
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
          <span>通过已配置的 AI 接口生成结构化日报摘要。</span>
          <em>按配置启用</em>
        </article>
        <article class="capability-item is-ready">
          <strong>Bark 推送</strong>
          <span>将基金日报推送到已配置的 Bark 通道。</span>
          <em>已接入</em>
        </article>
        <article class="capability-item is-ready">
          <strong>CSV 快照导出</strong>
          <span>导出已保存的日报快照，便于 Excel、数据分析或长期备份。</span>
          <em>已启用</em>
        </article>
      </div>
    </RevealContent>
  </div>
</template>

<script setup lang="ts">
import RevealContent from '@/components/common/RevealContent.vue';
import FundDailyReport from '@/plugins/fund/components/FundDailyReport.vue';
import { getFundDailySnapshotsExportUrl } from '@/plugins/fund/api';

const refreshKey = 0;

function downloadSnapshotCsv(): void {
  window.location.href = getFundDailySnapshotsExportUrl();
}

function printReport(): void {
  window.print();
}
</script>

<style scoped>
.reports-page {
  display: grid;
  gap: 18px;
}

.page-header-meta {
  color: var(--color-muted);
  font-size: 12px;
}

.page-header-actions {
  align-items: flex-end;
  display: grid;
  gap: 10px;
  justify-items: end;
}

.page-header-buttons {
  display: flex;
  gap: 8px;
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

  .page-header-actions {
    justify-items: stretch;
  }

  .page-header-buttons {
    flex-direction: column;
  }

  .capability-grid {
    grid-template-columns: 1fr;
  }
}

@media print {
  .reports-page {
    color: #111827;
    display: block;
  }

  .page-header-buttons,
  .report-capabilities {
    display: none;
  }
}
</style>
