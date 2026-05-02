<template>
  <div class="not-found">
    <div class="not-found-content">
      <div class="icon-wrapper">
        <SearchOutlined />
      </div>
      <h1>页面不存在</h1>
      <p>请通过公众号对话获取节目链接</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { SearchOutlined } from '@ant-design/icons-vue'
</script>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f5f5f5;
}

.not-found-content {
  text-align: center;
  padding: 40px;
}

.icon-wrapper {
  font-size: 64px;
  color: #bfbfbf;
  margin-bottom: 24px;
}

.not-found-content h1 {
  font-size: 20px;
  color: #262626;
  margin-bottom: 8px;
}

.not-found-content p {
  font-size: 14px;
  color: #8c8c8c;
}
</style>
