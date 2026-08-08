<template>
  <section class="sync-panel">
    <div class="sync-header">
      <div>
        <h3>天天基金流水同步</h3>
        <p>上传 PowerShell 同步脚本导出的 JSON，先预览变更，再确认写入 HAP。</p>
      </div>
      <el-tag type="info" effect="plain">可重复导入</el-tag>
    </div>

    <div class="sync-grid">
      <label class="sync-field sync-field-wide">
        <span>同步包 JSON</span>
        <input ref="fileInput" type="file" accept="application/json,.json" @change="readFile" />
        <small>文件应包含 list_payload、detail_payloads、account_name。</small>
      </label>
      <label class="sync-field">
        <span>同步令牌</span>
        <el-input v-model="syncToken" type="password" show-password autocomplete="off" placeholder="仅本次浏览器会话使用" />
      </label>
      <label class="sync-field">
        <span>账户名称</span>
        <el-input v-model="accountName" placeholder="天天基金" />
      </label>
    </div>

    <el-input v-model="rawJson" class="sync-json" type="textarea" :rows="5" spellcheck="false" placeholder="也可以直接粘贴同步包 JSON" />

    <div class="sync-actions">
      <el-button :loading="previewing" :disabled="!canSubmit" @click="previewImport">预览变更</el-button>
      <el-button type="primary" :loading="importing" :disabled="!preview || preview.error_count > 0 || preview.total === 0" @click="confirmImport">确认导入</el-button>
      <span class="sync-hint">跳过项不会写入，重复流水会显示为更新或跳过。</span>
    </div>

    <div v-if="preview" class="sync-result">
      <div class="sync-counts">
        <div><strong>{{ preview.total }}</strong><span>总数</span></div>
        <div class="is-create"><strong>{{ preview.create_count }}</strong><span>新增</span></div>
        <div class="is-update"><strong>{{ preview.update_count }}</strong><span>更新</span></div>
        <div class="is-skip"><strong>{{ preview.skip_count }}</strong><span>跳过</span></div>
        <div class="is-error"><strong>{{ preview.error_count }}</strong><span>错误</span></div>
      </div>

      <div v-if="preview.items.length" class="sync-table-wrap">
        <div class="sync-table sync-table-head">
          <span>交易号</span><span>基金</span><span>类型</span><span>处理结果</span><span>说明</span>
        </div>
        <div v-for="item in preview.items" :key="item.trade_id" class="sync-table">
          <span class="mono">{{ item.trade_id }}</span>
          <span>{{ item.fund_name }}<small>{{ item.fund_code }}</small></span>
          <span>{{ item.business_type }}</span>
          <el-tag size="small" :type="actionTag(item.action)">{{ actionText(item.action) }}</el-tag>
          <span class="reason">{{ item.reason }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, ref } from 'vue';

import { importTtSkillTrades, previewTtSkillTrades, type FundTtSkillTradesImport, type FundTtSkillTradesImportResult } from '@/plugins/fund/api';

const emit = defineEmits<{ imported: [] }>();
const rawJson = ref('');
const syncToken = ref('');
const accountName = ref('天天基金');
const preview = ref<FundTtSkillTradesImportResult | null>(null);
const previewing = ref(false);
const importing = ref(false);
const canSubmit = computed(() => rawJson.value.trim().length > 0 && syncToken.value.trim().length > 0);

async function readFile(event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  rawJson.value = await file.text();
  ElMessage.success(`已读取 ${file.name}`);
}

function parsePayload(): FundTtSkillTradesImport {
  let parsed: unknown;
  try { parsed = JSON.parse(rawJson.value); } catch { throw new Error('同步包不是有效的 JSON。'); }
  if (!parsed || typeof parsed !== 'object') throw new Error('同步包必须是 JSON 对象。');
  const value = parsed as Record<string, unknown>;
  if (!value.list_payload || !Array.isArray(value.detail_payloads)) throw new Error('同步包缺少 list_payload 或 detail_payloads。');
  return {
    list_payload: value.list_payload as Record<string, unknown>,
    detail_payloads: value.detail_payloads as Record<string, unknown>[],
    account_name: accountName.value.trim() || '天天基金',
  };
}

