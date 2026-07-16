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

export interface DatabaseBackupList {
  items: DatabaseBackup[];
  directory: string;
  database_engine: string;
  retention_count: number;
  total_size_bytes: number;
}

export const useSystemStore = defineStore('system', {
  state: () => ({
    health: null as HealthStatus | null,
    backups: null as DatabaseBackupList | null,
    loading: false,
    backupLoading: false,
    error: '',
    backupError: '',
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
  },
});
