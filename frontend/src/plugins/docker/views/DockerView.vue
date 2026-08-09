<template>
  <div class="docker-page">
    <section class="page-header"><div><h1 class="page-title">Docker</h1><p class="page-subtitle">只读查看容器、镜像和数据卷状态。HAP 不提供删除、重启或命令入口。</p></div><div class="header-actions"><span class="last-refresh">{{ refreshedAtLabel }}</span><el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新状态</el-button></div></section>
    <section class="panel connection-panel" :class="connectionClass"><div class="connection-indicator" aria-hidden="true"></div><div class="connection-copy"><strong>{{ connectionTitle }}</strong><span>{{ connectionMessage }}</span></div><span class="connection-version">{{ status?.docker_version ? `Docker ${status.docker_version}` : '只读监控' }}</span></section>
    <el-alert v-if="errorMessage" class="docker-alert" type="warning" :closable="false" show-icon :title="errorMessage" />
    <div class="grid metrics"><MetricCard label="容器" :value="String(status?.containers ?? containers.length)" meta="已发现的容器" :delay="60" /><MetricCard label="运行中" :value="String(status?.running ?? runningCount)" meta="当前 running 容器" :delay="110" /><MetricCard label="镜像" :value="String(images.length)" meta="本地镜像数量" :delay="160" /><MetricCard label="数据卷" :value="String(volumes.length)" meta="已发现的数据卷" :delay="210" /></div>
    <div v-if="!status?.configured" class="panel setup-panel"><div class="panel-header"><div><h2 class="panel-title">等待配置只读连接</h2><span class="panel-meta">默认关闭 Docker 访问，避免未授权读取 Docker Socket。</span></div><el-tag type="info" effect="dark">未配置</el-tag></div><div class="panel-body setup-body"><p>在 Docker Stack 环境变量中开启 Docker 监控，然后重新部署 HAP。</p><code>DOCKER_ENABLED=true</code><small>连接通过内部 Docker Socket Proxy，代理不发布宿主机端口，并禁用写入和删除操作。</small></div></div>
    <div v-else class="docker-grid">
      <section class="panel data-panel container-panel"><div class="panel-header"><div><h2 class="panel-title">容器</h2><span class="panel-meta">状态、资源和端口概览</span></div><el-tag v-if="containers.length" type="success" effect="dark">{{ runningCount }} 个运行中</el-tag></div><div class="panel-body table-wrap"><table class="data-table"><thead><tr><th>名称</th><th>状态</th><th>CPU</th><th>内存</th><th>网络</th><th>镜像</th><th>端口</th></tr></thead><tbody><tr v-for="container in containers" :key="String(container.Id ?? container.Names)"><td><strong>{{ containerName(container) }}</strong></td><td><span class="state"><i :class="['status-dot', containerStatusClass(container)]"></i>{{ text(container.Status, '未知') }}</span></td><td>{{ statText(container, 'cpu_percent', '%') }}</td><td>{{ memoryText(container) }}</td><td>{{ networkText(container) }}</td><td class="truncate">{{ text(container.Image, '--') }}</td><td>{{ ports(container.Ports) }}</td></tr></tbody></table><div v-if="!containers.length" class="empty-inline">暂无容器数据</div></div></section>
      <section class="panel data-panel"><div class="panel-header"><div><h2 class="panel-title">镜像</h2><span class="panel-meta">本地镜像与占用空间</span></div></div><div class="panel-body compact-list"><div v-for="image in images.slice(0, 8)" :key="String(image.Id)" class="list-row"><div><strong>{{ text(image.RepoTags, '无标签镜像') }}</strong><small>{{ text(image.Id, '--').slice(0, 19) }}</small></div><span>{{ imageSize(image.Size) }}</span></div><div v-if="!images.length" class="empty-inline">暂无镜像数据</div></div></section>
      <section class="panel data-panel"><div class="panel-header"><div><h2 class="panel-title">数据卷</h2><span class="panel-meta">名称和存储驱动</span></div></div><div class="panel-body compact-list"><div v-for="volume in volumes.slice(0, 8)" :key="String(volume.Name)" class="list-row"><div><strong>{{ text(volume.Name, '未命名卷') }}</strong><small>{{ text(volume.Mountpoint, '--') }}</small></div><span>{{ text(volume.Driver, 'local') }}</span></div><div v-if="!volumes.length" class="empty-inline">暂无数据卷</div></div></section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, onMounted, ref } from 'vue';
