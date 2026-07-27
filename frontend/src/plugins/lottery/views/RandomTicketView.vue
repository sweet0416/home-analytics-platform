<template>
  <div>
    <section class="page-header random-ticket-header">
      <div>
        <h1 class="page-title">随机票样本</h1>
        <div class="page-subtitle">录入外部随机五注，观察样本结构并生成可解释的二次候选</div>
      </div>
      <div class="random-ticket-actions">
        <el-select v-model="stageCode" class="stage-select" placeholder="全部阶段">
          <el-option label="全部阶段" value="" />
          <el-option
            v-for="stage in stageOptions"
            :key="stage.stage_code"
            :label="stage.stage_name"
            :value="stage.stage_code"
          />
        </el-select>
        <input
          ref="ticketImageInput"
          class="ticket-image-input"
          type="file"
          accept="image/*"
          @change="handleTicketImageSelected"
        />
        <el-button plain :loading="ocrLoading" @click="openTicketImagePicker">照片识别</el-button>
        <el-button plain @click="resetTickets">恢复默认</el-button>
        <el-button type="primary" :loading="loading" @click="runAnalysis">生成二次候选</el-button>
      </div>
    </section>

    <DltModuleNav />

    <DisclaimerAlert
      :text="analysis?.disclaimer ?? fallbackDisclaimer"
      class="random-ticket-alert"
    />

    <section v-if="ocrResult" class="panel random-ticket-panel">
      <div class="panel-header">
        <h2 class="panel-title">照片识别结果</h2>
        <span class="panel-meta">{{ ocrStatusText }}</span>
      </div>
      <div class="ocr-result">
        <p v-for="warning in ocrResult.warnings" :key="warning">{{ warning }}</p>
        <p v-if="ocrResult.combinations.length">
          已识别 {{ ocrResult.combinations.length }} 注，已填入下方号码球，请确认后再生成。
        </p>
        <details v-if="ocrResult.raw_text">
          <summary>查看 OCR 原文</summary>
          <pre>{{ ocrResult.raw_text }}</pre>
        </details>
      </div>
    </section>

    <section class="panel random-ticket-panel">
      <div class="panel-header">
        <h2 class="panel-title">老板随机五注</h2>
        <span class="panel-meta">选择一组后点击数字球，前区 5 个、后区 2 个</span>
      </div>
      <div class="ticket-workspace">
        <div class="ticket-list">
          <article
            v-for="(ticket, index) in tickets"
            :key="ticket.id"
            class="ticket-row"
            :class="{ active: activeIndex === index }"
            @click="activeIndex = index"
          >
            <strong>第 {{ index + 1 }} 注</strong>
            <div class="number-line">
              <span>前区</span>
              <LotteryBall
                v-for="number in ticket.frontNumbers"
                :key="`ticket-front-${ticket.id}-${number}`"
                area="front"
                :value="number"
              />
            </div>
            <div class="number-line">
              <span>后区</span>
              <LotteryBall
                v-for="number in ticket.backNumbers"
                :key="`ticket-back-${ticket.id}-${number}`"
                area="back"
                :value="number"
              />
            </div>
          </article>
        </div>

        <div class="picker-panel">
          <div class="picker-header">
            <strong>编辑第 {{ activeIndex + 1 }} 注</strong>
            <span>前区 {{ activeTicket.frontNumbers.length }}/5，后区 {{ activeTicket.backNumbers.length }}/2</span>
          </div>
          <div class="picker-block">
            <span class="picker-label">前区</span>
            <LotteryNumberBoard
              area="front"
              :numbers="frontNumbers"
              :columns="10"
              :tablet-columns="8"
              :mobile-columns="6"
              :classes-for-number="frontClasses"
              @toggle="toggleNumber('front', $event)"
            />
          </div>
          <div class="picker-block">
            <span class="picker-label">后区</span>
            <LotteryNumberBoard
              area="back"
              :numbers="backNumbers"
              :columns="6"
              :tablet-columns="6"
              :mobile-columns="6"
              :classes-for-number="backClasses"
              @toggle="toggleNumber('back', $event)"
            />
          </div>
        </div>
      </div>
    </section>

    <div class="grid metrics random-ticket-metrics">
      <MetricCard label="输入注数" :value="inputCount" meta="外部随机样本" />
      <MetricCard label="目标期号" :value="targetIssueNo" meta="生成后自动存档" />
      <MetricCard label="前区覆盖" :value="frontCoverage" meta="不同前区号码" />
      <MetricCard label="后区覆盖" :value="backCoverage" meta="不同后区号码" />
      <MetricCard label="分析阶段" :value="stageLabel" :meta="stageMeta" />
    </div>

    <section v-if="analysis" class="panel random-ticket-panel">
      <div class="panel-header">
        <h2 class="panel-title">样本体检</h2>
        <span class="panel-meta">先看随机票自身结构，再看二次候选</span>
      </div>
      <div class="summary-grid">
        <InfoBlock label="前区重复" :value="repeatSummary('front')" meta="随机票内部重复出现" />
        <InfoBlock label="后区重复" :value="repeatSummary('back')" meta="随机票内部重复出现" />
        <InfoBlock label="三区覆盖" :value="zoneSummary" meta="1-12 / 13-24 / 25-35" />
        <InfoBlock label="奇偶覆盖" :value="paritySummary" meta="前区 / 后区" />
      </div>
    </section>

    <section v-if="analysis?.recommendations.length" class="panel random-ticket-panel">
      <div class="panel-header">
        <h2 class="panel-title">二次候选</h2>
        <span class="panel-meta">基于随机票样本 + 历史统计 + 分散度</span>
      </div>
      <div class="recommendation-summary">
        <div
          v-for="item in analysis.recommendations"
          :key="`summary-${item.rank}`"
          class="summary-row"
        >
          <strong>第 {{ item.rank }} 组</strong>
          <span>{{ formatNumbers(item.front_numbers) }} + {{ formatNumbers(item.back_numbers) }}</span>
        </div>
      </div>
      <div class="recommendation-list">
        <article v-for="item in analysis.recommendations" :key="item.rank" class="recommendation-card">
          <div class="recommendation-head">
            <strong>第 {{ item.rank }} 组</strong>
            <span>评分 {{ item.score }}</span>
          </div>
          <div class="number-line">
            <span>前区</span>
            <LotteryBall
              v-for="number in item.front_numbers"
              :key="`result-front-${item.rank}-${number}`"
              area="front"
              :value="number"
            />
            <span class="back-label">后区</span>
            <LotteryBall
              v-for="number in item.back_numbers"
              :key="`result-back-${item.rank}-${number}`"
              area="back"
              :value="number"
            />
          </div>
          <ul>
            <li v-for="line in item.rationale" :key="line">{{ line }}</li>
          </ul>
        </article>
      </div>
    </section>

    <section v-if="archiveRuns.length" class="panel random-ticket-panel">
      <div class="panel-header">
        <h2 class="panel-title">样本存档</h2>
        <span class="panel-meta">开奖同步后会自动对比老板原始五注和二次候选五注</span>
      </div>
      <div class="archive-list">
        <article v-for="run in archiveRuns" :key="run.id" class="archive-card">
          <div class="archive-head">
            <strong>目标 {{ run.target_issue_no }}</strong>
            <span>{{ run.comparison.status_label }} · {{ formatDateTime(run.created_at) }}</span>
          </div>
          <p>{{ run.comparison.summary }}</p>
          <div v-if="run.comparison.target_draw" class="number-line">
            <span>开奖号</span>
            <LotteryBall
              v-for="number in run.comparison.target_draw.front_numbers"
              :key="`archive-draw-front-${run.id}-${number}`"
              area="front"
              :value="number"
            />
            <span class="back-label">后区</span>
            <LotteryBall
              v-for="number in run.comparison.target_draw.back_numbers"
              :key="`archive-draw-back-${run.id}-${number}`"
              area="back"
              :value="number"
            />
          </div>
          <div class="comparison-grid">
            <InfoBlock
              label="老板票最佳"
              :value="formatBestMatch(run.comparison.input_best)"
              meta="原始五注"
            />
            <InfoBlock
              label="二次候选最佳"
              :value="formatBestMatch(run.comparison.recommendation_best)"
              meta="系统生成五注"
            />
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, defineComponent, h, onMounted, ref } from 'vue';

