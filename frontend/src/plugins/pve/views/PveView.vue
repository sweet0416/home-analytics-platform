<template>
  <div class="pve-page">
    <section class="page-header pve-header">
      <div>
        <h1 class="page-title">Proxmox VE</h1>
        <p class="page-subtitle">
          只读查看节点、虚拟机、容器、存储和任务状态。HAP 不会执行任何管理操作。
        </p>
      </div>
      <div class="header-actions">
        <span class="last-refresh">{{ refreshedAtLabel }}</span>
        <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新状态</el-button>
      </div>
    </section>

    <section class="panel connection-panel" :class="connectionClass">
      <div class="connection-indicator" aria-hidden="true"></div>
      <div class="connection-copy">
        <strong>{{ connectionTitle }}</strong>
        <span>{{ connectionMessage }}</span>
      </div>
      <span class="connection-version">{{ status?.pve_version ? `PVE ${status.pve_version}` : '只读监控' }}</span>
    </section>

    <el-alert
      v-if="errorMessage"
      class="pve-alert"
      type="warning"
      :closable="false"
      show-icon
      :title="errorMessage"
    />

    <div class="grid metrics pve-metrics">
      <MetricCard label="节点" :value="String(nodes.length)" meta="PVE 节点" :delay="60" />
      <MetricCard label="虚拟机 / 容器" :value="String(guests.length)" meta="QEMU 与 LXC" :delay="110" />
      <MetricCard label="存储" :value="String(storage.length)" meta="已发现的存储池" :delay="160" />
      <MetricCard label="近期任务" :value="String(tasks.length)" meta="最近 API 任务" :delay="210" />
    </div>

    <div v-if="!configured" class="panel setup-panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">等待配置只读连接</h2>
          <span class="panel-meta">生产环境默认关闭，避免未授权访问</span>
        </div>
        <el-tag type="info" effect="dark">未配置</el-tag>
      </div>
      <div class="panel-body setup-body">
        <p>在 Docker Stack 的环境变量中填写 PVE 只读 API Token 后，重新部署 HAP。</p>
        <code>PVE_ENABLED=true · PVE_API_TOKEN_ID · PVE_API_TOKEN_SECRET</code>
        <small>Token 建议绑定 PVEAuditor，只提供读取权限；密钥不要写入 Git。</small>
      </div>
    </div>

    <div v-else class="pve-grid">
      <section class="panel resource-panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">节点资源</h2>
            <span class="panel-meta">CPU、内存和运行时间</span>
          </div>
          <el-tag v-if="nodes.length" type="success" effect="dark">{{ nodes.length }} 个节点</el-tag>
        </div>
        <div class="panel-body resource-list">
          <div v-for="node in nodes" :key="String(node.node ?? node.id)" class="resource-row">
            <div class="resource-name">
              <span class="status-dot" :class="statusDotClass(node.status)"></span>
              <strong>{{ text(node.node ?? node.id, '未知节点') }}</strong>
              <small>{{ text(node.status, '未知状态') }}</small>
            </div>
            <div class="resource-values">
              <span>{{ percent(node.cpu) }} CPU</span>
              <span>{{ memory(node.mem, node.maxmem) }}</span>
              <span>{{ uptime(node.uptime) }}</span>
            </div>
          </div>
          <div v-if="!nodes.length" class="empty-inline">暂无节点数据</div>
        </div>
      </section>

      <section class="panel resource-panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">虚拟机与容器</h2>
            <span class="panel-meta">运行状态和资源占用</span>
          </div>
          <el-tag v-if="guests.length" type="info" effect="dark">{{ guests.length }} 个实例</el-tag>
        </div>
        <div class="panel-body resource-list">
          <div v-for="guest in guests" :key="`${guest.node}-${guest.vmid}`" class="resource-row">
            <div class="resource-name">
              <span class="type-badge">{{ guest.type === 'lxc' ? 'LXC' : 'VM' }}</span>
              <strong>{{ text(guest.name ?? guest.vmid, '未命名实例') }}</strong>
              <small>{{ text(guest.status, '未知状态') }}</small>
            </div>
            <div class="resource-values">
              <span>{{ text(guest.node, '--') }}</span>
              <span>{{ percent(guest.cpu) }} CPU</span>
              <span>{{ memory(guest.mem, guest.maxmem) }}</span>
            </div>
          </div>
          <div v-if="!guests.length" class="empty-inline">暂无虚拟机或容器数据</div>
        </div>
      </section>

      <section class="panel resource-panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">存储池</h2>
            <span class="panel-meta">容量和使用情况</span>
          </div>
        </div>
        <div class="panel-body resource-list">
          <div v-for="item in storage" :key="String(item.storage ?? item.id)" class="storage-row">
            <div class="storage-heading">
              <strong>{{ text(item.storage ?? item.id, '未知存储') }}</strong>
              <span :class="{ 'is-muted': !hasStorageCapacity(item) }">{{ storageUsage(item) }}</span>
            </div>
            <small class="storage-meta">{{ text(item.node, '--') }} · {{ text(item.type, 'storage') }} · {{ text(item.content, 'content unknown') }} · free {{ storageAvailable(item) }}</small>
            <div class="usage-track"><span :style="{ width: `${usage(item.used, item.total)}%` }"></span></div>
            <small>{{ bytes(item.used) }} / {{ bytes(item.total) }} · {{ text(item.type, 'storage') }}</small>
          </div>
          <div v-if="!storage.length" class="empty-inline">暂无存储数据</div>
        </div>
      </section>

      <section class="panel resource-panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">最近任务</h2>
            <span class="panel-meta">只读显示，不提供操作入口</span>
          </div>
          <el-select v-model="taskFilter" class="task-filter" size="small" aria-label="任务状态筛选">
            <el-option label="全部" value="all" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="已停止" value="stopped" />
          </el-select>
        </div>
        <div class="panel-body task-list">
          <div v-for="task in visibleTasks" :key="String(task.upid ?? task.id)" class="task-row">
            <div>
              <strong>{{ text(task.type, '任务') }}</strong>
              <small>{{ text(task.node, '--') }} · {{ text(task.user, '未知用户') }}</small>
            </div>
            <el-tooltip :content="text(task.status, '未知')" placement="top">
              <el-tag class="task-status-tag" :type="taskStatusType(task.status)" effect="dark">
                {{ text(task.status, '未知') }}
              </el-tag>
            </el-tooltip>
          </div>
          <div v-if="tasks.length && !visibleTasks.length" class="empty-inline">当前筛选条件下暂无任务</div>
          <div v-if="!tasks.length" class="empty-inline">暂无任务数据</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, onMounted, reactive, ref } from 'vue';

