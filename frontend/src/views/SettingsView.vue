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
              <code>{{ backupDirectory }}</code>。它不会上传到 GitHub，也不会覆盖正在使用的数据。
            </p>
            <p>
              现在先提供“创建备份”和“查看备份”。恢复数据库属于高风险操作，
              后续会做成带确认、停服务和回滚记录的独立流程。
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
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" @click="downloadBackup(row.file_name)">
                  下载
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
import { FolderChecked, Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { computed, onMounted } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import { useSystemStore } from '@/stores/system';

const system = useSystemStore();

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
const latestBackupTime = computed(() => {
  const latest = system.backups?.items[0];
  return latest ? formatDateTime(latest.created_at) : '暂无';
});

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

onMounted(() => {
  void system.fetchBackups();
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

@media (max-width: 760px) {
  .backup-summary {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 761px) and (max-width: 1100px) {
  .backup-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
