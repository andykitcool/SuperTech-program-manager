<template>
  <div class="mobile-print-page">
    <header class="mobile-header">
      <button class="icon-btn" type="button" @click="goBack">
        <ChevronLeft :size="21" />
      </button>
      <div>
        <h1>打印管理</h1>
        <p>微信端打印工作台</p>
      </div>
      <button class="icon-btn" type="button" @click="refreshAll">
        <RefreshCw :size="18" />
      </button>
    </header>

    <main class="mobile-main">
      <a-spin :spinning="loading">
        <section class="metric-grid">
          <div>
            <span>打印总数</span>
            <strong>{{ stats.total }}</strong>
          </div>
          <div>
            <span>免费次数</span>
            <strong>{{ stats.free_count }}</strong>
          </div>
          <div>
            <span>付费次数</span>
            <strong>{{ stats.paid_count }}</strong>
          </div>
          <div>
            <span>收入</span>
            <strong>¥{{ formatMoney(stats.total_revenue) }}</strong>
          </div>
        </section>

        <section class="settings-card">
          <div class="section-title">
            <div>
              <h2>打印参数</h2>
              <p>适合手机现场快速调整</p>
            </div>
            <Printer :size="22" />
          </div>

          <div class="form-grid">
            <label>
              <span>免费次数</span>
              <a-input-number v-model:value="settingsForm.print_free_quota" :min="0" :max="999" />
            </label>
            <label>
              <span>单次价格</span>
              <a-input-number v-model:value="settingsForm.print_price_yuan" :min="0" :precision="2" addon-before="¥" />
            </label>
          </div>

          <div class="pay-row">
            <div>
              <strong>微信支付</strong>
              <span>{{ settingsForm.wechat_pay_enabled ? '已开启' : '未开启' }}</span>
            </div>
            <a-switch v-model:checked="settingsForm.wechat_pay_enabled" />
          </div>

          <div v-if="settingsForm.wechat_pay_enabled" class="pay-fields">
            <a-input v-model:value="settingsForm.wechat_pay_mchid" placeholder="商户号" />
            <a-input-password v-model:value="settingsForm.wechat_pay_api_key" placeholder="API Key" />
            <a-input v-model:value="settingsForm.wechat_pay_notify_url" placeholder="支付回调地址" />
          </div>

          <button class="primary-btn" type="button" :disabled="saving" @click="saveSettings">
            <Save :size="18" />
            <span>{{ saving ? '保存中' : '保存参数' }}</span>
          </button>
        </section>

        <section class="cloud-card">
          <div class="section-title">
            <div>
              <h2>云打印配置</h2>
              <p>{{ cloudPrintForm.enabled ? '蓝阔已启用' : '蓝阔未启用' }}</p>
            </div>
            <SlidersHorizontal :size="22" />
          </div>

          <div class="pay-row compact-row">
            <div>
              <strong>启用云打印</strong>
              <span>{{ cloudPrintForm.providerName }}</span>
            </div>
            <a-switch v-model:checked="cloudPrintForm.enabled" />
          </div>

          <div class="mobile-section-label">默认打印配置</div>
          <div class="form-grid">
            <label>
              <span>纸张尺寸</span>
              <a-select v-model:value="cloudPrintForm.dmPaperSize" :options="paperSizeOptions" />
            </label>
            <label>
              <span>打印方向</span>
              <a-select v-model:value="cloudPrintForm.dmOrientation" :options="orientationOptions" />
            </label>
            <label>
              <span>打印份数</span>
              <a-input-number v-model:value="cloudPrintForm.dmCopies" :min="1" :max="999" />
            </label>
            <label>
              <span>打印颜色</span>
              <a-select v-model:value="cloudPrintForm.dmColor" :options="colorOptions" />
            </label>
            <label>
              <span>双面打印</span>
              <a-select v-model:value="cloudPrintForm.dmDuplex" :options="duplexOptions" />
            </label>
            <label>
              <span>缩放方式</span>
              <a-select v-model:value="cloudPrintForm.jpScale" :options="scaleOptions" />
            </label>
            <label v-if="cloudPrintForm.dmPaperSize === '0'">
              <span>纸宽 0.1mm</span>
              <a-input-number v-model:value="cloudPrintForm.dmPaperWidth" :min="1" />
            </label>
            <label v-if="cloudPrintForm.dmPaperSize === '0'">
              <span>纸高 0.1mm</span>
              <a-input-number v-model:value="cloudPrintForm.dmPaperLength" :min="1" />
            </label>
          </div>

          <div class="mobile-section-label">高级选项</div>
          <div class="form-grid">
            <label>
              <span>HTML 内核</span>
              <a-select v-model:value="cloudPrintForm.htmlKernel" :options="htmlKernelOptions" />
            </label>
            <label>
              <span>自动对齐</span>
              <a-select v-model:value="cloudPrintForm.jpAutoAlign" :options="alignOptions" />
            </label>
            <label>
              <span>打印质量</span>
              <a-select v-model:value="cloudPrintForm.dmPrintQuality" :options="qualityOptions" allow-clear />
            </label>
            <label>
              <span>错误上限</span>
              <a-input-number v-model:value="cloudPrintForm.errLimitNum" :min="1" :max="30" />
            </label>
          </div>

          <div class="wide-fields">
            <a-input v-model:value="cloudPrintForm.jpPageRange" placeholder="页码范围，留空为全部" />
            <a-input v-model:value="cloudPrintForm.callbackUrl" placeholder="打印结果回调 callbackUrl" />
          </div>

          <div class="toggle-grid">
            <label>
              <span>设备异常</span>
              <a-switch v-model:checked="cloudPrintForm.reportDeviceStatus" />
            </label>
            <label>
              <span>打印机异常</span>
              <a-switch v-model:checked="cloudPrintForm.reportPrinterStatus" />
            </label>
            <label>
              <span>文档逆序</span>
              <a-switch v-model:checked="cloudPrintForm.pdfRev" />
            </label>
            <label>
              <span>自动旋转</span>
              <a-switch v-model:checked="cloudPrintForm.jpAutoRotate" />
            </label>
          </div>

          <p class="auto-ext-note">文件链接后缀由系统根据打印文件 URL 自动判断。</p>
        </section>

        <section class="records-card">
          <div class="section-title">
            <div>
              <h2>打印记录</h2>
              <p>{{ selectedActivityName }}</p>
            </div>
            <ReceiptText :size="22" />
          </div>

          <div v-if="activities.length" class="activity-strip">
            <button
              v-for="activity in activities"
              :key="activity.id"
              type="button"
              class="activity-chip"
              :class="{ active: selectedActivityId === activity.id }"
              @click="selectActivity(activity.id)"
            >
              <span>{{ activity.name }}</span>
              <small>{{ formatDate(activity.event_date || activity.start_time) }}</small>
            </button>
          </div>

          <a-empty v-else description="暂无活动数据" />

          <div v-if="records.length" class="record-list">
            <article v-for="record in records" :key="record.id" class="record-item">
              <img v-if="record.photo_url" :src="record.photo_url" alt="打印照片" />
              <div v-else class="photo-placeholder">无图</div>
              <div class="record-main">
                <h3>{{ record.user_name || record.user_identifier || '匿名用户' }}</h3>
                <p>{{ record.program_sequence_number ? `${record.program_sequence_number}. ` : '' }}{{ record.program_name || '未关联节目' }}</p>
                <span>{{ formatDateTime(record.created_at) }}</span>
              </div>
              <a-tag :color="record.status === 'printed' ? 'green' : record.status === 'failed' ? 'red' : 'blue'">
                {{ printStatusLabel(record.status) }}
              </a-tag>
            </article>
          </div>

          <a-empty v-else-if="activities.length" description="暂无打印记录" />
        </section>
      </a-spin>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ChevronLeft, Printer, ReceiptText, RefreshCw, Save, SlidersHorizontal } from 'lucide-vue-next'