import MetricCard from '@/components/metric/MetricCard.vue';
import {
  fetchPveGuests,
  fetchPveNodes,
  fetchPveStatus,
  fetchPveStorage,
  fetchPveTasks,
  type PveStatus,
} from '@/plugins/pve/api';

const loading = ref(false);
const status = ref<PveStatus | null>(null);
const nodes = ref<Record<string, unknown>[]>([]);
const guests = ref<Record<string, unknown>[]>([]);
const storage = ref<Record<string, unknown>[]>([]);
const tasks = ref<Record<string, unknown>[]>([]);
const taskFilter = ref<'all' | 'success' | 'failed' | 'stopped'>('all');
const errorMessage = ref('');
const refreshedAt = ref<Date | null>(null);
type ResourceKey = 'nodes' | 'guests' | 'storage' | 'tasks';
const resourceErrors = reactive<Record<ResourceKey, string>>({ nodes: '', guests: '', storage: '', tasks: '' });

const configured = computed(() => Boolean(status.value?.configured));
const connectionClass = computed(() => {
  if (!status.value?.configured) return 'is-muted';
  if (hasResourceError.value) return 'is-warning';
  return status.value.reachable ? 'is-online' : 'is-warning';
});
const connectionTitle = computed(() => {
  if (!status.value?.configured) return 'PVE 只读监控尚未配置';
  if (hasResourceError.value) return 'PVE API 已连接，资源读取异常';
  return status.value.reachable ? 'PVE API 连接正常' : 'PVE API 暂时不可达';
});
const connectionMessage = computed(() => {
  if (!status.value?.configured) return '配置只读 Token 后，HAP 才会读取节点和虚拟机状态。';
  if (hasResourceError.value) return '版本接口正常，但部分资源接口返回错误，请检查 Token Secret 和 PVEAuditor 权限。';
  return status.value.reachable ? '数据来自 Proxmox VE API，只读模式已启用。' : status.value.error ?? '请检查 PVE 地址、证书和 Token。';
});
const hasResourceError = computed(() => Object.values(resourceErrors).some(Boolean));
const visibleTasks = computed(() => tasks.value.filter((task) => {
  if (taskFilter.value === 'all') return true;
  const status = String(task.status ?? '').toLowerCase();
  if (taskFilter.value === 'success') return status === 'ok';
  if (taskFilter.value === 'stopped') return status === 'stopped';
  return status.includes('failed') || status.includes('error');
}));
const refreshedAtLabel = computed(() =>
  refreshedAt.value ? `更新于 ${refreshedAt.value.toLocaleTimeString('zh-CN', { hour12: false })}` : '尚未更新',
);

