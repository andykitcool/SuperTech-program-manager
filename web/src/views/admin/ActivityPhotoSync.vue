<template>
  <div class="photo-sync-workspace">
    <a-card title="喔图照片同步" class="sync-card">
      <div class="sync-mode-row">
        <span class="sync-mode-label">同步模式</span>
        <a-switch
          v-model:checked="syncMode"
          checked-children="API 同步"
          un-checked-children="本地同步"
          :loading="syncModeLoading"
          @change="onSyncModeChange"
        />
      </div>

      <a-alert
        v-if="syncMode"
        type="info"
        show-icon
        message="API 同步会把喔图相册任务派发到独立照片同步服务器执行，主服务器只接收进度和照片入库回调。"
        banner
        class="sync-mode-alert"
      />

      <div v-if="syncMode" class="api-config-panel">
        <div class="api-config-header">
          <div>
            <div class="api-config-title">API 同步配置</div>
            <div class="muted-text">
              API 密钥必须与独立同步项目的 WOTU_API_KEY 一致，回调地址必须是主项目公网域名。
            </div>
          </div>
          <a-tag :color="apiConfig.configured ? 'green' : 'orange'">
            {{ apiConfig.configured ? '已配置' : '未完整配置' }}
          </a-tag>
        </div>

        <a-form layout="vertical">
          <a-row :gutter="16">
            <a-col :xs="24" :lg="8">
              <a-form-item label="独立同步服务地址">
                <a-input
                  v-model:value="apiConfigForm.service_url"
                  placeholder="https://wotu-sync.example.com"
                />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :lg="8">
              <a-form-item label="API 密钥">
                <a-input-password
                  v-model:value="apiConfigForm.api_key"
                  :placeholder="apiConfig.has_api_key ? '已配置，留空不修改' : '请输入共享密钥'"
                />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :lg="8">
              <a-form-item label="主项目回调公网地址">
                <a-input
                  v-model:value="apiConfigForm.callback_base_url"
                  placeholder="https://wechat.vidiu.cn"
                />
              </a-form-item>
            </a-col>
          </a-row>

          <div class="callback-list">
            <div class="callback-item">
              <span>照片入库</span>
              <code>{{ apiConfig.callback_urls.photo_uploaded || '-' }}</code>
            </div>
            <div class="callback-item">
              <span>任务完成</span>
              <code>{{ apiConfig.callback_urls.task_complete || '-' }}</code>
            </div>
            <div class="callback-item">
              <span>进度上报</span>
              <code>{{ apiConfig.callback_urls.task_progress || '-' }}</code>
            </div>
          </div>

          <a-space class="api-config-actions">
            <a-button type="primary" :loading="apiConfigSaving" @click="saveApiConfig">保存配置</a-button>
            <a-button :loading="apiConfigLoading" @click="loadApiConfig">重新读取</a-button>
          </a-space>
        </a-form>
      </div>

      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :xs="24" :lg="10">
            <a-form-item label="当前活动">
              <a-input :value="activity.name" disabled />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :lg="14">
            <a-form-item label="喔图相册地址">
              <a-input v-model:value="form.url" placeholder="https://m.alltuu.com/album/..." />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :xs="24" :md="6">
            <a-form-item label="并发下载数">
              <a-input-number v-model:value="form.concurrency" :min="1" :max="20" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="6">
            <a-form-item label="API 轮询间隔（秒）">
              <a-input-number v-model:value="form.scroll_delay" :min="1" :max="30" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="6">
            <a-form-item label="无新照片停止次数">
              <a-input-number v-model:value="form.no_new_stop_rounds" :min="1" :max="999" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="6">
            <a-form-item label="默认同步范围">
              <a-select v-model:value="form.tab_mode">
                <a-select-option value="current">当前分类</a-select-option>
                <a-select-option value="all">全部分类</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <div class="album-info-bar">
          <a-space wrap>
            <a-button :loading="albumLoading" @click="loadAlbumInfo">
              <template #icon><SearchOutlined /></template>
              获取相册信息
            </a-button>
            <a-tag v-if="albumInfo" color="blue">照片总数：{{ albumInfo.total }} 张</a-tag>
            <a-tag v-if="albumInfo" color="default">分类：{{ albumInfo.categories.length }} 个</a-tag>
          </a-space>
        </div>

        <div v-if="albumInfo?.categories?.length" class="category-panel">
          <div class="category-panel-title">
            <span>下载分类范围</span>
            <a-space>
              <a-button size="small" @click="selectAllCategories">全选</a-button>
              <a-button size="small" @click="clearCategories">清空</a-button>
            </a-space>
          </div>
          <a-checkbox-group v-model:value="selectedCategoryKeys" class="category-grid">
            <a-checkbox
              v-for="category in albumInfo.categories"
              :key="categoryKey(category)"
              :value="categoryKey(category)"
            >
              {{ category.name || '默认分类' }}
              <span class="category-count">{{ category.count || 0 }} 张</span>
            </a-checkbox>
          </a-checkbox-group>
        </div>
      </a-form>

      <a-space class="action-row">
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
        <a-card size="small"><a-statistic title="发现照片" :value="stats.total_found" /></a-card>
      </a-col>
      <a-col :xs="12" :lg="6">
        <a-card size="small"><a-statistic title="已下载" :value="stats.total_downloaded" /></a-card>
      </a-col>
      <a-col :xs="12" :lg="6">
        <a-card size="small"><a-statistic title="已上传云存储" :value="stats.total_uploaded" /></a-card>
      </a-col>
      <a-col :xs="12" :lg="6">
        <a-card size="small"><a-statistic title="失败" :value="stats.total_failed" /></a-card>
      </a-col>
    </a-row>

    <a-card size="small" class="sync-card">
      <div class="progress-header">
        <span>
          <a-tag :color="phaseColor">{{ phaseText }}</a-tag>
          <span v-if="stats.current_tab" class="muted-text">当前分类：{{ stats.current_tab }}</span>
        </span>
        <span>{{ stats.total_downloaded + stats.total_failed }} / {{ stats.total_found || 0 }}</span>
      </div>
      <div v-if="stats.total_skipped > 0" class="muted-text">已跳过 {{ stats.total_skipped }} 张已存在照片</div>
    </a-card>

    <a-card size="small" class="sync-card">
      <div class="log-header" @click="logExpanded = !logExpanded">
        <span class="log-header-title">
          <a-switch :checked="logExpanded" size="small" class="log-toggle-switch" />
          实时日志 ({{ logs.length }})
        </span>
        <a-space>
          <a-button size="small" @click.stop="logs = []">清空</a-button>
          <span class="log-expand-icon">{{ logExpanded ? '收起' : '展开' }}</span>
        </a-space>
      </div>
      <div v-if="logExpanded" ref="logContainerRef" class="log-panel">
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
import { PlayCircleOutlined, SearchOutlined, StopOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import {
  wotuApi,
  type Activity,
  type WotuAlbumInfo,
  type WotuApiSyncConfig,
  type WotuCategoryInfo,
} from '@/api/admin'

const props = defineProps<{
  activityId: number
  activity: Activity
}>()

const starting = ref(false)
const albumLoading = ref(false)
const running = ref(false)
const syncModeLoading = ref(false)
const apiConfigLoading = ref(false)
const apiConfigSaving = ref(false)
const logs = ref<any[]>([])
const logContainerRef = ref<HTMLElement>()
const albumInfo = ref<WotuAlbumInfo | null>(null)
const selectedCategoryKeys = ref<string[]>([])
const syncMode = ref(props.activity.sync_mode === 'api')
const logExpanded = ref(true)

const emptyApiConfig: WotuApiSyncConfig = {
  service_url: '',
  api_key: '',
  callback_base_url: '',
  has_api_key: false,
  configured: false,
  callback_urls: {
    photo_uploaded: '',
    task_complete: '',
    task_progress: '',
  },
}

const apiConfig = reactive<WotuApiSyncConfig>({ ...emptyApiConfig, callback_urls: { ...emptyApiConfig.callback_urls } })
const apiConfigForm = reactive({
  service_url: '',
  api_key: '',
  callback_base_url: '',
})

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
  no_new_stop_rounds: 3,
  tab_mode: 'current',
  tab_subdir: true,
})