import MetricCard from '@/components/metric/MetricCard.vue';
import { fetchDockerContainerStats, fetchDockerContainers, fetchDockerImages, fetchDockerStatus, fetchDockerVolumes, type DockerStatus } from '@/plugins/docker/api';

const loading = ref(false); const status = ref<DockerStatus | null>(null); const containers = ref<Record<string, unknown>[]>([]); const images = ref<Record<string, unknown>[]>([]); const volumes = ref<Record<string, unknown>[]>([]); const errorMessage = ref(''); const refreshedAt = ref<Date | null>(null);
const runningCount = computed(() => containers.value.filter((item) => item.State === 'running').length);
const connectionClass = computed(() => !status.value?.configured ? 'is-muted' : status.value.reachable ? 'is-online' : 'is-warning');
const connectionTitle = computed(() => !status.value?.configured ? 'Docker 只读监控尚未配置' : status.value.reachable ? 'Docker API 连接正常' : 'Docker API 暂时不可达');
const connectionMessage = computed(() => !status.value?.configured ? '配置 DOCKER_ENABLED=true 并重新部署后，HAP 才会读取 Docker 状态。' : status.value.reachable ? '数据来自内部 Socket Proxy，只读模式已启用。' : status.value.error ?? '请检查 Docker Socket Proxy 和网络连接。');
const refreshedAtLabel = computed(() => refreshedAt.value ? `更新于 ${refreshedAt.value.toLocaleTimeString('zh-CN', { hour12: false })}` : '尚未更新');

function text(value: unknown, fallback: string): string { if (Array.isArray(value)) return value.join(', ') || fallback; return value === null || value === undefined || value === '' ? fallback : String(value); }
function containerName(container: Record<string, unknown>): string { const names = container.Names; return text(Array.isArray(names) ? names[0] : names, text(container.Id, '未命名容器').slice(0, 12)); }
function ports(value: unknown): string { if (!Array.isArray(value) || !value.length) return '--'; return value.slice(0, 3).map((port) => { const item = port as Record<string, unknown>; return item.PublicPort ? `${item.PublicPort}:${item.PrivatePort}` : `:${item.PrivatePort}`; }).join(', '); }
function imageSize(value: unknown): string { const bytes = Number(value); if (!Number.isFinite(bytes) || bytes <= 0) return '--'; const units = ['B', 'KB', 'MB', 'GB']; const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1); return `${(bytes / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`; }
function bytes(value: number): string { if (!Number.isFinite(value) || value <= 0) return '0 B'; const units = ['B', 'KB', 'MB', 'GB']; const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1); return `${(value / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`; }
function containerStatusClass(container: Record<string, unknown>): string { return container.State === 'running' ? 'is-running' : 'is-stopped'; }
function statText(container: Record<string, unknown>, key: string, suffix = ''): string { const stats = container.stats as Record<string, unknown> | undefined; const value = Number(stats?.[key]); return Number.isFinite(value) ? `${value.toFixed(1)}${suffix}` : '--'; }
function memoryText(container: Record<string, unknown>): string { const stats = container.stats as Record<string, unknown> | undefined; const usage = Number(stats?.memory_usage); const limit = Number(stats?.memory_limit); return Number.isFinite(usage) && Number.isFinite(limit) && limit ? `${bytes(usage)} / ${bytes(limit)}` : '--'; }
function networkText(container: Record<string, unknown>): string { const stats = container.stats as Record<string, unknown> | undefined; const rx = Number(stats?.network_rx); const tx = Number(stats?.network_tx); return Number.isFinite(rx) && Number.isFinite(tx) ? `↓${bytes(rx)} ↑${bytes(tx)}` : '--'; }

