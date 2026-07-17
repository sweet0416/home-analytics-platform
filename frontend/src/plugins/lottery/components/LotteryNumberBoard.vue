<template>
  <div class="number-grid" :class="area" :style="gridStyle">
    <button
      v-for="number in numbers"
      :key="`${area}-${number}`"
      type="button"
      class="number-button"
      :class="[area, ...classesForNumber(number)]"
      @click="$emit('toggle', number)"
    >
      {{ formatNumber(number) }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CSSProperties, PropType } from 'vue';

type Area = 'front' | 'back';

const props = defineProps({
  area: {
    type: String as PropType<Area>,
    required: true,
  },
  numbers: {
    type: Array as PropType<number[]>,
    required: true,
  },
  columns: {
    type: Number,
    default: 12,
  },
  tabletColumns: {
    type: Number,
    default: 8,
  },
  mobileColumns: {
    type: Number,
    default: 6,
  },
  classesForNumber: {
    type: Function as PropType<(number: number) => string[]>,
    default: () => [],
  },
});

defineEmits<{
  toggle: [number: number];
}>();

const gridStyle = computed<CSSProperties>(() => ({
  '--lottery-number-columns': String(props.columns),
  '--lottery-number-tablet-columns': String(props.tabletColumns),
  '--lottery-number-mobile-columns': String(props.mobileColumns),
}));

function formatNumber(value: number): string {
  return String(value).padStart(2, '0');
}
</script>

<style scoped>
.number-grid {
  display: grid;
  gap: 7px;
  grid-template-columns: repeat(var(--lottery-number-columns), 34px);
  justify-content: start;
}

.number-button {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 999px;
  color: var(--color-text);
  cursor: pointer;
  font-size: 12px;
  font-weight: 760;
  height: 34px;
  line-height: 1;
  min-width: 0;
  padding: 0;
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    transform 0.18s ease;
  width: 34px;
}

.number-button:hover {
  border-color: rgba(56, 189, 248, 0.48);
}

.number-button.selected {
  transform: translateY(-1px);
}

.number-button.front-selected,
.number-button.dan {
  background: rgba(56, 189, 248, 0.18);
  border-color: rgba(56, 189, 248, 0.7);
  color: #7dd3fc;
}

.number-button.back-selected,
.number-button.tuo {
  background: rgba(34, 197, 94, 0.16);
  border-color: rgba(34, 197, 94, 0.58);
  color: #86efac;
}

.number-button.kill {
  background: rgba(248, 113, 113, 0.16);
  border-color: rgba(248, 113, 113, 0.58);
  color: #fca5a5;
  text-decoration: line-through;
}

.number-button.active {
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.1);
}

@media (max-width: 1080px) {
  .number-grid {
    gap: 6px;
    grid-template-columns: repeat(var(--lottery-number-tablet-columns), 32px);
  }

  .number-button {
    height: 32px;
    width: 32px;
  }
}

@media (max-width: 520px) {
  .number-grid {
    grid-template-columns: repeat(var(--lottery-number-mobile-columns), 30px);
  }

  .number-button {
    font-size: 11px;
    height: 30px;
    width: 30px;
  }
}
</style>
