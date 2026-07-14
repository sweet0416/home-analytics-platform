<template>
  <div class="app-shell">
    <Sidebar />
    <div class="app-main">
      <TopBar />
      <main class="content-shell">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './Sidebar.vue';
import TopBar from './TopBar.vue';
</script>