async function loadAll(): Promise<void> {
  loading.value = true; errorMessage.value = '';
  try {
    status.value = await fetchDockerStatus();
    const results = await Promise.allSettled([fetchDockerContainers(), fetchDockerImages(), fetchDockerVolumes()]);
    if (results[0].status === 'fulfilled') containers.value = results[0].value.data;
    if (results[1].status === 'fulfilled') images.value = results[1].value.data;
    if (results[2].status === 'fulfilled') volumes.value = results[2].value.data;
    if (results.some((result) => result.status === 'rejected')) errorMessage.value = '部分 Docker 资源读取失败，请稍后重试。';
    if (status.value.error) errorMessage.value = status.value.error;
    refreshedAt.value = new Date();
  } catch (error) { errorMessage.value = error instanceof Error ? error.message : 'Docker 状态读取失败'; }
  finally { loading.value = false; }
  void loadContainerStats();
}

async function loadContainerStats(): Promise<void> { try { const response = await fetchDockerContainerStats(); const statsById = new Map(response.data.map((item) => [String(item.id), item])); containers.value = containers.value.map((container) => ({ ...container, stats: statsById.get(String(container.Id)) })); } catch { if (!errorMessage.value) errorMessage.value = '容器资源统计读取失败，基础状态仍可用。'; } }
onMounted(loadAll);
</script>

<style scoped>
.docker-page { display: grid; gap: 16px; }.page-header { margin-bottom: 0; }.header-actions { align-items: center; display: flex; flex-wrap: wrap; gap: 12px; }.last-refresh { color: var(--color-muted); font-size: 12px; }.connection-panel { align-items: center; display: flex; gap: 12px; padding: 15px 18px; }.connection-panel.is-online { border-color: rgba(52, 211, 153, 0.32); }.connection-panel.is-warning { border-color: rgba(251, 191, 36, 0.42); }.connection-indicator, .status-dot { background: var(--color-muted); border-radius: 50%; flex: 0 0 auto; height: 10px; width: 10px; }.connection-panel.is-online .connection-indicator, .status-dot.is-running { background: #34d399; box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.12); }.connection-panel.is-warning .connection-indicator { background: #fbbf24; box-shadow: 0 0 0 4px rgba(251, 191, 36, 0.12); }.connection-copy { display: grid; gap: 2px; min-width: 0; flex: 1; }.connection-copy span, .panel-meta, .list-row small { color: var(--color-muted); font-size: 12px; }.connection-version { color: var(--color-muted); font-size: 12px; white-space: nowrap; }.docker-alert { margin: 0; }.docker-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(280px, .65fr); gap: 14px; }.container-panel { grid-row: span 2; }.data-panel { min-width: 0; overflow: hidden; }.panel-header { align-items: center; display: flex; justify-content: space-between; gap: 16px; }.table-wrap { overflow-x: auto; }.data-table { border-collapse: collapse; min-width: 800px; width: 100%; }.data-table th, .data-table td { border-bottom: 1px solid var(--color-border-soft); padding: 13px 14px; text-align: left; white-space: nowrap; }.data-table th { color: var(--color-muted); font-size: 12px; font-weight: 600; }.data-table td { font-size: 13px; }.data-table tr:last-child td { border-bottom: 0; }.state { align-items: center; display: inline-flex; gap: 8px; }.status-dot.is-stopped { background: #94a3b8; }.truncate { max-width: 260px; overflow: hidden; text-overflow: ellipsis; }.compact-list { display: grid; }.list-row { align-items: center; border-bottom: 1px solid var(--color-border-soft); display: flex; justify-content: space-between; gap: 16px; padding: 13px 0; }.list-row:last-child { border-bottom: 0; }.list-row > div { display: grid; gap: 3px; min-width: 0; }.list-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.list-row > span { color: var(--color-muted); font-size: 12px; white-space: nowrap; }.setup-body { display: grid; gap: 10px; }.setup-body p, .setup-body small { color: var(--color-muted); margin: 0; }.setup-body code { background: rgba(56, 189, 248, .06); border: 1px solid var(--color-border-soft); border-radius: 6px; color: #8bd5ff; padding: 7px 10px; width: fit-content; }.empty-inline { color: var(--color-muted); padding: 28px 0; text-align: center; }
@media (max-width: 900px) { .docker-grid { grid-template-columns: 1fr; }.container-panel { grid-row: auto; } } @media (max-width: 640px) { .page-header, .connection-panel { align-items: flex-start; flex-direction: column; }.header-actions { justify-content: space-between; width: 100%; }.connection-version { align-self: flex-end; } }
</style>