import { adminApi, materialApi, printApi, type Activity, type PrintRecordItem } from '@/api/admin'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const activities = ref<Activity[]>([])
const selectedActivityId = ref<number | null>(null)
const records = ref<PrintRecordItem[]>([])

const stats = reactive({
  total: 0,
  free_count: 0,
  paid_count: 0,
  pending_count: 0,
  refunded_count: 0,
  total_revenue: 0,
})

const settingsForm = reactive({
  print_free_quota: 0,
  print_price_yuan: 0,
  wechat_pay_enabled: false,
  wechat_pay_mchid: '',
  wechat_pay_api_key: '',
  wechat_pay_notify_url: '',
})

const defaultCloudPrintConfig = {
  enabled: false,
  provider: 'lankuo',
  providerName: '蓝阔（链科云打印 v3）',
  apiBaseUrl: 'https://cloud.liankenet.com',
  ApiKey: '',
  deviceId: '',
  deviceKey: '',
  devicePort: '1',
  printerType: '1',
  printerModel: '',
  targetIp: '',
  dmPaperSize: '9',
  dmOrientation: '1',
  dmCopies: 1,
  dmColor: '2',
  dmDuplex: '1',
  dmDefaultSource: '',
  dmMediaType: '',
  dmPaperLength: 300,
  dmPaperWidth: 200,
  dmPrintQuality: '',
  jpScale: 'fit',
  jpAutoAlign: 'z5',
  jpPageRange: '',
  htmlKernel: 'chrometopdf',
  callbackUrl: '',
  reportDeviceStatus: true,
  reportPrinterStatus: true,
  errLimitNum: 30,
  pdfRev: false,
  jpAutoRotate: false,
}

