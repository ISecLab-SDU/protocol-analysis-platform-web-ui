<template>
  <div class="menu-placeholder">
    <div class="placeholder-content">
      <a-icon type="setting" class="placeholder-icon" />
      <h3>{{ $route.meta.title || '功能开发中' }}</h3>
      <p>该功能正在开发中，敬请期待...</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
// 占位符组件，用于尚未实现的功能模块
</script>

<style scoped>
.menu-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  background-color: #f5f5f5;
  border-radius: 8px;
}

.placeholder-content {
  padding: 40px;
  text-align: center;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgb(0 0 0 / 10%);
}

.placeholder-icon {
  margin-bottom: 16px;
  font-size: 48px;
  color: #1890ff;
}

h3 {
  margin-bottom: 8px;
  font-size: 20px;
  color: #333;
}

p {
  font-size: 14px;
  color: #666;
}
</style>