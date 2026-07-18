<template>
  <component
    :is="as"
    ref="root"
    class="reveal-content"
    :class="{ 'is-visible': isVisible, 'is-disabled': disabled }"
    :style="revealStyle"
    v-bind="$attrs"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    as?: string;
    delay?: number;
    distance?: number;
    duration?: number;
    disabled?: boolean;
    once?: boolean;
  }>(),
  {
    as: 'div',
    delay: 0,
    distance: 14,
    duration: 520,
    disabled: false,
    once: true,
  },
);

const root = ref<HTMLElement | null>(null);
const isVisible = ref(props.disabled);
let observer: IntersectionObserver | null = null;

const revealStyle = computed(() => ({
  '--reveal-delay': `${props.delay}ms`,
  '--reveal-distance': `${props.distance}px`,
  '--reveal-duration': `${props.duration}ms`,
}));

onMounted(() => {
  if (props.disabled || typeof window === 'undefined' || !('IntersectionObserver' in window)) {
    isVisible.value = true;
    return;
  }

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) {
    isVisible.value = true;
    return;
  }

  observer = new IntersectionObserver(
    ([entry]) => {
      if (!entry) return;
      isVisible.value = entry.isIntersecting;
      if (entry.isIntersecting && props.once) {
        observer?.disconnect();
      }
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.12 },
  );

  if (root.value) {
    observer.observe(root.value);
  }
});

onBeforeUnmount(() => {
  observer?.disconnect();
});
</script>

<style scoped>
.reveal-content {
  opacity: 0;
  transform: translate3d(0, var(--reveal-distance), 0) scale(0.985);
  transition:
    opacity var(--reveal-duration) ease,
    transform var(--reveal-duration) cubic-bezier(0.22, 1, 0.36, 1);
  transition-delay: var(--reveal-delay);
  will-change: opacity, transform;
}

.reveal-content.is-visible,
.reveal-content.is-disabled {
  opacity: 1;
  transform: translate3d(0, 0, 0) scale(1);
}

@media (prefers-reduced-motion: reduce) {
  .reveal-content {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