const cloudPrintForm = reactive({ ...defaultCloudPrintConfig })

const paperSizeOptions = [
  { label: 'A4（9）', value: '9' },
  { label: 'A5（11）', value: '11' },
  { label: 'A6（70）', value: '70' },
  { label: 'Letter（1）', value: '1' },
  { label: 'Legal（5）', value: '5' },
  { label: '自定义（0）', value: '0' },
]

const orientationOptions = [
  { label: '纵向（1）', value: '1' },
  { label: '横向（2）', value: '2' },
]

const colorOptions = [
  { label: '黑白（1）', value: '1' },
  { label: '彩色（2）', value: '2' },
]

const duplexOptions = [
  { label: '关闭（1）', value: '1' },
  { label: '长边（2）', value: '2' },
  { label: '短边（3）', value: '3' },
]

const scaleOptions = [
  { label: '自适应', value: 'fit' },
  { label: '宽度优先', value: 'fitw' },
  { label: '高度优先', value: 'fith' },
  { label: '拉伸全图', value: 'fill' },
  { label: '裁剪铺满', value: 'cover' },
  { label: '不缩放', value: 'none' },
]

const alignOptions = [
  { label: '左上 z1', value: 'z1' },
  { label: '中上 z2', value: 'z2' },
  { label: '右上 z3', value: 'z3' },
  { label: '左中 z4', value: 'z4' },
  { label: '居中 z5', value: 'z5' },
  { label: '右中 z6', value: 'z6' },
  { label: '左下 z7', value: 'z7' },
  { label: '中下 z8', value: 'z8' },
  { label: '右下 z9', value: 'z9' },
]

const htmlKernelOptions = [
  { label: 'chrometopdf', value: 'chrometopdf' },
  { label: 'wkhtmltopdf', value: 'wkhtmltopdf' },
  { label: 'wkhtml', value: 'wkhtml' },
]

const qualityOptions = [
  { label: '最低 -1', value: '-1' },
  { label: '较低 -2', value: '-2' },
  { label: '较高 -3', value: '-3' },
  { label: '最高 -4', value: '-4' },
]

