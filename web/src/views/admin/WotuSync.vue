<template>
  <div>
    <div class="page-header">
      <a-button @click="$router.back()">
        <template #icon><ArrowLeftOutlined /></template>
        返回
      </a-button>
      <h2>喔图照片同步</h2>
      <div></div>
    </div>

    <!-- 控制面板 -->
    <a-card class="mb-4" title="同步配置">
      <a-row :gutter="16">
        <a-col :span="24">
          <a-form layout="inline" style="width: 100%">
            <a-form-item label="选择活动">
              <a-select
                v-model:value="form.activity_id"
                placeholder="选择有喔图相册的活动"
                style="width: 240px"
                show-search
                :filter-option="filterOption"
                @change="onActivityChange"
              >
                <a-select-option v-for="a in activities" :key="a.id" :value="a.id">
                  {{ a.name }} {{ a.event_date ? `(${a.event_date})` : '' }}
                </a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="相册URL">
              <a-input v-model:value="form.url" placeholder="https://m.alltuu.com/album/..." style="width: 360px" />
            </a-form-item>
          </a-form>
        </a-col>
      </a-row>

      <a-divider style="margin: 12px 0" />

      <a-row :gutter="16">
        <a-col :span="6">
          <a-form-item label="并发数">
            <a-input-number v-model:value="form.concurrency" :min="1" :max="20" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="6">
          <a-form-item label="滚动延迟(秒)">
            <a-input-number v-model:value="form.scroll_delay" :min="0" :max="60" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="6">
          <a-form-item label="选项卡模式">
            <a-select v-model:value="form.tab_mode" style="width: 100%">
              <a-select-option value="current">仅当前选项卡</a-select-option>
              <a-select-option value="all">下载所有选项卡</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="6">
          <a-form-item label="分子目录">
            <a-checkbox v-model:checked="form.tab_subdir" :disabled="form.tab_mode !== 'all'" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-space>
        <a-button type="primary" :loading="starting" :disabled="running" @click="startSync">
          <template #icon><PlayCircleOutlined /></template>
          开始同步
        </a-button>
        <a-button danger :disabled="!running" @click="stopSync">
          <template #icon><StopOutlined /></template>
          停止
        </a-button>
      </a-space>
    </a-card>

    <!-- 实时进度 -->
    <a-row :gutter="16" class="mb-4">
      <a-col :span="6">
        <a-card size="small">
          <a-statistic title="已发现图片" :value="stats.total_found" value-style="color: #6366f1" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small">
          <a-statistic title="已下载" :value="stats.total_downloaded" value-style="color: #22c55e" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small">
          <a-statistic title="已上传到云端" :value="stats.total_uploaded" value-style="color: #06b6d4" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small">
          <a-statistic title="下载失败" :value="stats.total_failed" value-style="color: #ef4444" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 进度条 -->
    <a-card size="small" class="mb-4">
      <div class="flex items-center justify-between mb-2">
        <span style="font-weight: 600">
          <a-tag :color="phaseColor">{{ phaseText }}</a-tag>
          <span v-if="stats.current_tab" style="color: #94a3b8; font-size: 12px;">
            当前选项卡: {{ stats.current_tab }}
          </span>
        </span>
        <span>{{ stats.total_downloaded + stats.total_failed }} / {{ stats.total_found || 0 }}</span>
      </div>
      <a-progress
        :percent="progressPercent"
        :status="progressStatus"
        :stroke-color="{ from: '#6366f1', to: '#8b5cf6' }"
      />
      <div v-if="stats.total_skipped > 0" style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
        跳过 {{ stats.total_skipped }} 张（已存在）
      </div>
    </a-card>

    <!-- 照片列表 -->
    <a-card size="small" class="mb-4" title="照片列表">
      <template #extra>
        <span style="font-size: 12px; color: #94a3b8">共 {{ photos.length }} 张</span>
      </template>
      <div v-if="photos.length > 0" class="photo-grid">
        <div v-for="photo in photos" :key="photo.id" class="photo-card">
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
            <div v-if="photo.download_duration" class="photo-card-duration">
              {{ formatDuration(photo.download_duration) }}
            </div>
          </div>
        </div>
      </div>
      <div v-else style="text-align: center; padding: 40px; color: #94a3b8">
        <CameraOutlined style="font-size: 40px; opacity: 0.3; margin-bottom: 8px" />
        <p>暂无照片数据，请选择活动并开始同步</p>
      </div>
    </a-card>

    <!-- 实时日志 -->
    <a-card
      size="small"
      :title="'实时日志 (' + logs.length + ')'"
    >
      <template #extra>
        <a-button size="small" @click="logs = []">清空</a-button>
      </template>
      <div
        ref="logContainerRef"
        style="max-height: 250px; overflow-y: auto; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.8"
      >
        <div
          v-for="(log, i) in logs"
          :key="i"
          :style="{ color: log.level === 'error' ? '#ef4444' : log.level === 'warning' ? '#f59e0b' : '#94a3b8' }"
        >
          [{{ log.time }}] {{ log.message }}
        </div>
        <div v-if="logs.length === 0" style="text-align: center; padding: 20px; color: #475569;">
          暂无日志
        </div>
      </div>
    </a-card>

    <!-- 同步历史记录 -->
    <a-card size="small" title="同步历史记录" class="mt-4">
      <template #extra>
        <a-button size="small" @click="loadHistory" :loading="historyLoading">刷新</a-button>
      </template>
      <a-table
        :dataSource="historyItems"
        :columns="historyColumns"
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
        @change="(pag: any) => { historyPage = pag.current || 1; loadHistory() }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'index'">
            <span style="color: #94a3b8">{{ historyPageSize * (historyPage - 1) + (record as any)._index }}</span>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="historyStatusColor(record.status)">
              {{ historyStatusText(record.status) }}
            </a-tag>
          </template>
          <template v-if="column.key === 'started_at'">
            <span>{{ formatHistoryTime(record.started_at) }}</span>
          </template>
          <template v-if="column.key === 'duration'">
            <span>{{ record.duration || '-' }}</span>
          </template>
          <template v-if="column.key === 'activity'">
            <span>{{ record.activity_name || '-' }}</span>
          </template>
          <template v-if="column.key === 'found'">
            <a-tooltip title="已发现 / 已上传到云端 / 失败 / 跳过">
              <span>
                <span style="color: #6366f1">{{ record.total_found }}</span>
                <span style="color: #94a3b8"> / </span>
                <span style="color: #22c55e">{{ record.total_uploaded }}</span>
                <span style="color: #94a3b8"> / </span>
                <span :style="{ color: record.total_failed > 0 ? '#ef4444' : '#94a3b8' }">{{ record.total_failed }}</span>
                <span style="color: #94a3b8"> / </span>
                <span style="color: #f59e0b">{{ record.total_skipped }}</span>
              </span>
            </a-tooltip>
          </template>
          <template v-if="column.key === 'total_bytes'">
            <span>{{ record.total_bytes ? formatSize(record.total_bytes) : '-' }}</span>
          </template>
          <template v-if="column.key === 'config'">
            <a-tooltip placement="topLeft">
              <template #title>
                <div>并发数: {{ record.config?.concurrency ?? '-' }}</div>
                <div>滚动延迟: {{ record.config?.scroll_delay ?? '-' }}秒</div>
                <div>选项卡: {{ record.config?.tab_mode === 'all' ? '全部' : '仅当前' }}</div>
                <div>分子目录: {{ record.config?.tab_subdir ? '是' : '否' }}</div>
              </template>
              <span style="color: #94a3b8; cursor: help;">{{ record.config?.concurrency ?? '-' }}并发</span>
            </a-tooltip>
          </template>
          <template v-if="column.key === 'error_msg'">
            <a-tooltip v-if="record.error_msg" :title="record.error_msg">
              <span style="color: #ef4444; cursor: help;">{{ record.error_msg.length > 30 ? record.error_msg.slice(0, 30) + '...' : record.error_msg }}</span>
            </a-tooltip>
            <span v-else style="color: #d1d5db">-</span>
          </template>
        </template>
      </a-table>
      <div v-if="historyItems.length === 0 && !historyLoading" style="text-align: center; padding: 30px; color: #94a3b8">
        <HistoryOutlined style="font-size: 36px; opacity: 0.3; margin-bottom: 8px" />
        <p>暂无同步历史记录</p>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeftOutlined, PlayCircleOutlined, StopOutlined, CameraOutlined, HistoryOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { wotuApi, type SyncHistoryItem } from '@/api/admin'

