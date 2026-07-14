<template>
  <div class="disclaimer">{{ text }}</div>
</template>

<script setup lang="ts">
defineProps<{
  text: string;
}>();
</script>

<style scoped>
.disclaimer {
  border: 1px solid rgba(245, 158, 11, 0.28);
  border-radius: 8px;
  background: rgba(245, 158, 11, 0.08);
  color: #fcd34d;
  padding: 12px 14px;
  font-size: 13px;
}
</style>

