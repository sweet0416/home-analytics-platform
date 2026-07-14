<template>
  <span class="lottery-ball" :class="area">{{ formatted }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  value: number;
  area: 'front' | 'back';
}>();

const formatted = computed(() => String(props.value).padStart(2, '0'));
</script>

<style scoped>
.lottery-ball {
  display: inline-grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 750;
}

.lottery-ball.front {
  border: 1px solid rgba(56, 189, 248, 0.58);
  background: rgba(56, 189, 248, 0.14);
  color: #7dd3fc;
}

.lottery-ball.back {
  border: 1px solid rgba(245, 158, 11, 0.62);
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}
</style>

