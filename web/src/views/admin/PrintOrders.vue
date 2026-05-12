<template>
  <div class="print-orders-page">
    <div class="page-header">
      <div>
        <h2>打印订单</h2>
        <p>集中查看现场发起的全部打印订单、支付状态和云打印执行状态。</p>
      </div>
      <a-space v-if="activeTab === 'orders'">
        <a-input-search
          v-model:value="keyword"
          class="order-search"
          placeholder="搜索订单号 / 用户 / 节目"
          allow-clear
          enter-button
          @search="loadOrders(1)"
        />
        <a-select v-model:value="statusFilter" class="status-filter" @change="loadOrders(1)">
          <a-select-option value="">全部状态</a-select-option>
          <a-select-option value="queued">排队中</a-select-option>
          <a-select-option value="printing">打印中</a-select-option>
          <a-select-option value="success">成功</a-select-option>
          <a-select-option value="failed">失败</a-select-option>
        </a-select>
        <a-button @click="loadOrders(page)" :loading="loading">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </a-space>
    </div>

    <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
      <a-tab-pane key="orders" tab="订单列表">
        <a-table
          row-key="id"
          :columns="columns"
          :data-source="orders"
          :loading="loading"
          :pagination="pagination"
          size="middle"
          bordered
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'order'">
              <div class="order-no">
                <strong>{{ record.order_no || `P${String(record.id).padStart(8, '0')}` }}</strong>
                <span>ID {{ record.id }}</span>
              </div>
            </template>

        <template v-if="column.key === 'photo'">
          <button v-if="getPrintImageUrl(record)" class="photo-button" type="button" @click="openPreview(record)">
            <img :src="getThumbUrl(getPrintImageUrl(record))" :alt="record.photo_filename || '送印图'" />
          </button>
          <div v-else class="empty-thumb">无图</div>
        </template>

        <template v-if="column.key === 'activity'">
          <div class="stack-text">
            <strong>{{ record.activity_name || `活动 #${record.activity_id}` }}</strong>
            <span>{{ record.template_name || '默认模版' }} / {{ record.copies }} 份</span>
          </div>
        </template>

        <template v-if="column.key === 'program'">
          <div class="stack-text">
            <strong>{{ record.program_sequence_number ? `节目号 ${record.program_sequence_number}` : '未关联节目' }}</strong>
            <span>{{ record.program_name || '-' }}</span>
          </div>
        </template>

        <template v-if="column.key === 'payment'">
          <div class="stack-text">
            <a-tag :color="paymentColor(record.payment_status)">
              {{ paymentText(record.payment_status) }}
            </a-tag>
            <span>{{ formatMoney(record.payment_amount) }} / {{ paymentStateText(record) }}</span>
          </div>
        </template>

        <template v-if="column.key === 'user'">
          <div class="user-cell">
            <a-avatar :src="record.avatar_url || undefined" :size="38">
              {{ (record.nickname || record.user_name || '用').slice(0, 1) }}
            </a-avatar>
            <div class="stack-text">
              <strong>{{ record.nickname || record.user_name || '匿名用户' }}</strong>
              <span>{{ maskOpenid(record.user_identifier) }}</span>
            </div>
          </div>
        </template>

        <template v-if="column.key === 'status'">
          <a-tag :color="printStatusColor(record.status)">{{ printStatusText(record.status) }}</a-tag>
          <div v-if="record.error_msg" class="record-error">{{ record.error_msg }}</div>
        </template>

        <template v-if="column.key === 'created_at'">
          {{ formatTime(record.created_at) }}
        </template>

        <template v-if="column.key === 'actions'">
          <a-button type="primary" size="small" :loading="reprintingId === record.id" @click="handleReprint(record)">
            <template #icon><PrinterOutlined /></template>
            重打
          </a-button>
        </template>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="stats" tab="打印统计">
        <a-spin :spinning="loadingStats">
          <div class="stats-panel">
            <div class="stats-header">
              <div>
                <h3>打印统计</h3>
                <p>汇总全部打印订单、免费次数、付费次数和收入。</p>
              </div>
              <a-button @click="loadStats" :loading="loadingStats">刷新</a-button>
            </div>
            <div class="stats-grid">
              <div class="stat-card">
                <span class="stat-num">{{ stats.total }}</span>
                <span class="stat-label">总打印数</span>
              </div>
              <div class="stat-card free">
                <span class="stat-num">{{ stats.free_count }}</span>
                <span class="stat-label">免费打印</span>
              </div>
              <div class="stat-card paid">
                <span class="stat-num">{{ stats.paid_count }}</span>
                <span class="stat-label">付费打印</span>
              </div>
              <div class="stat-card">
                <span class="stat-num">{{ (stats.total_revenue / 100).toFixed(2) }}</span>
                <span class="stat-label">总收入（元）</span>
              </div>
            </div>
          </div>
        </a-spin>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="previewOpen" title="送印图预览" width="860px" centered>
      <div v-if="previewImageUrl" class="photo-preview">
        <img :src="getPreviewUrl(previewImageUrl)" :alt="previewRecord?.photo_filename || '送印图'" />
        <div class="preview-meta">
          <strong>{{ previewRecord?.photo_filename || `照片 #${previewRecord?.photo_id || '-'}` }}</strong>
          <span>{{ previewRecord?.activity_name || `活动 #${previewRecord?.activity_id || '-'}` }}</span>
        </div>
      </div>
      <a-empty v-else description="暂无可预览送印图" />
      <template #footer>
        <a-space>
          <a-button @click="previewOpen = false">关闭</a-button>
          <a-button type="primary" :disabled="!previewImageUrl" @click="downloadPrintImage">下载送印图</a-button>
        </a-space>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import type { TablePaginationConfig } from 'ant-design-vue'
import { PrinterOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { materialApi, printApi, type PrintRecordItem } from '@/api/admin'
import { getPreviewUrl, getThumbUrl } from '@/utils/image'

const loading = ref(false)
const orders = ref<PrintRecordItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const statusFilter = ref('')
const activeTab = ref('orders')
const loadingStats = ref(false)
const reprintingId = ref<number | null>(null)
const previewOpen = ref(false)
const previewRecord = ref<PrintRecordItem | null>(null)
const stats = reactive({
  total: 0,
  free_count: 0,
  paid_count: 0,
  pending_count: 0,
  refunded_count: 0,
  total_revenue: 0,
})

const columns = [
  { title: '订单号', key: 'order', width: 150 },
  { title: '送印图', key: 'photo', width: 110, align: 'center' as const },
  { title: '所属活动', key: 'activity', width: 220 },
  { title: '节目', key: 'program', width: 180 },
  { title: '支付信息', key: 'payment', width: 170 },
  { title: '发起订单时间', key: 'created_at', width: 180 },
  { title: '用户', key: 'user', width: 220 },
  { title: '打印状态', key: 'status', width: 140 },
  { title: '操作', key: 'actions', width: 110, align: 'center' as const },
]

const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showSizeChanger: true,
  showTotal: (count: number) => `共 ${count} 条`,
}))

const previewImageUrl = computed(() => getPrintImageUrl(previewRecord.value))

function getPrintImageUrl(record?: PrintRecordItem | null) {
  return record?.print_image_url || record?.photo_url || ''
}

