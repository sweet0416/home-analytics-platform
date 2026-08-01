<template>
  <section class="panel freshness-panel">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">净值新鲜度</h2>
        <span class="panel-meta">按工作日估算数据滞后，不把周末直接算作过期</span>
      </div>
      <div class="freshness-actions">
        <el-select
          v-model="staleAfterBusinessDays"
          aria-label="境内基金净值滞后阈值"
          @change="loadFreshness"
        >
          <el-option
            v-for="option in thresholdOptions"
            :key="option"
            :label="`境内 ${option} 日`"
            :value="option"
          />
        </el-select>
        <el-select
          v-model="qdiiStaleAfterBusinessDays"
          aria-label="QDII 净值滞后阈值"
          @change="loadFreshness"
        >
          <el-option
            v-for="option in qdiiThresholdOptions"
            :key="option"
            :label="`QDII ${option} 日`"
            :value="option"
          />
        </el-select>
        <el-button
          :loading="profileSyncing"
          @click="syncProfiles"
        >
          校准类型
        </el-button>
        <el-button :icon="Refresh" :loading="loading" @click="loadFreshness">
          刷新
        </el-button>
      </div>
    </div>

    <div class="panel-body">
      <div v-if="freshness" class="freshness-summary">
        <div>
          <span>统计日期</span>
          <strong>{{ freshness.as_of_date }}</strong>
        </div>
        <div>
          <span>及时</span>
          <strong class="status-fresh">{{ freshness.fresh_count }}</strong>
        </div>
        <div>
          <span>滞后</span>
          <strong class="status-stale">{{ freshness.stale_count }}</strong>
        </div>
        <div>
          <span>缺失</span>
          <strong class="status-missing">{{ freshness.missing_count }}</strong>
        </div>
      </div>

      <p v-if="profileSyncMessage" class="profile-sync-message">
        {{ profileSyncMessage }}
      </p>

      <div v-if="freshness?.items.length" class="freshness-table">
        <div class="freshness-row table-head">
          <span>基金</span>
          <span>最新净值</span>
          <span>滞后 / 阈值</span>
          <span>来源</span>
          <span>状态</span>
        </div>
        <div
          v-for="item in freshness.items"
          :key="item.fund_code"
          class="freshness-row"
        >
          <span>
            <strong>{{ item.fund_name }}</strong>
            <small>{{ item.fund_code }} · {{ item.account_names.join('、') }}</small>
          </span>
          <span>{{ item.latest_nav_date ?? '--' }}</span>
          <span>{{ ageText(item.business_day_age, item.allowed_business_days) }}</span>
          <span>{{ item.source ?? '--' }}</span>
          <span :class="['freshness-status', `is-${item.status}`]">
            {{ statusText(item.status) }}
          </span>
        </div>
      </div>

      <div v-else-if="loading" class="freshness-message">正在检查持仓净值日期...</div>
      <div v-else-if="errorMessage" class="freshness-message is-error">
        {{ errorMessage }}
      </div>
      <div v-else class="freshness-message">录入持仓后，这里会逐只检查最新净值日期。</div>

      <p class="freshness-note">
        工作日口径仅排除周六和周日，暂未接入各市场节假日日历；境内基金与 QDII 分别采用独立阈值。
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue';
import { computed, onMounted, ref, watch } from 'vue';

import {
  fetchFundNavFreshness,
  syncHeldFundProfiles,
  type FundNavFreshness,
  type FundNavFreshnessItem,
} from '@/plugins/fund/api';

const props = withDefaults(defineProps<{
  refreshKey?: number;
}>(), {
  refreshKey: 0,
});
const emit = defineEmits<{
  profilesSynced: [];
}>();

const thresholdOptions = [1, 2, 3, 5];
const qdiiThresholdOptions = [2, 3, 4, 5, 7];
const staleAfterBusinessDays = ref(2);
const qdiiStaleAfterBusinessDays = ref(4);
const freshness = ref<FundNavFreshness | null>(null);
const loading = ref(false);
const profileSyncing = ref(false);
const profileSyncMessage = ref('');
const errorMessage = ref('');

const statusLabels: Record<FundNavFreshnessItem['status'], string> = {
  fresh: '及时',
  stale: '滞后',
  missing: '缺失',
};

const hasLoaded = computed(() => freshness.value !== null);

function statusText(status: FundNavFreshnessItem['status']): string {
  return statusLabels[status];
}

function ageText(age: number | null, allowedBusinessDays: number): string {
  if (age === null) return `-- / ${allowedBusinessDays} 天`;
  const ageLabel = age === 0 ? '当天' : `${age} 天`;
  return `${ageLabel} / ${allowedBusinessDays} 天`;
}

async function loadFreshness(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    freshness.value = await fetchFundNavFreshness(
      staleAfterBusinessDays.value,
      qdiiStaleAfterBusinessDays.value,
    );
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '净值新鲜度加载失败';
  } finally {
    loading.value = false;
  }
}

async function syncProfiles(): Promise<void> {
  profileSyncing.value = true;
  profileSyncMessage.value = '';
  try {
    const result = await syncHeldFundProfiles();
    profileSyncMessage.value = `类型校准完成：更新 ${result.updated}，保持 ${result.unchanged}，失败 ${result.failed}`;
    await loadFreshness();
    emit('profilesSynced');
  } catch (error) {
    profileSyncMessage.value = error instanceof Error ? error.message : '基金类型校准失败';
  } finally {
    profileSyncing.value = false;
  }
}

watch(() => props.refreshKey, () => {
  if (hasLoaded.value) void loadFreshness();
});

onMounted(loadFreshness);
</script>

<style scoped>
.freshness-panel {
  margin-top: 16px;
}

.freshness-actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.freshness-actions .el-select {
  width: 126px;
}

.freshness-summary {
  border-block: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 14px;
  padding: 12px 0;
}

.freshness-summary div {
  display: grid;
  gap: 5px;
}

.freshness-summary span,
.freshness-row small,
.freshness-note,
.freshness-message {
  color: var(--color-muted);
  font-size: 12px;
}

.freshness-summary strong {
  font-size: 17px;
  font-variant-numeric: tabular-nums;
}

.profile-sync-message {
  color: #67e8f9;
  font-size: 12px;
  margin: 0 0 12px;
}

.freshness-table {
  overflow-x: auto;
}

.freshness-row {
  align-items: center;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  display: grid;
  font-size: 13px;
  gap: 12px;
  grid-template-columns: minmax(220px, 1.6fr) 110px 110px 90px 72px;
  min-width: 720px;
  padding: 11px 0;
}

.freshness-row > span:first-child {
  display: grid;
  gap: 3px;
}

.table-head {
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 650;
}

.freshness-status {
  font-size: 12px;
  font-weight: 700;
}

.status-fresh,
.is-fresh {
  color: #34d399;
}

.status-stale,
.is-stale {
  color: #fbbf24;
}

.status-missing,
.is-missing,
.freshness-message.is-error {
  color: #fb7185;
}

.freshness-note {
  line-height: 1.7;
  margin: 12px 0 0;
}

@media (max-width: 720px) {
  .freshness-actions {
    align-items: stretch;
    width: 100%;
  }

  .freshness-actions .el-select {
    flex: 1;
    width: auto;
  }

  .freshness-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    row-gap: 14px;
  }
}
</style>
