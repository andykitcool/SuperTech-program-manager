<template>
  <div>
    <div class="page-header">
      <h2>同步记录</h2>
      <a-button @click="loadHistory" :loading="historyLoading">
        刷新
      </a-button>
    </div>

    <a-card>
      <a-table
        :data-source="historyItems"
        :columns="historyColumns"
        :loading="historyLoading"
        :pagination="{
          current: historyPage,
          pageSize: historyPageSize,
          total: historyTotal,
          size: 'small',
          showSizeChanger: false,
          showTotal: (total: number) => `共 ${total} 条`,
        }"
        size="small"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.key === 'index'">
            <span class="muted-text">{{ historyPageSize * (historyPage - 1) + index + 1 }}</span>
          </template>

          <template v-if="column.key === 'status'">
            <a-tag :color="historyStatusColor(record.status)">
              {{ historyStatusText(record.status) }}
            </a-tag>
          </template>

          <template v-if="column.key === 'activity'">
            <span>{{ record.activity_name || '-' }}</span>
          </template>

          <template v-if="column.key === 'found'">
            <a-tooltip title="已发现 / 已上传到云端 / 失败 / 跳过">
              <span>
                <span class="found-count">{{ record.total_found }}</span>
                <span class="count-separator"> / </span>
                <span class="uploaded-count">{{ record.total_uploaded }}</span>
                <span class="count-separator"> / </span>
                <span :class="record.total_failed > 0 ? 'failed-count' : 'muted-text'">{{ record.total_failed }}</span>
                <span class="count-separator"> / </span>
                <span class="skipped-count">{{ record.total_skipped }}</span>
              </span>
            </a-tooltip>
          </template>

          <template v-if="column.key === 'total_bytes'">
            <span>{{ record.total_bytes ? formatSize(record.total_bytes) : '-' }}</span>
          </template>

          <template v-if="column.key === 'duration'">
            <span>{{ record.duration || '-' }}</span>
          </template>

          <template v-if="column.key === 'config'">
            <a-tooltip placement="topLeft">
              <template #title>
                <div>并发数: {{ record.config?.concurrency ?? '-' }}</div>
                <div>滚动延迟: {{ record.config?.scroll_delay ?? '-' }}秒</div>
                <div>选项卡: {{ record.config?.tab_mode === 'all' ? '全部' : '仅当前' }}</div>
                <div>分子目录: {{ record.config?.tab_subdir ? '是' : '否' }}</div>
              </template>
              <span class="config-summary">{{ record.config?.concurrency ?? '-' }}并发</span>
            </a-tooltip>
          </template>

          <template v-if="column.key === 'started_at'">
            <span>{{ formatHistoryTime(record.started_at) }}</span>
          </template>

          <template v-if="column.key === 'error_msg'">
            <a-tooltip v-if="record.error_msg" :title="record.error_msg">
              <span class="error-message">
                {{ record.error_msg.length > 30 ? record.error_msg.slice(0, 30) + '...' : record.error_msg }}
              </span>
            </a-tooltip>
            <span v-else class="muted-text">-</span>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { wotuApi, type SyncHistoryItem } from '@/api/admin'

const historyItems = ref<SyncHistoryItem[]>([])
const historyLoading = ref(false)
const historyPage = ref(1)
const historyPageSize = ref(20)
const historyTotal = ref(0)

const historyColumns = [
  { title: '#', key: 'index', width: 56, align: 'center' as const },
  { title: '状态', key: 'status', width: 90, align: 'center' as const },
  { title: '活动', key: 'activity', width: 160 },
  { title: '发现/上传/失败/跳过', key: 'found', width: 190, align: 'center' as const },
  { title: '数据量', key: 'total_bytes', width: 100, align: 'right' as const },
  { title: '耗时', key: 'duration', width: 90, align: 'center' as const },
  { title: '配置', key: 'config', width: 90, align: 'center' as const },
  { title: '开始时间', key: 'started_at', width: 170 },
  { title: '错误信息', key: 'error_msg', ellipsis: true },
]

function historyStatusColor(status: string) {
  const map: Record<string, string> = {
    running: 'processing',
    completed: 'success',
    failed: 'error',
    stopped: 'warning',
  }
  return map[status] || 'default'
}

function historyStatusText(status: string) {
  const map: Record<string, string> = {
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止',
  }
  return map[status] || status
}

function formatHistoryTime(t: string) {
  return dayjs(t).format('YYYY-MM-DD HH:mm:ss')
}

function formatSize(bytes: number) {
  if (!bytes || bytes <= 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 3)
  return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + ' ' + units[i]
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await wotuApi.getSyncHistory(historyPage.value, historyPageSize.value)
    historyItems.value = res.data.items || []
    historyTotal.value = res.data.total || 0
  } finally {
    historyLoading.value = false
  }
}

function handleTableChange(pagination: any) {
  historyPage.value = pagination.current || 1
  loadHistory()
}

onMounted(loadHistory)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.muted-text {
  color: #94a3b8;
}

.found-count {
  color: #6366f1;
}

.uploaded-count {
  color: #22c55e;
}

.failed-count,
.error-message {
  color: #ef4444;
}

.skipped-count {
  color: #f59e0b;
}

.count-separator {
  color: #94a3b8;
}

.config-summary {
  color: #64748b;
  cursor: help;
}
</style>