import MetricCard from '@/components/metric/MetricCard.vue';
import DisclaimerAlert from '@/plugins/lottery/components/DisclaimerAlert.vue';
import DltModuleNav from '@/plugins/lottery/components/DltModuleNav.vue';
import LotteryBall from '@/plugins/lottery/components/LotteryBall.vue';
import LotteryNumberBoard from '@/plugins/lottery/components/LotteryNumberBoard.vue';
import type { LotteryRandomTicketComparisonItem } from '@/plugins/lottery/api';
import { useLotteryStore } from '@/plugins/lottery/store';

type Area = 'front' | 'back';

interface EditableTicket {
  id: string;
  frontNumbers: number[];
  backNumbers: number[];
}

const defaultTickets: EditableTicket[] = Array.from({ length: 5 }, (_, index) => ({
  id: `ticket-${index + 1}`,
  frontNumbers: [],
  backNumbers: [],
}));

const lottery = useLotteryStore();
const loading = ref(false);
const ocrLoading = ref(false);
const activeIndex = ref(0);
const stageCode = ref('');
const ticketImageInput = ref<HTMLInputElement | null>(null);
const tickets = ref<EditableTicket[]>(cloneDefaults());
const frontNumbers = Array.from({ length: 35 }, (_, index) => index + 1);
const backNumbers = Array.from({ length: 12 }, (_, index) => index + 1);
const fallbackDisclaimer = '本结果仅基于历史统计分析，仅供娱乐，不代表未来开奖结果。';