let pollTimer: ReturnType<typeof setInterval> | null = null

const phaseText = computed(() => {
  const map: Record<string, string> = {
    idle: '待命',
    scraping: '检查新照片',
    downloading: '下载中',
    uploading: '上传中',
    completed: '已完成',
    stopped: '已停止',
    error: '出错',
  }
  return map[stats.phase] || '待命'
})

const phaseColor = computed(() => {
  const map: Record<string, string> = {
    idle: 'default',
    scraping: 'processing',
    downloading: 'processing',
    uploading: 'processing',
    completed: 'success',
    stopped: 'warning',
    error: 'error',
  }
  return map[stats.phase] || 'default'
})

const selectedCategories = computed(() => {
  if (!albumInfo.value) return []
  const selected = new Set(selectedCategoryKeys.value)
  return albumInfo.value.categories.filter((category) => selected.has(categoryKey(category)))
})

function assignApiConfig(config: WotuApiSyncConfig) {
  Object.assign(apiConfig, config)
  apiConfig.callback_urls = config.callback_urls || { ...emptyApiConfig.callback_urls }
  apiConfigForm.service_url = config.service_url || ''
  apiConfigForm.callback_base_url = config.callback_base_url || ''
  apiConfigForm.api_key = ''
}

async function loadApiConfig() {
  apiConfigLoading.value = true
  try {
    const res = await wotuApi.getApiConfig()
    assignApiConfig(res.data)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '读取 API 同步配置失败')
  } finally {
    apiConfigLoading.value = false
  }
}

