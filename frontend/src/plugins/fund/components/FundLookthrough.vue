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
        <el-button :icon="Connection" @click="openTargetLinkManager">
          目标 ETF
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
              <small>
                {{ snapshot.fund_code }} · 仓位 {{ formatPercent(snapshot.allocation_weight) }}
                · 覆盖 {{ formatPercent(snapshot.covered_weight) }}
              </small>
              <small v-if="snapshot.source_mode === 'target_etf'">
                目标 {{ snapshot.target_fund_code }} {{ snapshot.target_fund_name }}
                · 占比 {{ formatOptionalPercent(snapshot.target_allocation_ratio) }}
              </small>
            </div>
            <div class="snapshot-meta">
              <span>{{ snapshotDateText(snapshot) }}</span>
              <span v-if="snapshot.source_mode === 'target_etf'">
                关系披露 {{ snapshot.relation_report_date || '--' }}
              </span>
              <span :class="['snapshot-status', `is-${snapshot.status}`]">
                {{ snapshotSourceText(snapshot) }} · {{ snapshotStatusText(snapshot.status) }}
              </span>
            </div>
          </div>
        </div>

        <p class="lookthrough-note">{{ lookthrough.warning }}</p>
      </div>
    </div>

    <el-dialog
      v-model="managerVisible"
      title="目标 ETF 关系"
      width="min(780px, 92vw)"
      destroy-on-close
    >
      <div class="target-manager">
        <div class="target-manager-head">
          <p>联接基金直接披露过期时，系统按这里的目标 ETF 和配置占比进行二级穿透。</p>
          <el-button type="primary" :icon="Plus" @click="startCreateLink">
            新增关系
          </el-button>
        </div>

        <div v-if="editingLink" class="target-form">
          <label>
            <span>联接基金代码</span>
            <el-input
              v-model="linkForm.parent_fund_code"
              :disabled="editingParentCode !== null"
              maxlength="6"
              placeholder="例如 050025"
            />
          </label>
          <label>
            <span>目标 ETF 代码</span>
            <el-input
              v-model="linkForm.target_fund_code"
              maxlength="6"
              placeholder="例如 513500"
            />
          </label>
          <label class="wide">
            <span>目标 ETF 名称</span>
            <el-input v-model="linkForm.target_fund_name" maxlength="128" />
          </label>
          <label>
            <span>目标 ETF 占比</span>
            <el-input-number
              v-model="linkForm.target_allocation_percent"
              :min="0.01"
              :max="100"
              :precision="2"
              :step="0.1"
              controls-position="right"
            />
          </label>
          <label>
            <span>关系披露日期</span>
            <el-date-picker
              v-model="linkForm.report_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
            />
          </label>
          <label class="wide">
            <span>公开来源链接</span>
            <el-input v-model="linkForm.source_url" placeholder="https://..." />
          </label>
          <div class="target-form-actions wide">
            <el-button @click="cancelEditLink">取消</el-button>
            <el-button type="primary" :loading="savingLink" @click="submitTargetLink">
              保存关系
            </el-button>
          </div>
        </div>

        <div v-loading="loadingLinks" class="target-list">
          <div v-if="!targetLinks.length && !loadingLinks" class="target-empty">
            暂无目标 ETF 关系
          </div>
          <div v-for="link in targetLinks" :key="link.parent_fund_code" class="target-row">
            <div class="target-route">
              <strong>{{ link.parent_fund_code }}</strong>
              <span>联接至</span>
              <strong>{{ link.target_fund_code }}</strong>
              <span>{{ link.target_fund_name }}</span>
            </div>
            <div class="target-meta">
              <span>占比 {{ formatPercent(link.target_allocation_ratio) }}</span>
              <span>披露 {{ link.report_date }}</span>
              <el-link :href="link.source_url" :icon="TopRight" target="_blank">
                来源
              </el-link>
              <el-tag size="small" effect="plain">
                {{ link.origin === 'database' ? '页面配置' : '部署默认' }}
              </el-tag>
            </div>
            <div class="target-row-actions">
              <el-tooltip content="编辑关系" placement="top">
                <el-button circle :icon="Edit" @click="startEditLink(link)" />
              </el-tooltip>
              <el-tooltip content="删除关系" placement="top">
                <el-button
                  circle
                  type="danger"
                  plain
                  :icon="Delete"
                  :loading="deletingLinkCode === link.parent_fund_code"
                  @click="removeTargetLink(link)"
                />
              </el-tooltip>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </RevealContent>
</template>

<script setup lang="ts">
import { Connection, Delete, Edit, Plus, Refresh, TopRight } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, ref, watch } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';
import {
  deleteFundTargetLink,
  fetchFundTargetLinks,
  fetchFundLookthrough,
  saveFundTargetLink,
  syncFundLookthrough,
  type FundLookthrough,
  type FundLookthroughSnapshot,
  type FundTargetLink,
} from '@/plugins/fund/api';

const props = defineProps<{
  refreshKey: number;
}>();

