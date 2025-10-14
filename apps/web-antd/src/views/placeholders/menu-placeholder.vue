<script lang="ts" setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const title = computed(() =>
  String(route.meta?.title ?? route.name ?? '功能建设中'),
);
</script>

<template>
  <div class="menu-placeholder">
    <h1>{{ title }}</h1>
    <p>该页面正在规划中，敬请期待。</p>
  </div>
</template>

<style scoped>
.menu-placeholder {
  padding: 24px;
}

.menu-placeholder h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.menu-placeholder p {
  margin-top: 12px;
  font-size: 14px;
  color: rgb(0 0 0 / 45%);
}
</style>