async function saveApiConfig() {
  apiConfigSaving.value = true
  try {
    const payload: { service_url: string; callback_base_url: string; api_key?: string } = {
      service_url: apiConfigForm.service_url,
      callback_base_url: apiConfigForm.callback_base_url,
    }
    if (apiConfigForm.api_key) {
      payload.api_key = apiConfigForm.api_key
    }
    const res = await wotuApi.updateApiConfig(payload)
    assignApiConfig(res.data)
    message.success('API 同步配置已保存')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '保存 API 同步配置失败')
  } finally {
    apiConfigSaving.value = false
  }
}

function categoryKey(category: WotuCategoryInfo) {
  return category.category_id || `index:${category.index ?? category.name}`
}

function selectAllCategories() {
  selectedCategoryKeys.value = albumInfo.value?.categories.map(categoryKey) || []
}

function clearCategories() {
  selectedCategoryKeys.value = []
}

async function loadAlbumInfo() {
  if (!form.url) {
    message.warning('请填写喔图相册地址')
    return
  }
  albumLoading.value = true
  try {
    const res = await wotuApi.getAlbumInfo(form.url)
    albumInfo.value = res.data
    selectedCategoryKeys.value = res.data.categories.map(categoryKey)
    form.tab_mode = res.data.categories.length > 1 ? 'all' : 'current'
    message.success(`已获取相册信息：${res.data.total} 张照片`)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '获取相册信息失败')
  } finally {
    albumLoading.value = false
  }
}

async function onSyncModeChange(checked: boolean) {
  syncModeLoading.value = true
  try {
    await wotuApi.setSyncMode(props.activityId, checked ? 'api' : 'local')
    if (checked) {
      await loadApiConfig()
    }
    message.success(`已切换至${checked ? 'API 同步' : '本地同步'}模式`)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '切换同步模式失败')
    syncMode.value = !checked
  } finally {
    syncModeLoading.value = false
  }
}