const staleAfterDays = ref(180);
const lookthrough = ref<FundLookthrough | null>(null);
const loading = ref(false);
const syncing = ref(false);
const managerVisible = ref(false);
const loadingLinks = ref(false);
const savingLink = ref(false);
const deletingLinkCode = ref<string | null>(null);
const editingLink = ref(false);
const editingParentCode = ref<string | null>(null);
const targetLinks = ref<FundTargetLink[]>([]);
const emptyLinkForm = () => ({
  parent_fund_code: '',
  target_fund_code: '',
  target_fund_name: '',
  target_allocation_percent: 100,
  report_date: '',
  source_url: '',
});
const linkForm = ref(emptyLinkForm());

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

async function loadTargetLinks(): Promise<void> {
  loadingLinks.value = true;
  try {
    targetLinks.value = await fetchFundTargetLinks();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '目标 ETF 关系加载失败');
  } finally {
    loadingLinks.value = false;
  }
}

function openTargetLinkManager(): void {
  managerVisible.value = true;
  editingLink.value = false;
  void loadTargetLinks();
}

function startCreateLink(): void {
  linkForm.value = emptyLinkForm();
  editingParentCode.value = null;
  editingLink.value = true;
}

function startEditLink(link: FundTargetLink): void {
  editingParentCode.value = link.parent_fund_code;
  linkForm.value = {
    parent_fund_code: link.parent_fund_code,
    target_fund_code: link.target_fund_code,
    target_fund_name: link.target_fund_name,
    target_allocation_percent: Number(link.target_allocation_ratio) * 100,
    report_date: link.report_date,
    source_url: link.source_url,
  };
  editingLink.value = true;
}

function cancelEditLink(): void {
  editingLink.value = false;
  editingParentCode.value = null;
  linkForm.value = emptyLinkForm();
}

async function submitTargetLink(): Promise<void> {
  const form = linkForm.value;
  if (!/^\d{6}$/.test(form.parent_fund_code) || !/^\d{6}$/.test(form.target_fund_code)) {
    ElMessage.warning('联接基金和目标 ETF 必须填写 6 位数字代码');
    return;
  }
  if (form.parent_fund_code === form.target_fund_code) {
    ElMessage.warning('联接基金和目标 ETF 不能是同一只基金');
    return;
  }
  if (!form.target_fund_name.trim() || !form.report_date || !form.source_url.trim()) {
    ElMessage.warning('请填写完整的关系名称、披露日期和公开来源');
    return;
  }
  savingLink.value = true;
  try {
    await saveFundTargetLink({
      parent_fund_code: form.parent_fund_code,
      target_fund_code: form.target_fund_code,
      target_fund_name: form.target_fund_name.trim(),
      target_allocation_ratio: form.target_allocation_percent / 100,
      report_date: form.report_date,
      source_url: form.source_url.trim(),
    });
    ElMessage.success('目标 ETF 关系已保存');
    cancelEditLink();
    await Promise.all([loadTargetLinks(), loadLookthrough()]);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '目标 ETF 关系保存失败');
  } finally {
    savingLink.value = false;
  }
}

async function removeTargetLink(link: FundTargetLink): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除 ${link.parent_fund_code} 到 ${link.target_fund_code} 的穿透关系？`,
      '确认删除关系',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
  } catch {
    return;
  }
  deletingLinkCode.value = link.parent_fund_code;
  try {
    await deleteFundTargetLink(link.parent_fund_code);
    ElMessage.success('目标 ETF 关系已删除');
    await Promise.all([loadTargetLinks(), loadLookthrough()]);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '目标 ETF 关系删除失败');
  } finally {
    deletingLinkCode.value = null;
  }
}

function formatPercent(value: string): string {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : '--';
}

function formatOptionalPercent(value: string | null): string {
  return value === null ? '--' : formatPercent(value);
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

function snapshotSourceText(snapshot: FundLookthroughSnapshot): string {
  if (snapshot.source_mode === 'direct') return '直接披露';
  if (snapshot.source_mode === 'target_etf') return '二级穿透';
  return '暂无来源';
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

.target-manager {
  display: grid;
  gap: 16px;
}

.target-manager-head {
  align-items: center;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.target-manager-head p,
.target-empty {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}

.target-form {
  border-block: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding-block: 14px;
}

.target-form label {
  display: grid;
  gap: 6px;
}

.target-form label > span {
  color: var(--color-muted);
  font-size: 12px;
}

.target-form .wide {
  grid-column: span 2;
}

.target-form .el-input-number,
.target-form .el-date-editor {
  width: 100%;
}

.target-form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.target-list {
  display: grid;
  min-height: 56px;
}

.target-row {
  align-items: center;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr) auto;
  min-height: 62px;
  padding-block: 9px;
}

.target-route,
.target-meta,
.target-row-actions {
  align-items: center;
  display: flex;
  gap: 8px;
}

.target-route span,
.target-meta span {
  color: var(--color-muted);
  font-size: 12px;
}

.target-meta {
  flex-wrap: wrap;
}

.target-row-actions {
  justify-content: flex-end;
}

.target-empty {
  padding: 18px 0;
  text-align: center;
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

  .target-manager-head,
  .target-row {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .target-manager-head {
    flex-direction: column;
  }

  .target-manager-head .el-button {
    width: 100%;
  }

  .target-form {
    grid-template-columns: 1fr;
  }

  .target-form .wide {
    grid-column: auto;
  }

  .target-row-actions {
    justify-content: flex-start;
  }
}
</style>