async function loadOrders(nextPage = page.value) {
  loading.value = true
  try {
    page.value = nextPage
    const res = await printApi.getPrintRecords({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
      keyword: keyword.value || undefined,
    })
    orders.value = res.data.items
    total.value = res.data.total
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载打印订单失败')
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  loadingStats.value = true
  try {
    const statsData = (await materialApi.getPrintStats() as any)?.data || {}
    Object.assign(stats, statsData)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载打印统计失败')
  } finally {
    loadingStats.value = false
  }
}

function handleTabChange(key: string) {
  if (key === 'stats') {
    loadStats()
  }
}

function handleTableChange(pager: TablePaginationConfig) {
  page.value = pager.current || 1
  pageSize.value = pager.pageSize || 20
  loadOrders(page.value)
}

function openPreview(record: PrintRecordItem) {
  previewRecord.value = record
  previewOpen.value = true
}

function downloadPrintImage() {
  const url = previewImageUrl.value
  if (!url) return
  const link = document.createElement('a')
  link.href = url
  link.download = previewRecord.value?.photo_filename || `print-image-${previewRecord.value?.photo_id || 'sent'}`
  link.target = '_blank'
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

async function handleReprint(record: PrintRecordItem) {
  reprintingId.value = record.id
  try {
    await printApi.reprintRecord(record.id)
    message.success('已提交重打任务')
    loadOrders(page.value)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '提交重打失败')
  } finally {
    reprintingId.value = null
  }
}

function formatTime(value?: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '--'
}

function formatMoney(value?: number | null) {
  if (!value) return '¥0.00'
  return `¥${(value / 100).toFixed(2)}`
}

function maskOpenid(value?: string | null) {
  if (!value) return '无用户标识'
  return value.length <= 8 ? value : `${value.slice(0, 4)}...${value.slice(-4)}`
}

function paymentText(value?: string | null) {
  return ({
    free: '免费',
    pending: '收费',
    paid: '收费',
    refunded: '已退款',
  } as Record<string, string>)[value || ''] || '未知'
}

function paymentColor(value?: string | null) {
  return ({
    free: 'green',
    pending: 'orange',
    paid: 'blue',
    refunded: 'default',
  } as Record<string, string>)[value || ''] || 'default'
}

function paymentStateText(record: PrintRecordItem) {
  if (record.payment_status === 'paid') return '支付成功'
  if (record.payment_status === 'pending') return '待支付'
  if (record.payment_status === 'refunded') return '已退款'
  return '无需支付'
}

function printStatusColor(status: string) {
  return ({
    queued: 'blue',
    printing: 'processing',
    success: 'green',
    failed: 'red',
    cancelled: 'default',
  } as Record<string, string>)[status] || 'default'
}

function printStatusText(status: string) {
  return ({
    queued: '排队中',
    printing: '打印中',
    success: '成功',
    failed: '失败',
    cancelled: '已取消',
  } as Record<string, string>)[status] || status
}

onMounted(() => {
  loadOrders(1)
  loadStats()
})
</script>

<style scoped>
.print-orders-page {
  display: grid;
  gap: 18px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.page-header h2 {
  margin: 0;
  color: #111827;
  font-size: 22px;
}

.page-header p {
  margin: 6px 0 0;
  color: #6b7280;
}

.order-search {
  width: 280px;
}

.status-filter {
  width: 128px;
}

.order-no strong,
.stack-text strong {
  display: block;
  color: #111827;
  font-size: 13px;
}

.order-no span,
.stack-text span {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
}

.photo-button,
.empty-thumb {
  width: 70px;
  height: 70px;
  border-radius: 6px;
}

.photo-button {
  padding: 0;
  overflow: hidden;
  cursor: zoom-in;
  border: 1px solid #e5e7eb;
  background: #f3f4f6;
}

.photo-button img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.empty-thumb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #8c8c8c;
  background: #eef1f6;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.record-error {
  max-width: 220px;
  margin-top: 5px;
  color: #cf1322;
  font-size: 12px;
  white-space: normal;
}

.photo-preview {
  display: grid;
  gap: 14px;
}

.photo-preview img {
  width: 100%;
  max-height: 68vh;
  object-fit: contain;
  border-radius: 8px;
  background: #f5f7fb;
}

.preview-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #4b5563;
}

.stats-panel {
  background: #fff;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 18px;
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.stats-header h3 {
  margin: 0;
  font-size: 16px;
}

.stats-header p {
  margin: 4px 0 0;
  color: #8c8c8c;
  font-size: 13px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-card {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-card.free {
  background: #f6ffed;
}

.stat-card.paid {
  background: #e6f7ff;
}

.stat-num {
  display: block;
  color: #333;
  font-size: 24px;
  font-weight: 700;
}

.stat-card.free .stat-num {
  color: #52c41a;
}

.stat-card.paid .stat-num {
  color: #1890ff;
}

.stat-label {
  color: #999;
  font-size: 12px;
}

@media (max-width: 900px) {
  .page-header {
    display: grid;
  }

  .order-search,
  .status-filter {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
