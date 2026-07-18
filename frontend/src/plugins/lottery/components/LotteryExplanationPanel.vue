<template>
  <section class="panel explanation-panel">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">{{ title }}</h2>
        <span v-if="subtitle" class="panel-meta">{{ subtitle }}</span>
      </div>
    </div>
    <div class="explanation-grid">
      <article
        v-for="section in sections"
        :key="section.title"
        class="explanation-card"
      >
        <div class="explanation-card-title">{{ section.title }}</div>
        <ul>
          <li v-for="item in section.items" :key="item">{{ item }}</li>
        </ul>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
export interface LotteryExplanationSection {
  title: string;
  items: string[];
}

defineProps<{
  title: string;
  subtitle?: string;
  sections: LotteryExplanationSection[];
}>();
</script>

<style scoped>
.explanation-panel {
  margin-top: 16px;
}

.panel-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.explanation-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 14px;
}

.explanation-card {
  background: rgba(15, 23, 42, 0.36);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 14px;
}

.explanation-card-title {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 720;
}

.explanation-card ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
}

.explanation-card li {
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.65;
}

@media (max-width: 1080px) {
  .explanation-grid {
    grid-template-columns: 1fr;
  }
}
</style>