const selectedActivityName = computed(() => {
  const activity = activities.value.find(item => item.id === selectedActivityId.value)
  return activity ? activity.name : '选择活动查看最近记录'
})

function goBack() {
  router.back()
}

function applyCloudPrintConfig(value: Record<string, any>) {
  const { urlFileExt: _urlFileExt, ...cleaned } = value || {}
  Object.assign(cloudPrintForm, {
    ...defaultCloudPrintConfig,
    ...cleaned,
    provider: 'lankuo',
    providerName: '蓝阔（链科云打印 v3）',
    reportDeviceStatus: cleaned.reportDeviceStatus ?? true,
    reportPrinterStatus: cleaned.reportPrinterStatus ?? true,
  })
}

function cloudPrintPayload() {
  const { urlFileExt: _urlFileExt, ...payload } = { ...cloudPrintForm } as Record<string, any>
  return payload
}

function formatMoney(value: number) {
  return (Number(value || 0) / 100).toFixed(2)
}

function formatDate(value?: string | null) {
  if (!value) return '未定日期'
  return new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function formatDateTime(value?: string | null) {
  if (!value) return '暂无时间'
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function printStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待打印',
    queued: '队列中',
    printing: '打印中',
    printed: '已打印',
    failed: '失败',
  }
  return labels[status] || status
}

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([loadSettings(), loadActivities()])
    await Promise.all([loadStats(), loadRecords()])
  } finally {
    loading.value = false
  }
}

async function loadSettings() {
  const res = await materialApi.getPrintSettings()
  const data = (res.data || {}) as any
  settingsForm.print_free_quota = Number(data.print_free_quota || 0)
  settingsForm.print_price_yuan = Number(data.print_price || 0) / 100
  settingsForm.wechat_pay_enabled = Boolean(data.wechat_pay_enabled)
  settingsForm.wechat_pay_mchid = data.wechat_pay_mchid || ''
  settingsForm.wechat_pay_api_key = data.wechat_pay_api_key || ''
  settingsForm.wechat_pay_notify_url = data.wechat_pay_notify_url || ''
  applyCloudPrintConfig(data.lankuo_print_config || {})
}

async function loadActivities() {
  const res = await adminApi.listActivities()
  activities.value = res.data || []
  if (!selectedActivityId.value || !activities.value.some(item => item.id === selectedActivityId.value)) {
    selectedActivityId.value = activities.value[0]?.id || null
  }
}

async function loadStats() {
  const res = await materialApi.getPrintStats(selectedActivityId.value || undefined)
  Object.assign(stats, res.data || {})
}

async function loadRecords() {
  if (!selectedActivityId.value) {
    records.value = []
    return
  }
  const res = await printApi.getActivityPrintRecords(selectedActivityId.value, 1, 8)
  records.value = res.data.items || []
}

async function selectActivity(activityId: number) {
  selectedActivityId.value = activityId
  loading.value = true
  try {
    await Promise.all([loadStats(), loadRecords()])
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await materialApi.updatePrintSettings({
      print_free_quota: settingsForm.print_free_quota,
      print_price: Math.round(Number(settingsForm.print_price_yuan || 0) * 100),
      wechat_pay_enabled: settingsForm.wechat_pay_enabled,
      wechat_pay_mchid: settingsForm.wechat_pay_mchid,
      wechat_pay_api_key: settingsForm.wechat_pay_api_key,
      wechat_pay_notify_url: settingsForm.wechat_pay_notify_url,
      lankuo_print_config: cloudPrintPayload(),
    })
    message.success('打印参数已保存')
    await loadStats()
  } finally {
    saving.value = false
  }
}

onMounted(refreshAll)
</script>

<style scoped>
.mobile-print-page {
  min-height: 100vh;
  background: #f7f4ee;
  color: #211c17;
}