const router = useRouter()
const logContainerRef = ref<HTMLElement>()
const starting = ref(false)

const activities = ref<any[]>([])
const photos = ref<any[]>([])
const logs = ref<any[]>([])
const running = ref(false)
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
  activity_id: undefined as number | undefined,
  url: '',
  concurrency: 5,
  scroll_delay: 5,
  tab_mode: 'current',
  tab_subdir: true,
})

let pollTimer: ReturnType<typeof setInterval> | null = null

// 历史记录
const historyItems = ref<SyncHistoryItem[]>([])
const historyLoading = ref(false)
const historyPage = ref(1)
const historyPageSize = ref(20)
const historyTotal = ref(0)

const historyColumns = [
  { title: '#', key: 'index', width: 50, align: 'center' as const },
  { title: '状态', key: 'status', width: 80, align: 'center' as const },
  { title: '活动', key: 'activity', width: 120 },
  { title: '发现/上传/失败/跳过', key: 'found', width: 180, align: 'center' as const },
  { title: '数据量', key: 'total_bytes', width: 90, align: 'right' as const },
  { title: '耗时', key: 'duration', width: 80, align: 'center' as const },
  { title: '配置', key: 'config', width: 80, align: 'center' as const },
  { title: '开始时间', key: 'started_at', width: 160 },
  { title: '错误信息', key: 'error_msg', ellipsis: true },
]

