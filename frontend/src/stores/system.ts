import { defineStore } from 'pinia';

import { getApiData, postApiData } from '@/api/client';

export interface HealthStatus {
  status: string;
  version: string;
  database: string;
}

export interface DatabaseBackup {
  file_name: string;
  size_bytes: number;
  created_at: string;
}

export interface DatabaseRestoreResult {
  source_file_name: string;
  safety_backup_file_name: string;
  status: string;
  message: string;
  restored_at: string;
}

export interface DatabaseRestoreRun {
  source_file_name: string;
  safety_backup_file_name: string;
  status: string;
  message: string;
  started_at: string;
  finished_at: string | null;
  created_at: string;
}

export type NotificationChannel = 'all' | 'bark' | 'wecom' | 'whatsapp' | 'custom_webhook';

export interface NotificationChannelStatus {
  channel: NotificationChannel;
  label: string;
  enabled: boolean;
  configured: boolean;
  description: string;
  target: string;
}

export interface NotificationStatus {
  channels: NotificationChannelStatus[];
  default_channel: NotificationChannel;
  supports_imessage_bridge: boolean;
  note: string;
}

export interface NotificationSendResult {
  channel: NotificationChannel;
  status: 'sent' | 'skipped' | 'failed';
  message: string;
  sent_at: string | null;
  provider_message_id: string | null;
}

export interface NotificationTestResult {
  requested_channel: NotificationChannel;
  results: NotificationSendResult[];
}

interface DatabaseRestorePayload {
  file_name: string;
  confirmation: string;
}

interface NotificationTestPayload {
  channel: NotificationChannel;
  title: string;
  message: string;
}

export interface DatabaseBackupList {
  items: DatabaseBackup[];
  directory: string;
  database_engine: string;
  retention_count: number;
  total_size_bytes: number;
  latest_restore: DatabaseRestoreRun | null;
  restore_runs: DatabaseRestoreRun[];
  scheduler: {
    enabled?: boolean;
    running?: boolean;
    cron?: string;
    timezone?: string;
    next_run_at?: string | null;
    last_run_at?: string | null;
    last_status?: string | null;
    last_message?: string | null;
    last_backup_file_name?: string | null;
    remote?: {
      enabled?: boolean;
      configured?: boolean;
      repo?: string;
      release_tag?: string;
      last_status?: string | null;
      last_message?: string | null;
      last_asset_name?: string | null;
      last_uploaded_at?: string | null;
    };
  };
}

export const useSystemStore = defineStore('system', {
  state: () => ({
    health: null as HealthStatus | null,
    backups: null as DatabaseBackupList | null,
    notifications: null as NotificationStatus | null,
    loading: false,
    backupLoading: false,
    notificationLoading: false,
    error: '',
    backupError: '',
    notificationError: '',
  }),
  actions: {
    async fetchHealth(): Promise<void> {
      this.loading = true;
      this.error = '';
      try {
        this.health = await getApiData<HealthStatus>('/system/health');
      } catch (error) {
        this.health = null;
        this.error = error instanceof Error ? error.message : 'Backend is not reachable';
      } finally {
        this.loading = false;
      }
    },
    async fetchBackups(): Promise<void> {
      this.backupLoading = true;
      this.backupError = '';
      try {
        this.backups = await getApiData<DatabaseBackupList>('/system/backups');
      } catch (error) {
        this.backups = null;
        this.backupError = error instanceof Error ? error.message : '无法读取备份列表';
      } finally {
        this.backupLoading = false;
      }
    },
    async fetchNotifications(): Promise<void> {
      this.notificationLoading = true;
      this.notificationError = '';
      try {
        this.notifications = await getApiData<NotificationStatus>('/system/notifications');
      } catch (error) {
        this.notifications = null;
        this.notificationError = error instanceof Error ? error.message : '无法读取推送配置';
      } finally {
        this.notificationLoading = false;
      }
    },
    async sendNotificationTest(payload: NotificationTestPayload): Promise<NotificationTestResult> {
      this.notificationLoading = true;
      this.notificationError = '';
      try {
        const result = await postApiData<NotificationTestResult, NotificationTestPayload>(
          '/system/notifications/test',
          payload,
        );
        await this.fetchNotifications();
        return result;
      } catch (error) {
        this.notificationError = error instanceof Error ? error.message : '推送测试失败';
        throw error;
      } finally {
        this.notificationLoading = false;
      }
    },
    async createBackup(): Promise<DatabaseBackup> {
      this.backupLoading = true;
      this.backupError = '';
      try {
        const backup = await postApiData<DatabaseBackup, Record<string, never>>('/system/backups', {});
        await this.fetchBackups();
        return backup;
      } catch (error) {
        this.backupError = error instanceof Error ? error.message : '数据库备份失败';
        throw error;
      } finally {
        this.backupLoading = false;
      }
    },
    async restoreBackup(fileName: string, confirmation: string): Promise<DatabaseRestoreResult> {
      this.backupLoading = true;
      this.backupError = '';
      try {
        const result = await postApiData<DatabaseRestoreResult, DatabaseRestorePayload>(
          `/system/backups/${encodeURIComponent(fileName)}/restore`,
          { file_name: fileName, confirmation },
        );
        await this.fetchBackups();
        return result;
      } catch (error) {
        this.backupError = error instanceof Error ? error.message : '数据库恢复失败';
        throw error;
      } finally {
        this.backupLoading = false;
      }
    },
  },
});
