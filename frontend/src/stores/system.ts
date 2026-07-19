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

export interface NotificationDeliveryRun {
  id: number;
  source: string;
  channel: NotificationChannel;
  status: 'sent' | 'skipped' | 'failed';
  title: string;
  message_preview: string;
  result_message: string;
  provider_message_id: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface NotificationDeliveryRunPage {
  items: NotificationDeliveryRun[];
  total: number;
  limit: number;
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
    notificationRuns: null as NotificationDeliveryRunPage | null,
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
        this.backupError = error instanceof Error ? error.message : '\u65e0\u6cd5\u8bfb\u53d6\u5907\u4efd\u5217\u8868';
      } finally {
        this.backupLoading = false;
      }
    },
    async fetchNotifications(): Promise<void> {
      this.notificationLoading = true;
      this.notificationError = '';
      try {
        const [notifications, notificationRuns] = await Promise.all([
          getApiData<NotificationStatus>('/system/notifications'),
          getApiData<NotificationDeliveryRunPage>('/system/notifications/runs?limit=20'),
        ]);
        this.notifications = notifications;
        this.notificationRuns = notificationRuns;
      } catch (error) {
        this.notifications = null;
        this.notificationRuns = null;
        this.notificationError = error instanceof Error ? error.message : '\u65e0\u6cd5\u8bfb\u53d6\u63a8\u9001\u914d\u7f6e';
      } finally {
        this.notificationLoading = false;
      }
    },
    async fetchNotificationRuns(): Promise<void> {
      try {
        this.notificationRuns = await getApiData<NotificationDeliveryRunPage>('/system/notifications/runs?limit=20');
      } catch (error) {
        this.notificationRuns = null;
        this.notificationError = error instanceof Error ? error.message : '\u65e0\u6cd5\u8bfb\u53d6\u63a8\u9001\u8bb0\u5f55';
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
        this.notificationError = error instanceof Error ? error.message : '\u63a8\u9001\u6d4b\u8bd5\u5931\u8d25';
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
        this.backupError = error instanceof Error ? error.message : '\u6570\u636e\u5e93\u5907\u4efd\u5931\u8d25';
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
        this.backupError = error instanceof Error ? error.message : '\u6570\u636e\u5e93\u6062\u590d\u5931\u8d25';
        throw error;
      } finally {
        this.backupLoading = false;
      }
    },
  },
});