const fallbackImage = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect fill="%231E293B" width="40" height="40"/><text x="20" y="24" text-anchor="middle" fill="%2364748B" font-size="12">?</text></svg>'



const phaseText = computed(() => {
  const map: Record<string, string> = {
    idle: '就绪', scraping: '正在抓取...', downloading: '正在下载...',
    uploading: '正在上传...', completed: '已完成', error: '出错',
  }
  return map[stats.phase] || '就绪'
})

const phaseColor = computed(() => {
  const map: Record<string, string> = {
    idle: 'default', scraping: 'processing', downloading: 'processing',
    uploading: 'processing', completed: 'success', error: 'error',
  }
  return map[stats.phase] || 'default'
})

const progressPercent = computed(() => {
  if (!stats.total_found) return 0
  const done = stats.total_downloaded + stats.total_failed
  return Math.round((done / stats.total_found) * 100)
})

const progressStatus = computed(() => {
  if (stats.phase === 'error') return 'exception' as const
  if (stats.phase === 'completed') return 'success' as const
  if (stats.phase === 'active') return 'active' as const
  return 'normal' as const
})

function statusColor(status: string) {
  const map: Record<string, string> = {
    pending: 'default', downloading: 'processing', uploading: 'processing',
    success: 'success', failed: 'error', skipped: 'warning',
  }
  return map[status] || 'default'
}

function statusText(status: string) {
  const map: Record<string, string> = {
    pending: '等待中', downloading: '下载中', uploading: '上传中',
    success: '成功', failed: '失败', skipped: '已跳过',
  }
  return map[status] || status
}

function formatSize(bytes: number) {
  if (!bytes || bytes <= 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 3)
  return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + ' ' + units[i]
}

