<template>
  <div>
    <section class="page-header">
      <div>
        <h1 class="page-title">Settings</h1>
        <div class="page-subtitle">平台配置、插件配置、数据源与备份策略</div>
      </div>
    </section>
    <section class="panel">
      <div class="panel-body">
        <EmptyState title="设置页待接入" description="后续会由 Core 和插件共同提供配置 schema。" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue';
</script>