const analysis = computed(() => lottery.randomTicket);
const activeTicket = computed(() => tickets.value[activeIndex.value] ?? tickets.value[0]);
const stageOptions = computed(() => lottery.dataStageReport?.stages ?? []);
const archiveRuns = computed(() => lottery.randomTicketRuns);
const ocrResult = computed(() => lottery.randomTicketOcr);
const inputCount = computed(() => String(analysis.value?.input_set_count ?? tickets.value.length));
const targetIssueNo = computed(() => analysis.value?.target_issue_no ?? '--');
const frontCoverage = computed(() =>
  analysis.value ? String(analysis.value.sample_summary.front_unique_count) : '--',
);
const backCoverage = computed(() =>
  analysis.value ? String(analysis.value.sample_summary.back_unique_count) : '--',
);
const stageLabel = computed(() => analysis.value?.stage_name ?? '全部阶段');
const stageMeta = computed(() =>
  analysis.value?.stage_code ? '仅使用该规则阶段内样本' : '混合全部已入库阶段',
);
const zoneSummary = computed(() => {
  const value = analysis.value?.sample_summary.zone_coverage;
  return value ? `${value.zone_1_12}/${value.zone_13_24}/${value.zone_25_35}` : '--';
});
const paritySummary = computed(() => {
  const value = analysis.value?.sample_summary.parity_coverage;
  return value ? `${value.front_odd}:${value.front_even} / ${value.back_odd}:${value.back_even}` : '--';
});
const ocrStatusText = computed(() => {
  if (!ocrResult.value) return '';
  if (ocrResult.value.status === 'recognized') return '已识别，支持 6+14+17+23+33  1+6 这种格式';
  if (ocrResult.value.status === 'engine_missing') return 'OCR 引擎未启用';
  if (ocrResult.value.status === 'timeout') return '识别超时';
  return '需要人工校对';
});

const InfoBlock = defineComponent({
  name: 'InfoBlock',
  props: {
    label: { type: String, required: true },
    value: { type: String, required: true },
    meta: { type: String, required: true },
  },
  setup(props) {
    return () =>
      h('div', { class: 'info-block' }, [
        h('span', props.label),
        h('strong', props.value),
        h('small', props.meta),
      ]);
  },
});

onMounted(() => {
  void lottery.loadDataStageReport();
  void lottery.loadRandomTicketRuns();
});

function cloneDefaults(): EditableTicket[] {
  return defaultTickets.map((item) => ({
    id: `${item.id}-${Date.now()}`,
    frontNumbers: [...item.frontNumbers],
    backNumbers: [...item.backNumbers],
  }));
}

function frontClasses(number: number): string[] {
  return activeTicket.value.frontNumbers.includes(number) ? ['front-selected', 'selected'] : [];
}

function backClasses(number: number): string[] {
  return activeTicket.value.backNumbers.includes(number) ? ['back-selected', 'selected'] : [];
}

function toggleNumber(area: Area, number: number): void {
  const item = activeTicket.value;
  const key = area === 'front' ? 'frontNumbers' : 'backNumbers';
  const limit = area === 'front' ? 5 : 2;
  const current = item[key];
  if (current.includes(number)) {
    item[key] = current.filter((value) => value !== number);
    return;
  }
  if (current.length >= limit) {
    ElMessage.warning(`${area === 'front' ? '前区' : '后区'}最多选择 ${limit} 个号码`);
    return;
  }
  item[key] = [...current, number].sort((left, right) => left - right);
}

function resetTickets(): void {
  tickets.value = cloneDefaults();
  activeIndex.value = 0;
  lottery.randomTicket = null;
  lottery.randomTicketOcr = null;
}

function openTicketImagePicker(): void {
  ticketImageInput.value?.click();
}

async function handleTicketImageSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  ocrLoading.value = true;
  try {
    const result = await lottery.recognizeRandomTicketImage(file);
    if (result.combinations.length) {
      applyOcrCombinations(result.combinations);
      ElMessage.success(`识别到 ${result.combinations.length} 注，请确认号码后再生成`);
      return;
    }
    ElMessage.warning(result.warnings[0] ?? '没有识别出完整号码，请手动输入');
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '照片识别失败');
  } finally {
    ocrLoading.value = false;
  }
}