function formatDuration(seconds: number) {
  if (seconds < 1) return Math.round(seconds * 1000) + 'ms'
  if (seconds < 60) return seconds.toFixed(1) + 's'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

function filterOption(input: string, option: any) {
  return option.children?.[0]?.children?.toLowerCase().includes(input.toLowerCase())
}

function historyStatusColor(status: string) {
  const map: Record<string, string> = {
    running: 'processing', completed: 'success', failed: 'error', stopped: 'warning',
  }
  return map[status] || 'default'
}

function historyStatusText(status: string) {
  const map: Record<string, string> = {
    running: '运行中', completed: '已完成', failed: '失败', stopped: '已停止',
  }
  return map[status] || status
}

function formatHistoryTime(t: string) {
  return dayjs(t).format('YYYY-MM-DD HH:mm:ss')
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await wotuApi.getSyncHistory(historyPage.value, historyPageSize.value)
    historyItems.value = res.data.items || []
    historyTotal.value = res.data.total || 0
  } catch {} finally {
    historyLoading.value = false
  }
}

function onActivityChange(activityId: number) {
  const activity = activities.value.find(a => a.id === activityId)
  if (activity?.wotu_album_url) {
    form.url = activity.wotu_album_url
  }
}

async function loadActivities() {
  try {
    const res = await wotuApi.getActivities()
    activities.value = res.data || []
  } catch {}
}

async function startSync() {
  if (!form.activity_id) {
    message.warning('请选择活动')
    return
  }
  if (!form.url) {
    message.warning('请输入相册URL')
    return
  }

  starting.value = true
  try {
    await wotuApi.startSync({
      activity_id: form.activity_id,
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
  } catch {
    // error handled by interceptor
  } finally {
    starting.value = false
  }
}

async function stopSync() {
  try {
    await wotuApi.stopSync()
    message.info('已发送停止请求')
  } catch {}
}

async function pollStatus() {
  try {
    const res = await wotuApi.getStatus()
    const data = res.data
    running.value = data.running
    Object.assign(stats, data.stats)

    // 获取增量照片和日志
    const photosRes = await wotuApi.getPhotos()
    const newPhotos = photosRes.data || []
    if (newPhotos.length > photos.value.length) {
      photos.value = newPhotos
    }

    const logsRes = await wotuApi.getLogs()
    const newLogs = logsRes.data || []
    if (newLogs.length > logs.value.length) {
      logs.value = newLogs
      await nextTick()
      if (logContainerRef.value) {
        logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
      }
    }

    // 任务完成后停止轮询
    if (!data.running && (data.stats.phase === 'completed' || data.stats.phase === 'error')) {
      stopPolling()
      // 最终获取一次完整数据
      photos.value = (await wotuApi.getPhotos()).data || []
      logs.value = (await wotuApi.getLogs()).data || []
      // 刷新历史记录
      loadHistory()
    }
  } catch {}
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(pollStatus, 2000)
  pollStatus() // 立即执行一次
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  loadActivities()
  loadHistory()
})

onBeforeUnmount(() => {
  stopPolling()
})
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
.mb-4 {
  margin-bottom: 16px;
}
.mt-4 {
  margin-top: 16px;
}
.flex {
  display: flex;
}
.items-center {
  align-items: center;
}
.justify-between {
  justify-content: space-between;
}
.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  max-height: 500px;
  overflow-y: auto;
}
.photo-card {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.2s, transform 0.2s;
  background: #fff;
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
  line-height: 1.4;
}
.photo-card-status {
  position: absolute;
  bottom: 4px;
  right: 4px;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  line-height: 1.4;
  color: #fff;
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
  font-size: 12px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}
.photo-card-meta {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  justify-content: space-between;
  margin-top: 2px;
}
.photo-card-duration {
  font-size: 11px;
  color: #64748b;
  margin-top: 1px;
}
</style>