async function loadAll(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  for (const key of Object.keys(resourceErrors) as ResourceKey[]) resourceErrors[key] = '';
  try {
    const currentStatus = await fetchPveStatus();
    status.value = currentStatus;
    if (!currentStatus.configured || !currentStatus.reachable) {
      nodes.value = [];
      guests.value = [];
      storage.value = [];
      tasks.value = [];
      return;
    }
    const results = await Promise.allSettled([
      fetchPveNodes(),
      fetchPveGuests(),
      fetchPveStorage(),
      fetchPveTasks(),
    ]);
    const keys: ResourceKey[] = ['nodes', 'guests', 'storage', 'tasks'];
    const setters = [
      (data: Record<string, unknown>[]) => { nodes.value = data; },
      (data: Record<string, unknown>[]) => { guests.value = data; },
      (data: Record<string, unknown>[]) => { storage.value = data; },
      (data: Record<string, unknown>[]) => { tasks.value = data; },
    ];
    results.forEach((result, index) => {
      const key = keys[index];
      if (result.status === 'fulfilled') setters[index](result.value.data);
      else resourceErrors[key] = result.reason instanceof Error ? result.reason.message : '接口读取失败';
    });
    if (hasResourceError.value) errorMessage.value = 'PVE 已连接，但部分资源接口读取失败；页面将保留能够正常返回的数据。';
    refreshedAt.value = new Date();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'PVE 数据加载失败，请稍后重试。';
  } finally {
    loading.value = false;
  }
}

function text(value: unknown, fallback: string): string {
  return value === undefined || value === null || value === '' ? fallback : String(value);
}

function percent(value: unknown): string {
  const number = Number(value);
  if (!Number.isFinite(number)) return '--';
  return `${(number * 100).toFixed(1)}%`;
}

function memory(used: unknown, total: unknown): string {
  if (!Number.isFinite(Number(used)) || !Number.isFinite(Number(total)) || Number(total) <= 0) return '--';
  return `${bytes(used)} / ${bytes(total)}`;
}