function applyOcrCombinations(
  combinations: Array<{ front_numbers: number[]; back_numbers: number[] }>,
): void {
  const nextTickets = cloneDefaults();
  combinations.slice(0, nextTickets.length).forEach((item, index) => {
    nextTickets[index].frontNumbers = [...item.front_numbers].sort((left, right) => left - right);
    nextTickets[index].backNumbers = [...item.back_numbers].sort((left, right) => left - right);
  });
  tickets.value = nextTickets;
  activeIndex.value = 0;
  lottery.randomTicket = null;
}

function repeatSummary(area: Area): string {
  const items = area === 'front'
    ? analysis.value?.sample_summary.front_repeat_numbers
    : analysis.value?.sample_summary.back_repeat_numbers;
  if (!items?.length) return '无明显重复';
  return items.map((item) => `${String(item.number).padStart(2, '0')}x${item.count}`).join('、');
}

function formatNumbers(numbers: number[]): string {
  return numbers.map((number) => String(number).padStart(2, '0')).join(' ');
}

async function runAnalysis(): Promise<void> {
  const invalidIndex = tickets.value.findIndex(
    (item) => item.frontNumbers.length !== 5 || item.backNumbers.length !== 2,
  );
  if (invalidIndex >= 0) {
    activeIndex.value = invalidIndex;
    ElMessage.warning(`第 ${invalidIndex + 1} 注需要选择 5 个前区和 2 个后区`);
    return;
  }
  loading.value = true;
  try {
    await lottery.analyzeRandomTicket({
      combinations: tickets.value.map((item) => ({
        front_numbers: item.frontNumbers,
        back_numbers: item.backNumbers,
      })),
      sets: 5,
      sample_limit: 200,
      sample_weight: 18,
      stage_code: stageCode.value || null,
      save: true,
    });
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '随机票样本分析失败');
  } finally {
    loading.value = false;
  }
}

function formatBestMatch(item: LotteryRandomTicketComparisonItem | null): string {
  if (!item) return '等待开奖';
  const tier = item.prize_tier ? ` · ${item.prize_tier}等奖` : '';
  return `${item.match_key}${tier}`;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
</script>

<style scoped>
.random-ticket-header,
.random-ticket-actions {
  align-items: center;
}

.random-ticket-actions {
  display: flex;
  flex-shrink: 0;
  gap: 10px;
}

.stage-select {
  min-width: 220px;
}

.ticket-image-input {
  display: none;
}

.random-ticket-alert,
.random-ticket-panel,
.random-ticket-metrics {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.ocr-result {
  display: grid;
  gap: 8px;
}

.ocr-result p {
  color: var(--color-muted);
  font-size: 13px;
  margin: 0;
}

.ocr-result summary {
  color: var(--color-primary);
  cursor: pointer;
  font-size: 13px;
}

.ocr-result pre {
  background: rgba(2, 6, 23, 0.45);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  color: var(--color-text);
  margin: 8px 0 0;
  max-height: 180px;
  overflow: auto;
  padding: 10px;
  white-space: pre-wrap;
}

.ticket-workspace {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.1fr);
}

.ticket-list,
.recommendation-list,
.archive-list {
  display: grid;
  gap: 10px;
}

.recommendation-summary {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}

.summary-row {
  align-items: center;
  border: 1px solid rgba(56, 189, 248, 0.16);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.48);
  color: var(--color-text);
  display: flex;
  gap: 14px;
  justify-content: space-between;
  padding: 9px 11px;
}

.summary-row span {
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 13px;
}

.ticket-row,
.recommendation-card,
.archive-card {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 8px;
  padding: 12px;
}

.ticket-row {
  cursor: pointer;
}

.ticket-row.active {
  background: rgba(34, 211, 238, 0.08);
  border-color: rgba(34, 211, 238, 0.42);
}

.number-line,
.recommendation-head,
.picker-header,
.archive-head {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.recommendation-head,
.picker-header,
.archive-head {
  justify-content: space-between;
}

.number-line span,
.picker-header span,
.recommendation-head span,
.archive-head span,
.archive-card p,
.recommendation-card li,
.info-block span,
.info-block small {
  color: var(--color-muted);
  font-size: 12px;
}

.picker-panel {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 14px;
  padding: 14px;
}

.picker-block {
  display: grid;
  gap: 8px;
}

.picker-label {
  color: var(--color-muted);
  font-size: 12px;
}

.summary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.comparison-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.info-block {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 12px;
}

.info-block strong {
  color: var(--color-text);
  font-size: 18px;
}

.back-label {
  margin-left: 8px;
}

.recommendation-card ul {
  display: grid;
  gap: 6px;
  margin: 4px 0 0;
  padding-left: 18px;
}

@media (max-width: 980px) {
  .ticket-workspace,
  .summary-grid,
  .comparison-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .random-ticket-header,
  .random-ticket-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
