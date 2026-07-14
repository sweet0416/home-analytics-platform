<template>
  <div class="empty-state">
    <div class="empty-title">{{ title }}</div>
    <div class="empty-description">{{ description }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description: string;
}>();
</script>

<style scoped>
.empty-state {
  border: 1px dashed rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  color: var(--color-muted);
  padding: 22px;
  text-align: center;
}

.empty-title {
  color: var(--color-text);
  font-weight: 650;
}

.empty-description {
  margin-top: 6px;
  font-size: 13px;
}
</style>