function requestOptions() { return { headers: { 'X-HAP-Sync-Token': syncToken.value.trim() } }; }

async function previewImport(): Promise<void> {
  previewing.value = true;
  try {
    preview.value = await previewTtSkillTrades(parsePayload(), requestOptions());
    ElMessage.success('预览完成，请核对新增、更新、跳过和错误明细。');
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '流水预览失败'); }
  finally { previewing.value = false; }
}

async function confirmImport(): Promise<void> {
  if (!preview.value) return;
  try {
    await ElMessageBox.confirm(`确认导入 ${preview.value.create_count} 条新增、更新 ${preview.value.update_count} 条流水吗？`, '确认写入 HAP', { confirmButtonText: '确认导入', cancelButtonText: '取消', type: 'warning' });
  } catch { return; }
  importing.value = true;
  try {
    preview.value = await importTtSkillTrades(parsePayload(), requestOptions());
    ElMessage.success('流水导入完成，重复执行不会产生重复记录。');
    emit('imported');
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '流水导入失败'); }
  finally { importing.value = false; }
}

function actionText(action: FundTtSkillTradesImportResult['items'][number]['action']): string { return { create: '新增', update: '更新', skip: '跳过', error: '错误' }[action]; }
function actionTag(action: FundTtSkillTradesImportResult['items'][number]['action']): 'success' | 'warning' | 'danger' | 'info' {
  if (action === 'create') return 'success';
  if (action === 'update') return 'info';
  if (action === 'error') return 'danger';
  return 'warning';
}
</script>

<style scoped>
.sync-panel { border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 8px; margin-bottom: 18px; padding: 16px; }
.sync-header { align-items: flex-start; display: flex; gap: 12px; justify-content: space-between; }
.sync-header h3 { font-size: 15px; margin: 0; }
.sync-header p, .sync-field small, .sync-hint { color: var(--color-muted); font-size: 12px; margin: 6px 0 0; }
.sync-grid { display: grid; gap: 12px; grid-template-columns: 1.5fr 1fr 1fr; margin-top: 14px; }
.sync-field { display: grid; gap: 7px; }.sync-field > span { color: var(--color-muted); font-size: 12px; }.sync-field-wide { grid-column: 1 / -1; }
.sync-field input[type='file'] { color: var(--color-muted); font-size: 12px; }.sync-json { margin-top: 12px; }
.sync-actions { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
.sync-result { margin-top: 16px; }.sync-counts { display: grid; gap: 8px; grid-template-columns: repeat(5, 1fr); }
.sync-counts div { background: rgba(15, 23, 42, 0.35); border: 1px solid rgba(148, 163, 184, 0.12); border-radius: 8px; display: grid; gap: 3px; padding: 9px; }
.sync-counts strong { font-size: 18px; font-variant-numeric: tabular-nums; }.sync-counts span { color: var(--color-muted); font-size: 12px; }
.is-create strong { color: #34d399; }.is-update strong { color: #67e8f9; }.is-skip strong { color: #fbbf24; }.is-error strong { color: #fb7185; }
.sync-table-wrap { margin-top: 12px; max-height: 320px; overflow: auto; }.sync-table { align-items: center; border-bottom: 1px solid rgba(148, 163, 184, 0.1); display: grid; gap: 10px; grid-template-columns: 1fr 1.2fr .8fr .7fr 2fr; min-width: 760px; padding: 9px 4px; }
.sync-table-head { color: var(--color-muted); font-size: 12px; font-weight: 650; }.sync-table small { color: var(--color-muted); display: block; margin-top: 3px; }.reason { color: var(--color-muted); font-size: 12px; }.mono { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }
@media (max-width: 760px) { .sync-grid { grid-template-columns: 1fr; }.sync-field-wide { grid-column: auto; }.sync-counts { grid-template-columns: repeat(3, 1fr); } }
</style>
