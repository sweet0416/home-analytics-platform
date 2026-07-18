<template>
  <div>
    <RevealContent as="section" class="page-header" :delay="20">
      <div>
        <h1 class="page-title">{{ title }}</h1>
        <div class="page-subtitle">{{ subtitle }}</div>
      </div>
    </RevealContent>
    <RevealContent as="section" class="panel" :delay="120">
      <div class="panel-body">
        <EmptyState title="模块预留" :description="description" />
      </div>
    </RevealContent>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

import EmptyState from '@/components/common/EmptyState.vue';
import RevealContent from '@/components/common/RevealContent.vue';

const route = useRoute();
const title = computed(() => String(route.meta.title ?? 'Module'));
const subtitle = computed(() => String(route.meta.subtitle ?? '插件模块将在后续阶段接入'));
const description = computed(() => `${title.value} 已在导航中预留，后续作为独立插件开发。`);
</script>