.mobile-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: grid;
  grid-template-columns: 42px 1fr 42px;
  gap: 10px;
  align-items: center;
  padding: 12px 14px;
  background: rgba(255, 253, 248, 0.94);
  border-bottom: 1px solid #e4ddd1;
  backdrop-filter: blur(14px);
}

.mobile-header h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 850;
}

.mobile-header p {
  margin: 2px 0 0;
  color: #766d60;
  font-size: 12px;
}

.icon-btn {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: #ece3d4;
  color: #2b241d;
}

.mobile-main {
  padding: 14px 14px 28px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.metric-grid div,
.settings-card,
.cloud-card,
.records-card {
  border: 1px solid #e2d8ca;
  border-radius: 8px;
  background: #ffffff;
}

.metric-grid div {
  padding: 13px;
}

.metric-grid span {
  color: #7b7062;
  font-size: 12px;
}

.metric-grid strong {
  display: block;
  margin-top: 4px;
  font-size: 23px;
  line-height: 1.1;
}

.settings-card,
.cloud-card,
.records-card {
  margin-top: 12px;
  padding: 14px;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-title h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 850;
}

.section-title p {
  margin: 3px 0 0;
  color: #786f64;
  font-size: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.form-grid label span {
  color: #786f64;
  font-size: 12px;
}

.form-grid :deep(.ant-input-number) {
  width: 100%;
}

.form-grid :deep(.ant-select) {
  width: 100%;
}

.mobile-section-label {
  margin: 15px 0 9px;
  color: #2a413e;
  font-size: 13px;
  font-weight: 850;
}

.pay-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  padding: 11px 12px;
  border-radius: 8px;
  background: #f8f3ea;
}

.compact-row {
  margin-bottom: 2px;
}

.pay-row strong,
.pay-row span {
  display: block;
}

.pay-row span {
  margin-top: 2px;
  color: #81766a;
  font-size: 12px;
}

.pay-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.wide-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.toggle-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.toggle-grid label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 42px;
  padding: 9px 10px;
  border-radius: 8px;
  background: #f7f6f0;
}

.toggle-grid span {
  color: #514940;
  font-size: 12px;
  font-weight: 750;
}

.auto-ext-note {
  margin: 10px 0 0;
  padding: 9px 10px;
  border-radius: 8px;
  background: #edf6f3;
  color: #2d625d;
  font-size: 12px;
}

.primary-btn {
  width: 100%;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 14px;
  border: 0;
  border-radius: 8px;
  background: #1f5d57;
  color: #ffffff;
  font-weight: 850;
}

.primary-btn:disabled {
  opacity: 0.72;
}

.activity-strip {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  margin: 0 -14px 12px;
  padding: 0 14px 4px;
}

.activity-chip {
  min-width: 136px;
  padding: 10px 11px;
  border: 1px solid #e2d8ca;
  border-radius: 8px;
  background: #fffdf8;
  text-align: left;
}

.activity-chip.active {
  border-color: #1f5d57;
  background: #e8f3f0;
}

.activity-chip span,
.activity-chip small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-chip span {
  font-weight: 800;
}

.activity-chip small {
  margin-top: 3px;
  color: #7d7368;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.record-item {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 9px;
  border: 1px solid #eee7dd;
  border-radius: 8px;
  background: #fffdf9;
}

.record-item img,
.photo-placeholder {
  width: 54px;
  height: 54px;
  border-radius: 8px;
  object-fit: cover;
  background: #efe8dc;
}

.photo-placeholder {
  display: grid;
  place-items: center;
  color: #8c8175;
  font-size: 12px;
}

.record-main {
  min-width: 0;
}

.record-main h3,
.record-main p,
.record-main span {
  display: block;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-main h3 {
  font-size: 14px;
  font-weight: 850;
}

.record-main p {
  margin-top: 3px;
  color: #6f675e;
  font-size: 12px;
}

.record-main span {
  margin-top: 2px;
  color: #93877b;
  font-size: 11px;
}

button {
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
</style>