async function startSync() {
  if (!form.url) {
    message.warning('请填写喔图相册地址')
    return
  }
  if (syncMode.value && !apiConfig.configured) {
    await loadApiConfig()
    if (!apiConfig.configured) {
      message.warning('请先完整填写 API 同步配置')
      return
    }
  }
  if (albumInfo.value?.categories.length && selectedCategories.value.length === 0) {
    message.warning('请至少选择一个分类')
    return
  }

  starting.value = true
  try {
    await wotuApi.startSync({
      activity_id: props.activityId,
      url: form.url,
      concurrency: form.concurrency,
      scroll_delay: form.scroll_delay,
      no_new_stop_rounds: form.no_new_stop_rounds,
      tab_mode: selectedCategories.value.length > 0 ? 'all' : form.tab_mode,
      tab_subdir: form.tab_subdir,
      selected_categories: selectedCategories.value,
      sync_mode: syncMode.value ? 'api' : 'local',
    })
    message.success('同步任务已启动')
    logs.value = []
    startPolling()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '启动同步失败')
  } finally {
    starting.value = false
  }
}

async function stopSync() {
  const params: any = {}
  if (syncMode.value) {
    params.activity_id = props.activityId
  }
  try {
    const res = await wotuApi.stopSync(params)
    message.info(res.data?.message || '已发送停止请求')
    await pollStatus()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '停止同步失败')
  }
}

async function refreshStatus() {
  await pollStatus()
}

async function pollStatus() {
  try {
    const params: any = {}
    if (syncMode.value) {
      params.activity_id = props.activityId
    }
    const res = await wotuApi.getStatus(params)
    const data = res.data
    running.value = data.running
    Object.assign(stats, data.stats)

    if (!syncMode.value || !data.running) {
      try {
        const logsRes = await wotuApi.getLogs()
        logs.value = logsRes.data || []
      } catch {
        // Ignore log fetch errors during polling.
      }
    }

    await nextTick()
    if (logContainerRef.value && logExpanded.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
    }

    if (!data.running && ['completed', 'error', 'stopped'].includes(data.stats?.phase)) {
      stopPolling()
    }
  } catch {
    // Polling will retry on the next tick or manual refresh.
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

watch(
  () => props.activity.sync_mode,
  (mode) => {
    syncMode.value = mode === 'api'
    if (syncMode.value) {
      loadApiConfig()
    }
  },
)

onMounted(() => {
  if (syncMode.value) {
    loadApiConfig()
  }
  refreshStatus()
})
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

.sync-mode-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.sync-mode-label {
  font-weight: 600;
  color: #1f2937;
  white-space: nowrap;
}

.sync-mode-alert {
  margin-bottom: 16px;
}

.api-config-panel {
  margin-bottom: 16px;
  padding: 14px;
  border: 1px solid #d9e7ff;
  border-radius: 8px;
  background: #f7fbff;
}

.api-config-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.api-config-title {
  font-weight: 700;
  color: #1f2937;
}

.callback-list {
  display: grid;
  gap: 8px;
  margin-top: -4px;
}

.callback-item {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 12px;
}

.callback-item code {
  display: block;
  min-width: 0;
  overflow-wrap: anywhere;
  color: #0f172a;
  background: transparent;
}

.api-config-actions {
  margin-top: 12px;
}

.album-info-bar {
  padding-top: 2px;
}

.category-panel {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fafbfc;
}

.category-panel-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  font-weight: 700;
  color: #1f2937;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px 12px;
}

.category-count {
  margin-left: 6px;
  color: #8c8c8c;
  font-size: 12px;
}

.action-row {
  margin-top: 16px;
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
  color: #64748b;
  font-size: 12px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.log-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #1f2937;
}

.log-toggle-switch {
  margin-right: 4px;
}

.log-expand-icon {
  color: #1890ff;
  font-size: 12px;
}

.log-panel {
  max-height: 250px;
  overflow-y: auto;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.8;
  margin-top: 8px;
}
</style>