function bytes(value: unknown): string {
  const number = Number(value);
  if (!Number.isFinite(number)) return '--';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = number;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function usage(used: unknown, total: unknown): number {
  const value = Number(used) / Number(total) * 100;
  return Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0;
}

function hasStorageCapacity(item: Record<string, unknown>): boolean {
  return Number.isFinite(Number(item.used)) && Number.isFinite(Number(item.total)) && Number(item.total) > 0;
}

function storageUsage(item: Record<string, unknown>): string {
  return hasStorageCapacity(item) ? `${usage(item.used, item.total).toFixed(1)}%` : '--';
}

function storageAvailable(item: Record<string, unknown>): string {
  if (!hasStorageCapacity(item)) return '--';
  return bytes(Number(item.total) - Number(item.used));
}

function uptime(value: unknown): string {
  const seconds = Number(value);
  if (!Number.isFinite(seconds)) return '--';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return `${days}天 ${hours}小时`;
}

function statusDotClass(value: unknown): string {
  return value === 'online' ? 'is-online' : 'is-warning';
}

function taskStatusType(value: unknown): 'success' | 'warning' | 'danger' | 'info' {
  const status = String(value ?? '').toLowerCase();
  if (status === 'ok') return 'success';
  if (status === 'stopped') return 'warning';
  if (status === 'error' || status.includes('failed') || status.includes('error')) return 'danger';
  return 'info';
}

onMounted(() => {
  void loadAll();
});
</script>

<style scoped>
.pve-page { display: grid; gap: 16px; }
.pve-header { align-items: center; margin-bottom: 0; }
.header-actions { align-items: center; display: flex; flex-wrap: wrap; gap: 12px; }
.last-refresh { color: var(--color-muted); font-size: 12px; }
.connection-panel { align-items: center; display: flex; gap: 12px; min-height: 64px; padding: 14px 18px; }
.connection-panel.is-online { border-color: rgba(67, 212, 155, 0.34); }
.connection-panel.is-warning { border-color: rgba(244, 184, 96, 0.34); }
.connection-panel.is-muted { border-color: rgba(148, 163, 184, 0.22); }
.connection-indicator, .status-dot { background: var(--color-muted); border-radius: 999px; box-shadow: 0 0 0 4px rgba(148, 163, 184, 0.1); flex: 0 0 auto; height: 9px; width: 9px; }
.connection-indicator { height: 11px; width: 11px; }
.is-online .connection-indicator, .status-dot.is-online { background: var(--color-success); box-shadow: 0 0 0 4px rgba(67, 212, 155, 0.1); }
.is-warning .connection-indicator, .status-dot.is-warning { background: var(--color-warning); box-shadow: 0 0 0 4px rgba(244, 184, 96, 0.1); }
.connection-copy { display: grid; gap: 2px; min-width: 0; }
.connection-copy span, .panel-meta, .resource-name small, .storage-row small, .task-row small, .setup-body p, .setup-body small { color: var(--color-muted); font-size: 12px; }
.connection-version { color: var(--color-muted); font-size: 12px; margin-left: auto; }
.pve-alert { margin-top: -4px; }
.pve-metrics { margin-top: 0; }
.setup-panel { border-color: rgba(105, 185, 255, 0.28); }
.setup-body { display: grid; gap: 10px; }
.setup-body p, .setup-body small { margin: 0; }
.setup-body code { background: rgba(105, 185, 255, 0.08); border: 1px solid rgba(105, 185, 255, 0.16); border-radius: 8px; color: #bfe8ff; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; overflow-wrap: anywhere; padding: 10px 12px; }
.pve-grid { display: grid; gap: 16px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.resource-panel { min-width: 0; }
.resource-list, .task-list { display: grid; gap: 10px; }
.resource-row, .task-row { align-items: center; border-bottom: 1px solid rgba(148, 163, 184, 0.1); display: flex; gap: 12px; justify-content: space-between; min-width: 0; padding: 4px 0 11px; }
.resource-row:last-child, .task-row:last-child { border-bottom: 0; padding-bottom: 0; }
.resource-name, .resource-values, .task-row > div { align-items: center; display: flex; gap: 8px; min-width: 0; }
.resource-name strong, .task-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.resource-values { color: var(--color-muted); flex-wrap: wrap; font-size: 12px; justify-content: flex-end; }
.type-badge { border: 1px solid rgba(105, 185, 255, 0.24); border-radius: 5px; color: #9ddcff; font-size: 10px; font-weight: 750; padding: 2px 5px; }
.storage-row { display: grid; gap: 7px; padding-bottom: 3px; }
.storage-heading { align-items: center; display: flex; justify-content: space-between; }
.storage-heading span { color: var(--color-primary); font-variant-numeric: tabular-nums; font-size: 12px; }
.storage-meta { overflow-wrap: anywhere; }
.task-filter { width: 108px; }
.usage-track { background: rgba(148, 163, 184, 0.12); border-radius: 999px; height: 6px; overflow: hidden; }
.usage-track span { background: linear-gradient(90deg, var(--color-primary-strong), #7dd3fc); border-radius: inherit; display: block; height: 100%; transition: width 240ms ease; }
.task-row > div { display: grid; gap: 3px; }
.task-status-tag { flex: 0 1 52%; height: auto; line-height: 1.35; max-width: 52%; min-width: 0; overflow-wrap: anywhere; text-align: left; white-space: normal; }
:deep(.task-status-tag .el-tag__content) { overflow-wrap: anywhere; white-space: normal; }
.empty-inline { color: var(--color-muted); font-size: 13px; padding: 8px 0; }
@media (max-width: 920px) { .pve-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) {
  .pve-header, .header-actions { align-items: stretch; flex-direction: column; }
  .connection-panel { align-items: flex-start; }
  .connection-version { margin-left: auto; }
  .resource-row, .task-row { align-items: flex-start; flex-direction: column; }
  .resource-values { justify-content: flex-start; padding-left: 17px; }
}
</style>
