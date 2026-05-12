<template>
  <div class="cloud-print-settings-page">
    <div class="page-header">
      <div>
        <h2>云印设置</h2>
        <p>维护云打印设备、默认参数和打印机状态。</p>
      </div>
    </div>

    <CloudPrintConfigPanel />
  </div>
</template>

<script setup lang="ts">
import CloudPrintConfigPanel from '@/components/CloudPrintConfigPanel.vue'
</script>

<style scoped>
.cloud-print-settings-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 18px;
}

.page-header h2 {
  margin: 0;
  color: #111827;
  font-size: 20px;
}

.page-header p {
  margin: 6px 0 0;
  color: #8c8c8c;
}
</style>
