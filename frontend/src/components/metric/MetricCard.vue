<template>
  <RevealContent as="section" class="metric-card panel" :delay="delay">
    <div class="metric-label">{{ label }}</div>
    <div class="metric-value">{{ value }}</div>
    <div class="metric-meta">{{ meta }}</div>
  </RevealContent>
</template>

<script setup lang="ts">
import RevealContent from '@/components/common/RevealContent.vue';

withDefaults(defineProps<{
  label: string;
  value: string;
  meta: string;
  delay?: number;
}>(), {
  delay: 0,
});
</script>

<style scoped>
.metric-card {
  padding: 16px;
}

.metric-label {
  color: var(--color-muted);
  font-size: 12px;
}

.metric-value {
  margin-top: 10px;
  font-variant-numeric: tabular-nums;
  font-size: 28px;
  font-weight: 760;
}

.metric-meta {
  margin-top: 8px;
  color: var(--color-muted);
  font-size: 12px;
}
</style>
