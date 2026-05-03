<template>
  <div class="photo-sync-workspace">
    <a-card title="同步配置" class="sync-card">
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :xs="24" :lg="12">
            <a-form-item label="当前活动">
              <a-input :value="activity.name" disabled />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :lg="12">
            <a-form-item label="相册URL">
              <a-input v-model:value="form.url" placeholder="https://m.alltuu.com/album/..." />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :xs="24" :md="6">
            <a-form-item label="并发数">
              <a-input-number v-model:value="form.concurrency" :min="1" :max="20" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="6">
            <a-form-item label="滚动延迟(秒)">
              <a-input-number v-model:value="form.scroll_delay" :min="0" :max="60" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="6">
            <a-form-item label="选项卡模式">
              <a-select v-model:value="form.tab_mode">
                <a-select-option value="current">仅当前选项卡</a-select-option>
                <a-select-option value="all">下载所有选项卡</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="6">
            <a-form-item label="分子目录">
              <a-checkbox v-model:checked="form.tab_subdir" :disabled="form.tab_mode !== 'all'" />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>

      <a-space>
        <a-button type="primary" :loading="starting" :disabled="running" @click="startSync">
          <template #icon><PlayCircleOutlined /></template>
          开始同步
        </a-button>
        <a-button danger :disabled="!running" @click="stopSync">
          <template #icon><StopOutlined /></template>
          停止
        </a-button>
        <a-button @click="refreshStatus">刷新状态</a-button>
      </a-space>
    </a-card>

    <a-row :gutter="16" class="sync-stats">
      <a-col :xs="12" :lg="6">
        <a-card size="small">
          <a-statistic title="已发现图片" :value="stats.total_found" value-style="color: #6366f1" />
        </a-card>
      </a-col>
      <a-col :xs="12" :lg="6">
        <a-card size="small">
          <a-statistic title="已下载" :value="stats.total_downloaded" value-style="color: #22c55e" />
        </a-card>
      </a-col>
      <a-col :xs="12" :lg="6">
        <a-card size="small">
          <a-statistic title="已上传到云端" :value="stats.total_uploaded" value-style="color: #06b6d4" />
        </a-card>
      </a-col>
      <a-col :xs="12" :lg="6">
        <a-card size="small">
          <a-statistic title="下载失败" :value="stats.total_failed" value-style="color: #ef4444" />
        </a-card>
      </a-col>
    </a-row>

    <a-card size="small" class="sync-card">
      <div class="progress-header">
        <span>
          <a-tag :color="phaseColor">{{ phaseText }}</a-tag>
          <span v-if="stats.current_tab" class="muted-text">当前选项卡: {{ stats.current_tab }}</span>
        </span>
        <span>{{ stats.total_downloaded + stats.total_failed }} / {{ stats.total_found || 0 }}</span>
      </div>
      <a-progress :percent="progressPercent" :status="progressStatus" />
      <div v-if="stats.total_skipped > 0" class="muted-text">跳过 {{ stats.total_skipped }} 张（已存在）</div>
    </a-card>

    <a-card size="small" title="照片列表" class="sync-card">
      <template #extra>
        <span class="muted-text">共 {{ photos.length }} 张</span>
      </template>
      <div v-if="photos.length > 0" class="photo-grid">
        <div v-for="photo in photos" :key="photo.id || photo.index" class="photo-card">
          <div class="photo-card-thumb">
            <a-image
              :src="photo.thumb_url || photo.url"
              :fallback="fallbackImage"
              :preview="!!(photo.thumb_url || photo.url)"
              style="width: 100%; height: 100%; object-fit: cover;"
            />
            <div class="photo-card-index">{{ photo.index }}</div>
            <div class="photo-card-status" :class="'photo-status-' + photo.status">
              {{ statusText(photo.status) }}
            </div>
          </div>
          <div class="photo-card-info">
            <div class="photo-card-name" :title="photo.filename">{{ photo.filename }}</div>
            <div class="photo-card-meta">
              <span v-if="photo.size">{{ formatSize(photo.size) }}</span>
              <span v-if="photo.shoot_time">{{ photo.shoot_time }}</span>
            </div>
          </div>
        </div>
      </div>
      <a-empty v-else description="暂无照片数据，请开始同步" />
    </a-card>

    <a-card size="small" :title="'实时日志 (' + logs.length + ')'">
      <template #extra>
        <a-button size="small" @click="logs = []">清空</a-button>
      </template>
      <div ref="logContainerRef" class="log-panel">
        <div
          v-for="(log, i) in logs"
          :key="i"
          :style="{ color: log.level === 'error' ? '#ef4444' : log.level === 'warning' ? '#f59e0b' : '#64748b' }"
        >
          [{{ log.time }}] {{ log.message }}
        </div>
        <a-empty v-if="logs.length === 0" description="暂无日志" />
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { wotuApi, type Activity } from '@/api/admin'

const props = defineProps<{
  activityId: number
  activity: Activity
}>()

