<template>
  <div>
    <section class="page-header">
      <div>
        <h1 class="page-title">Settings</h1>
        <div class="page-subtitle">平台配置、插件配置、数据源与备份策略</div>
      </div>
    </section>
    <section class="settings-grid">
      <div class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">数据库备份</h2>
            <div class="panel-hint">保护 Docker Volume 里的 SQLite 数据</div>
          </div>
          <el-button :icon="Refresh" :loading="system.backupLoading" @click="reloadBackups">
            刷新
          </el-button>
        </div>
        <div class="panel-body">
          <div class="backup-summary">
            <div class="backup-summary-item">
              <span>数据库</span>
              <strong>{{ databaseEngine }}</strong>
            </div>
            <div class="backup-summary-item">
              <span>备份数量</span>
              <strong>{{ backupCount }}</strong>
            </div>
            <div class="backup-summary-item">
              <span>最近备份</span>
              <strong>{{ latestBackupTime }}</strong>
            </div>
            <div class="backup-summary-item">
              <span>备份总大小</span>
              <strong>{{ totalBackupSize }}</strong>
            </div>
          </div>

          <div class="explain-box">
            <div class="explain-title">这是什么意思？</div>
            <p>
              备份会把当前 SQLite 数据库复制一份到 Docker 的备份卷里，路径是
              <code>{{ backupDirectory }}</code>。如果 GitHub 远程备份已配置，会同时上传一份加密副本。
              备份不会覆盖正在使用的数据。
            </p>
            <p>
              恢复数据库属于高风险操作，需要输入确认短语才会执行；
              系统会在恢复前先创建一份安全备份，并记录恢复审计。
            </p>
            <p>
              当前建议最多保留 {{ retentionCount }} 份备份；后续会增加自动清理和恢复审计。
            </p>
          </div>

          <div class="scheduler-box">
            <div class="scheduler-status">
              <span class="status-dot" :class="{ online: autoBackupRunning }" />
              <strong>{{ autoBackupStatusText }}</strong>
            </div>
            <div class="scheduler-meta">
              <span>计划：{{ autoBackupCron }}</span>
              <span>下次：{{ nextAutoBackupTime }}</span>
              <span>最近：{{ lastAutoBackupText }}</span>
            </div>
          </div>

          <div class="remote-box">
            <div class="scheduler-status">
              <span class="status-dot" :class="{ online: githubBackupReady }" />
              <strong>{{ githubBackupStatusText }}</strong>
            </div>
            <div class="scheduler-meta">
              <span>仓库：{{ githubBackupRepo }}</span>
              <span>Release：{{ githubBackupReleaseTag }}</span>
              <span>最近：{{ lastGithubBackupText }}</span>
            </div>
            <p>
              远程备份会先压缩并加密数据库，再上传到 GitHub Release；Token 和加密密码只通过后端环境变量配置，不会在页面显示。
            </p>
            <p>
              推荐使用单独的私有备份仓库，Token 只授予该仓库 Contents 读写权限。
            </p>
          </div>

          <div class="restore-box">
            <div class="scheduler-status">
              <span class="status-dot" :class="{ online: latestRestoreSuccess }" />
              <strong>{{ latestRestoreStatusText }}</strong>
              <el-tag v-if="latestRestore" size="small" :type="latestRestoreTagType">
                {{ latestRestore.status }}
              </el-tag>
            </div>
            <div class="scheduler-meta">
              <span>最近恢复：{{ latestRestoreTime }}</span>
              <span>审计记录：{{ restoreRunCount }}</span>
            </div>
            <p v-if="latestRestore">
              从 <code>{{ latestRestore.source_file_name }}</code> 恢复；
              恢复前安全备份为 <code>{{ latestRestore.safety_backup_file_name }}</code>。
            </p>
            <p v-else>
              还没有执行过数据库恢复。只有输入确认短语后，恢复动作才会写入这里。
            </p>
            <el-table
              v-if="system.backups?.restore_runs.length"
              :data="system.backups.restore_runs"
              class="restore-table"
              size="small"
            >
              <el-table-column prop="source_file_name" label="来源备份" min-width="210" />
              <el-table-column prop="safety_backup_file_name" label="安全备份" min-width="230" />
              <el-table-column label="状态" width="110">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'success' ? 'success' : 'danger'">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="恢复时间" min-width="180">
                <template #default="{ row }">
                  {{ formatDateTime(row.created_at) }}
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="backup-actions">
            <el-button type="primary" :icon="FolderChecked" :loading="system.backupLoading" @click="createBackup">
              创建当前数据库备份
            </el-button>
            <span v-if="system.backupError" class="error-text">{{ system.backupError }}</span>
          </div>

          <el-table
            v-if="system.backups?.items.length"
            :data="system.backups.items"
            class="backup-table"
            size="small"
          >
            <el-table-column prop="file_name" label="备份文件" min-width="210" />
            <el-table-column label="大小" width="120">
              <template #default="{ row }">
                {{ formatBytes(row.size_bytes) }}
              </template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="downloadBackup(row.file_name)">
                  下载
                </el-button>
                <el-button text type="danger" @click="restoreBackup(row.file_name)">
                  恢复
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <EmptyState
            v-else
            title="还没有数据库备份"
            description="点击“创建当前数据库备份”后，会在 Docker 数据卷中生成一份 SQLite 备份。"
          />
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">推送通知</h2>
            <div class="panel-hint">开奖提醒、日报、备份异常和系统告警会复用这里的通道</div>
          </div>
          <el-button :icon="Refresh" :loading="system.notificationLoading" @click="reloadNotifications">
            刷新
          </el-button>
        </div>
        <div class="panel-body">
          <div class="notification-summary">
            <div class="scheduler-status">
              <span class="status-dot" :class="{ online: notificationReadyCount > 0 }" />
              <strong>{{ notificationStatusText }}</strong>
            </div>
            <p>{{ system.notifications?.note ?? '推送配置只从后端环境变量读取，页面不会显示密钥。' }}</p>
          </div>

          <div class="notification-grid">
            <div
              v-for="channel in notificationChannels"
              :key="channel.channel"
              class="notification-card"
            >
              <div class="notification-card-header">
                <strong>{{ channel.label }}</strong>
                <div class="notification-tags">
                  <el-tag size="small" :type="channel.enabled ? 'success' : 'info'">
                    {{ channel.enabled ? '已启用' : '未启用' }}
                  </el-tag>
                  <el-tag size="small" :type="channel.configured ? 'success' : 'warning'">
                    {{ channel.configured ? '已配置' : '未配置' }}
                  </el-tag>
                </div>
              </div>
              <p>{{ channel.description }}</p>
              <div class="notification-target">{{ channel.target }}</div>
            </div>
          </div>

          <div class="notification-test-form">
            <el-form label-position="top">
              <el-form-item label="推送通道">
                <el-select v-model="notificationForm.channel" class="notification-select">
                  <el-option
                    v-for="option in notificationChannelOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="标题">
                <el-input v-model="notificationForm.title" maxlength="120" show-word-limit />
              </el-form-item>
              <el-form-item label="内容">
                <el-input
                  v-model="notificationForm.message"
                  type="textarea"
                  :rows="3"
                  maxlength="2048"
                  show-word-limit
                />
              </el-form-item>
              <div class="backup-actions">
                <el-button
                  type="primary"
                  :icon="Bell"
                  :loading="system.notificationLoading"
                  @click="sendNotificationTest"
                >
                  发送测试
                </el-button>
                <span v-if="system.notificationError" class="error-text">{{ system.notificationError }}</span>
              </div>
            </el-form>
          </div>

          <div v-if="notificationResults.length" class="notification-result-list">
            <div
              v-for="result in notificationResults"
              :key="`${result.channel}-${result.status}`"
              class="notification-result-item"
            >
              <el-tag size="small" :type="notificationResultTagType(result.status)">
                {{ notificationResultStatusText(result.status) }}
              </el-tag>
              <span>{{ notificationChannelLabel(result.channel) }}</span>
              <em>{{ result.message }}</em>
            </div>
          </div>

          <div class="notification-history">
            <div class="notification-history-header">
              <div>
                <strong>最近推送记录</strong>
                <span>记录最近 {{ notificationRunCount }} 条发送、跳过和失败结果</span>
              </div>
              <el-button text :icon="Refresh" :loading="system.notificationLoading" @click="reloadNotificationRuns">
                刷新记录
              </el-button>
            </div>
            <el-table
              v-if="notificationRuns.length"
              :data="notificationRuns"
              class="notification-history-table"
              size="small"
            >
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="notificationResultTagType(row.status)">
                    {{ notificationResultStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="通道" width="130">
                <template #default="{ row }">
                  {{ notificationChannelLabel(row.channel) }}
                </template>
              </el-table-column>
              <el-table-column label="来源" width="130">
                <template #default="{ row }">
                  {{ notificationSourceLabel(row.source) }}
                </template>
              </el-table-column>
              <el-table-column label="标题 / 摘要" min-width="260">
                <template #default="{ row }">
                  <div class="notification-history-title">{{ row.title }}</div>
                  <div class="notification-history-message">{{ row.message_preview }}</div>
                </template>
              </el-table-column>
              <el-table-column label="结果" min-width="180">
                <template #default="{ row }">
                  {{ row.result_message }}
                </template>
              </el-table-column>
              <el-table-column label="时间" width="170">
                <template #default="{ row }">
                  {{ formatDateTime(row.created_at) }}
                </template>
              </el-table-column>
            </el-table>
            <EmptyState
              v-else
              title="暂无推送记录"
              description="发送测试通知或等待同步任务推送后，这里会显示最近记录。"
            />
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">后续配置中心</h2>
            <div class="panel-hint">插件配置、数据源、同步策略会逐步放到这里</div>
          </div>
        </div>
        <div class="panel-body">
          <EmptyState title="设置项待接入" description="后续会由 Core 和各插件共同提供配置 schema。" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Bell, FolderChecked, Refresh } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import {
  type NotificationChannel,
  type NotificationDeliveryRun,
  type NotificationSendResult,
  useSystemStore,
} from '@/stores/system';

const system = useSystemStore();
const RESTORE_CONFIRMATION = 'RESTORE HAP DATABASE';
const notificationForm = ref({
  channel: 'all' as NotificationChannel,
  title: 'HAP 通知测试',
  message: '如果你收到这条消息，说明 Home Analytics Platform 推送通道已经连通。',
});
const notificationResults = ref<NotificationSendResult[]>([]);

const backupCount = computed(() => String(system.backups?.items.length ?? 0));
const databaseEngine = computed(() => system.backups?.database_engine.toUpperCase() ?? 'SQLITE');
const backupDirectory = computed(() => system.backups?.directory ?? '/app/data/sqlite/backups');
const retentionCount = computed(() => system.backups?.retention_count ?? 30);
const totalBackupSize = computed(() => formatBytes(system.backups?.total_size_bytes ?? 0));
const autoBackupRunning = computed(() => Boolean(system.backups?.scheduler.running));
const autoBackupStatusText = computed(() => {
  if (!system.backups?.scheduler.enabled) {
    return '自动备份已关闭';
  }
  return autoBackupRunning.value ? '自动备份运行中' : '自动备份未运行';
});
const autoBackupCron = computed(() => system.backups?.scheduler.cron ?? '10 3 * * *');
const nextAutoBackupTime = computed(() => {
  const value = system.backups?.scheduler.next_run_at;
  return value ? formatDateTime(value) : '暂无';
});
const lastAutoBackupText = computed(() => {
  const scheduler = system.backups?.scheduler;
  if (!scheduler?.last_run_at) {
    return '暂无自动备份记录';
  }
  const status = scheduler.last_status === 'success' ? '成功' : '失败';
  return `${formatDateTime(scheduler.last_run_at)} · ${status}`;
});
const githubBackup = computed(() => system.backups?.scheduler.remote ?? {});
const githubBackupReady = computed(() => {
  return Boolean(githubBackup.value.enabled && githubBackup.value.configured);
});
const githubBackupStatusText = computed(() => {
  if (!githubBackup.value.enabled) {
    return 'GitHub 远程备份已关闭';
  }
  if (!githubBackup.value.configured) {
    return 'GitHub 远程备份未配置完整';
  }
  return 'GitHub 加密远程备份已就绪';
});
const githubBackupRepo = computed(() => githubBackup.value.repo || '未配置');
const githubBackupReleaseTag = computed(() => githubBackup.value.release_tag || 'hap-backups');
const lastGithubBackupText = computed(() => {
  if (!githubBackup.value.last_uploaded_at) {
    return githubBackup.value.last_message || '暂无远程备份记录';
  }
  const asset = githubBackup.value.last_asset_name ?? '加密备份';
  return `${formatDateTime(githubBackup.value.last_uploaded_at)} · ${asset}`;
});
const latestRestore = computed(() => system.backups?.latest_restore ?? null);
const latestRestoreSuccess = computed(() => latestRestore.value?.status === 'success');
const latestRestoreStatusText = computed(() => {
  if (!latestRestore.value) {
    return '暂无数据库恢复记录';
  }
  return latestRestoreSuccess.value ? '最近恢复成功' : '最近恢复异常';
});
const latestRestoreTagType = computed(() => {
  return latestRestoreSuccess.value ? 'success' : 'danger';
});
const latestRestoreTime = computed(() => {
  return latestRestore.value ? formatDateTime(latestRestore.value.created_at) : '暂无';
});
const restoreRunCount = computed(() => String(system.backups?.restore_runs.length ?? 0));
const latestBackupTime = computed(() => {
  const latest = system.backups?.items[0];
  return latest ? formatDateTime(latest.created_at) : '暂无';
});
const notificationChannels = computed(() => system.notifications?.channels ?? []);
const notificationRuns = computed<NotificationDeliveryRun[]>(() => system.notificationRuns?.items ?? []);
const notificationRunCount = computed(() => String(notificationRuns.value.length));
const notificationReadyCount = computed(() => {
  return notificationChannels.value.filter((channel) => channel.enabled && channel.configured).length;
});
const notificationStatusText = computed(() => {
  if (!system.notifications) {
    return '推送状态待读取';
  }
  if (notificationReadyCount.value === 0) {
    return '暂无可用推送通道';
  }
  return `${notificationReadyCount.value} 个推送通道已就绪`;
});
const notificationChannelOptions = computed(() => [
  { label: '全部已启用通道', value: 'all' as NotificationChannel },
  ...notificationChannels.value.map((channel) => ({
    label: channel.label,
    value: channel.channel,
  })),
]);

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / 1024 / 1024).toFixed(2)} MB`;
}

async function reloadBackups(): Promise<void> {
  await system.fetchBackups();
}

async function reloadNotifications(): Promise<void> {
  await system.fetchNotifications();
}

async function reloadNotificationRuns(): Promise<void> {
  await system.fetchNotificationRuns();
}

async function createBackup(): Promise<void> {
  try {
    const backup = await system.createBackup();
    ElMessage.success(`备份已创建：${backup.file_name}`);
  } catch {
    ElMessage.error('数据库备份失败，请查看后端日志。');
  }
}

function downloadBackup(fileName: string): void {
  window.location.href = `/api/v1/system/backups/${encodeURIComponent(fileName)}/download`;
}

async function restoreBackup(fileName: string): Promise<void> {
  try {
    const promptMessage = [
      `恢复会先创建安全备份，然后用 ${fileName} 替换当前 SQLite 数据库。`,
      `请输入 ${RESTORE_CONFIRMATION} 确认。`,
    ].join('');
    const { value } = await ElMessageBox.prompt(
      promptMessage,
      '恢复数据库',
      {
        confirmButtonText: '确认恢复',
        cancelButtonText: '取消',
        inputPattern: /^RESTORE HAP DATABASE$/,
        inputErrorMessage: `请输入 ${RESTORE_CONFIRMATION}`,
        type: 'warning',
        distinguishCancelAndClose: true,
      },
    );
    const result = await system.restoreBackup(fileName, String(value ?? ''));
    ElMessage.success(`数据库已恢复，安全备份：${result.safety_backup_file_name}`);
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return;
    }
    ElMessage.error('数据库恢复失败，请查看后端日志。');
  }
}

async function sendNotificationTest(): Promise<void> {
  try {
    const result = await system.sendNotificationTest(notificationForm.value);
    notificationResults.value = result.results;
    const sentCount = result.results.filter((item) => item.status === 'sent').length;
    if (sentCount > 0) {
      ElMessage.success(`推送测试完成：${sentCount} 个通道发送成功`);
      return;
    }
    ElMessage.warning('推送测试完成，但没有通道成功发送。');
  } catch {
    ElMessage.error('推送测试失败，请查看后端日志。');
  }
}

function notificationChannelLabel(channel: NotificationChannel): string {
  if (channel === 'all') {
    return '全部通道';
  }
  return notificationChannels.value.find((item) => item.channel === channel)?.label ?? channel;
}

function notificationSourceLabel(source: string): string {
  const sourceMap: Record<string, string> = {
    manual_test: '手动测试',
    lottery_dlt_sync: '大乐透同步',
  };
  return sourceMap[source] ?? source;
}

function notificationResultStatusText(status: NotificationSendResult['status']): string {
  const statusMap: Record<NotificationSendResult['status'], string> = {
    sent: '已发送',
    skipped: '已跳过',
    failed: '失败',
  };
  return statusMap[status];
}

function notificationResultTagType(status: NotificationSendResult['status']): 'success' | 'warning' | 'danger' {
  if (status === 'sent') {
    return 'success';
  }
  return status === 'skipped' ? 'warning' : 'danger';
}

onMounted(() => {
  void system.fetchBackups();
  void system.fetchNotifications();
});
</script>

<style scoped>
.settings-grid {
  display: grid;
  gap: 16px;
}

.panel-hint {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 12px;
}

.backup-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.backup-summary-item {
  min-width: 0;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.42);
  padding: 12px;
}

.backup-summary-item span {
  display: block;
  color: var(--color-muted);
  font-size: 12px;
}

.backup-summary-item strong {
  display: block;
  margin-top: 7px;
  overflow-wrap: anywhere;
  color: var(--color-text);
  font-size: 17px;
}

.explain-box {
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 8px;
  background: rgba(56, 189, 248, 0.08);
  color: var(--color-muted);
  line-height: 1.7;
  margin-bottom: 14px;
  padding: 13px 14px;
}

.explain-box p {
  margin: 6px 0 0;
}

.explain-box code {
  color: var(--color-primary);
}

.explain-title {
  color: var(--color-text);
  font-weight: 650;
}

.backup-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}

.scheduler-box {
  display: grid;
  gap: 8px;
  border: 1px solid rgba(34, 197, 94, 0.18);
  border-radius: 8px;
  background: rgba(34, 197, 94, 0.07);
  margin-bottom: 14px;
  padding: 12px 14px;
}

.remote-box {
  display: grid;
  gap: 8px;
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: 8px;
  background: rgba(167, 139, 250, 0.08);
  color: var(--color-muted);
  line-height: 1.6;
  margin-bottom: 14px;
  padding: 12px 14px;
}

.remote-box p {
  margin: 0;
}

.restore-box {
  display: grid;
  gap: 8px;
  border: 1px solid rgba(251, 191, 36, 0.22);
  border-radius: 8px;
  background: rgba(251, 191, 36, 0.08);
  color: var(--color-muted);
  line-height: 1.6;
  margin-bottom: 14px;
  padding: 12px 14px;
}

.restore-box p {
  margin: 0;
}

.restore-box code {
  color: var(--color-warning);
}

.notification-summary {
  display: grid;
  gap: 8px;
  border: 1px solid rgba(45, 212, 191, 0.2);
  border-radius: 8px;
  background: rgba(45, 212, 191, 0.07);
  color: var(--color-muted);
  line-height: 1.6;
  margin-bottom: 14px;
  padding: 12px 14px;
}

.notification-summary p {
  margin: 0;
}

.notification-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.notification-card {
  min-width: 0;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.42);
  padding: 12px;
}

.notification-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.notification-card-header strong {
  color: var(--color-text);
}

.notification-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.notification-card p {
  min-height: 40px;
  margin: 9px 0;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.55;
}

.notification-target {
  overflow-wrap: anywhere;
  border-radius: 6px;
  background: rgba(2, 6, 23, 0.38);
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 7px 8px;
}

.notification-test-form {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  background: rgba(2, 6, 23, 0.2);
  margin-bottom: 14px;
  padding: 14px;
}

.notification-select {
  width: min(100%, 320px);
}

.notification-result-list {
  display: grid;
  gap: 8px;
}

.notification-result-item {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.34);
  padding: 9px 10px;
}

.notification-result-item span {
  color: var(--color-text);
  font-weight: 650;
}

.notification-result-item em {
  color: var(--color-muted);
  font-style: normal;
}

.notification-history {
  display: grid;
  gap: 10px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  background: rgba(2, 6, 23, 0.18);
  margin-top: 14px;
  padding: 14px;
}

.notification-history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.notification-history-header strong {
  display: block;
  color: var(--color-text);
  font-size: 15px;
}

.notification-history-header span {
  display: block;
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 12px;
}

.notification-history-table {
  width: 100%;
}

.notification-history-title {
  color: var(--color-text);
  font-weight: 650;
}

.notification-history-message {
  color: var(--color-muted);
  font-size: 12px;
  margin-top: 3px;
  overflow-wrap: anywhere;
}

.scheduler-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.scheduler-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  color: var(--color-muted);
  font-size: 13px;
}

.error-text {
  color: var(--color-danger);
  font-size: 13px;
}

.backup-table {
  width: 100%;
}

.restore-table {
  width: 100%;
}

@media (max-width: 760px) {
  .backup-summary {
    grid-template-columns: 1fr;
  }

  .notification-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 761px) and (max-width: 1100px) {
  .backup-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .notification-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