const starting = ref(false)
const running = ref(false)
const photos = ref<any[]>([])
const logs = ref<any[]>([])
const logContainerRef = ref<HTMLElement>()

const stats = reactive({
  phase: 'idle',
  total_found: 0,
  total_downloaded: 0,
  total_uploaded: 0,
  total_failed: 0,
  total_skipped: 0,
  total_bytes: 0,
  speed: 0,
  current_tab: '',
  error_msg: '',
})

const form = reactive({
  url: props.activity.wotu_album_url || '',
  concurrency: 5,
  scroll_delay: 5,
  tab_mode: 'current',
  tab_subdir: true,
})

let pollTimer: ReturnType<typeof setInterval> | null = null

const fallbackImage = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect fill="%23f5f5f5" width="40" height="40"/><text x="20" y="24" text-anchor="middle" fill="%23999" font-size="12">?</text></svg>'

const phaseText = computed(() => {
  const map: Record<string, string> = {
    idle: '就绪',
    scraping: '正在抓取',
    downloading: '正在下载',
    uploading: '正在上传',
    completed: '已完成',
    error: '出错',
  }
  return map[stats.phase] || '就绪'
})

const phaseColor = computed(() => {
  const map: Record<string, string> = {
    idle: 'default',
    scraping: 'processing',
    downloading: 'processing',
    uploading: 'processing',
    completed: 'success',
    error: 'error',
  }
  return map[stats.phase] || 'default'
})

const progressPercent = computed(() => {
  if (!stats.total_found) return 0
  return Math.round(((stats.total_downloaded + stats.total_failed) / stats.total_found) * 100)
})

const progressStatus = computed(() => {
  if (stats.phase === 'error') return 'exception' as const
  if (stats.phase === 'completed') return 'success' as const
  return 'normal' as const
})

function statusText(status: string) {
  const map: Record<string, string> = {
    pending: '等待中',
    downloading: '下载中',
    uploading: '上传中',
    success: '成功',
    failed: '失败',
    skipped: '已跳过',
  }
  return map[status] || status
}

function formatSize(bytes: number) {
  if (!bytes || bytes <= 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 3)
  return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + ' ' + units[i]
}

async function startSync() {
  if (!form.url) {
    message.warning('请输入相册URL')
    return
  }

  starting.value = true
  try {
    await wotuApi.startSync({
      activity_id: props.activityId,
      url: form.url,
      concurrency: form.concurrency,
      scroll_delay: form.scroll_delay,
      tab_mode: form.tab_mode,
      tab_subdir: form.tab_subdir,
    })
    message.success('同步任务已启动')
    photos.value = []
    logs.value = []
    startPolling()
  } finally {
    starting.value = false
  }
}

async function stopSync() {
  await wotuApi.stopSync()
  message.info('已发送停止请求')
}

async function refreshStatus() {
  await pollStatus()
}

async function pollStatus() {
  try {
    const res = await wotuApi.getStatus()
    const data = res.data
    running.value = data.running
    Object.assign(stats, data.stats)

    const [photosRes, logsRes] = await Promise.all([
      wotuApi.getPhotos(),
      wotuApi.getLogs(),
    ])
    photos.value = photosRes.data || []
    logs.value = logsRes.data || []

    await nextTick()
    if (logContainerRef.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
    }

    if (!data.running && (data.stats.phase === 'completed' || data.stats.phase === 'error')) {
      stopPolling()
    }
  } catch {
    // Status polling is best-effort; the next manual refresh can recover.
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(pollStatus, 2000)
  pollStatus()
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(
  () => props.activity.wotu_album_url,
  (url) => {
    if (url && !form.url) {
      form.url = url
    }
  },
)

onMounted(refreshStatus)
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.photo-sync-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sync-card {
  margin-bottom: 0;
}

.sync-stats {
  row-gap: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.muted-text {
  color: #94a3b8;
  font-size: 12px;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  max-height: 420px;
  overflow-y: auto;
}

.photo-card {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  transition: box-shadow 0.2s, transform 0.2s;
}

.photo-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.photo-card-thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: #f5f5f5;
}

.photo-card-index {
  position: absolute;
  top: 4px;
  left: 4px;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
}

.photo-card-status {
  position: absolute;
  right: 4px;
  bottom: 4px;
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
}

.photo-status-pending { background: rgba(0, 0, 0, 0.45); }
.photo-status-downloading { background: rgba(99, 102, 241, 0.85); }
.photo-status-uploading { background: rgba(6, 182, 212, 0.85); }
.photo-status-success { background: rgba(34, 197, 94, 0.85); }
.photo-status-failed { background: rgba(239, 68, 68, 0.85); }
.photo-status-skipped { background: rgba(245, 158, 11, 0.85); }

.photo-card-info {
  padding: 6px 8px;
}

.photo-card-name {
  color: #333;
  font-size: 12px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.photo-card-meta {
  display: flex;
  justify-content: space-between;
  color: #94a3b8;
  font-size: 11px;
  margin-top: 2px;
}

.log-panel {
  max-height: 250px;
  overflow-y: auto;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.8;
}
</style>
