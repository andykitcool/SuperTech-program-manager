<template>
  <div class="personal-center">
    <header class="pc-header">
      <button class="icon-button" type="button" aria-label="返回" @click="handleBack">
        <ChevronLeft :size="22" />
      </button>
      <h1>个人中心</h1>
      <span class="header-fill" />
    </header>

    <main class="pc-content">
      <section class="profile-panel">
        <div class="avatar-wrap">
          <img v-if="profile?.avatar_url" :src="profile.avatar_url" class="avatar" alt="用户头像" />
          <div v-else class="avatar avatar-fallback">
            <User :size="28" />
          </div>
        </div>
        <div class="profile-info">
          <p class="nickname">{{ profile?.nickname || '微信用户' }}</p>
          <p class="openid">ID {{ shortOpenid }}</p>
        </div>
      </section>

      <button class="editor-entry" type="button" @click="emit('openEditor')">
        <span class="entry-icon">
          <ImageIcon :size="22" />
        </span>
        <span class="entry-copy">
          <strong>进入照片编辑器</strong>
          <span>选择照片继续创作</span>
        </span>
        <ChevronRight :size="20" />
      </button>

      <button v-if="adminEntry?.enabled" class="editor-entry admin-entry" type="button" @click="handleOpenAdminEntry">
        <span class="entry-icon">
          <Printer v-if="adminEntry.management_url === '/m/print-admin'" :size="22" />
          <User v-else :size="22" />
        </span>
        <span class="entry-copy">
          <strong>{{ adminEntry.management_url === '/m/print-admin' ? '进入打印管理' : '进入活动管理' }}</strong>
          <span>{{ adminEntry.management_url === '/m/print-admin' ? '管理打印参数与记录' : '管理授权活动内容' }}</span>
        </span>
        <ChevronRight :size="20" />
      </button>

      <section class="stat-grid">
        <div class="stat-card">
          <Printer :size="18" />
          <span class="stat-value">{{ totalPrints }}</span>
          <span class="stat-label">打印记录</span>
        </div>
        <div class="stat-card">
          <Gift :size="18" />
          <span class="stat-value">{{ quotaInfo?.remaining ?? '--' }}</span>
          <span class="stat-label">免费打印</span>
        </div>
      </section>

      <section class="records-panel">
        <div class="panel-title">
          <div>
            <strong>打印记录</strong>
            <span>查看和管理自己的打印任务</span>
          </div>
          <Printer :size="18" />
        </div>

        <div class="record-list">
          <div v-if="printLoading" class="state-block">
            <a-spin />
          </div>
          <div v-else-if="prints.length === 0" class="state-block empty-state">
            <Printer :size="34" />
            <p>暂无打印记录</p>
          </div>
          <template v-else>
            <article v-for="item in prints" :key="item.id" class="record-item">
              <div class="print-status-icon" :class="getStatusClass(item.status, item.payment_status)">
                <Printer v-if="item.status === 'completed' || item.status === 'success'" :size="18" />
                <Clock v-else-if="item.status === 'queued'" :size="18" />
                <Loader v-else-if="item.status === 'printing'" :size="18" />
                <AlertCircle v-else :size="18" />
              </div>
              <div class="record-info">
                <h2>{{ item.template_name || '打印任务' }}</h2>
                <p>
                  <span class="status-text" :class="getStatusClass(item.status, item.payment_status)">
                    {{ getStatusText(item.status, item.payment_status) }}
                  </span>
                  <span class="record-dot">·</span>
                  <span>{{ formatTime(item.created_at) }}</span>
                </p>
              </div>
              <div class="record-actions">
                <span class="record-badge" :class="item.payment_status">
                  {{ getPaymentLabel(item.payment_status) }}
                </span>
                <button
                  v-if="canDeletePrint(item.status)"
                  class="delete-btn"
                  type="button"
                  aria-label="删除打印记录"
                  @click="handleDeletePrint(item)"
                >
                  <Trash2 :size="15" />
                </button>
              </div>
            </article>
            <button v-if="printHasMore" class="load-more" type="button" @click="loadMorePrints">
              <a-spin v-if="printLoadingMore" size="small" />
              <span v-else>加载更多</span>
            </button>
          </template>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Gift,
  Image as ImageIcon,
  Loader,
  Printer,
  Trash2,
  User,
} from 'lucide-vue-next'
import { publicApi2 } from '@/api/admin'
import type { WechatProfile } from '@/api/admin'

interface PrintRecord {
  id: number
  status: string
  payment_status?: string
  template_name?: string | null
  created_at?: string | null
}

const props = defineProps<{
  activityId: number
  profile: WechatProfile | null
}>()

const emit = defineEmits<{
  back: []
  openEditor: []
}>()

const pageSize = 10
const prints = ref<PrintRecord[]>([])
const printPage = ref(1)
const printHasMore = ref(false)
const printLoading = ref(false)
const printLoadingMore = ref(false)
const totalPrints = ref(0)

const quotaInfo = ref<{ free_quota: number; used_count: number; remaining: number; price: number; pay_enabled: boolean } | null>(null)
const adminEntry = ref<any>(null)

const shortOpenid = computed(() => props.profile?.openid ? props.profile.openid.slice(-8) : '--')

function handleBack() {
  emit('back')
}

async function loadPrints(append = false) {
  if (!props.profile?.openid) return
  if (!append) printLoading.value = true
  else printLoadingMore.value = true

  const page = append ? printPage.value : 1
  try {
    const res = await publicApi2.getUserRecords(props.profile.openid, 'print', page, pageSize) as any
    const data = res?.data || {}
    const items = data.prints || []
    const hasTotal = data.total_prints !== undefined || data.total !== undefined
    totalPrints.value = data.total_prints ?? data.total ?? (append ? prints.value.length + items.length : items.length)

    if (append) prints.value.push(...items)
    else prints.value = items

    printHasMore.value = hasTotal ? prints.value.length < totalPrints.value : items.length === pageSize
  } catch (e) {
    console.error(e)
    message.error('打印记录加载失败')
  } finally {
    printLoading.value = false
    printLoadingMore.value = false
  }
}

function loadMorePrints() {
  printPage.value += 1
  void loadPrints(true)
}

async function loadQuota() {
  if (!props.profile?.openid) return
  try {
    quotaInfo.value = (await publicApi2.checkPrintQuota(props.activityId, props.profile.openid) as any)?.data
  } catch {
    quotaInfo.value = null
  }
}

async function loadAdminEntry() {
  if (!props.profile?.openid) return
  try {
    adminEntry.value = (await publicApi2.getUserAdminEntry(props.profile.openid) as any)?.data
  } catch {
    adminEntry.value = null
  }
}

function handleOpenAdminEntry() {
  const entry = adminEntry.value
  if (!entry?.enabled || !entry.access_token) return
  localStorage.setItem('token', entry.access_token)
  localStorage.setItem('username', entry.username || props.profile?.nickname || '微信管理员')
  localStorage.setItem('permissions', JSON.stringify(entry.permissions || []))
  localStorage.setItem('role_codes', JSON.stringify(entry.role_codes || []))
  localStorage.setItem('activity_ids', JSON.stringify(entry.activity_ids || []))
  window.location.href = entry.management_url || '/m/activity-admin'
}

function handleDeletePrint(item: PrintRecord) {
  if (!props.profile?.openid) return

  Modal.confirm({
    title: '删除打印记录',
    content: '确定删除这条打印记录吗？',
    okText: '删除',
    cancelText: '取消',
    okType: 'danger',
    async onOk() {
      await publicApi2.deletePrintRecord(item.id, props.profile!.openid)
      prints.value = prints.value.filter(record => record.id !== item.id)
      totalPrints.value = Math.max(0, totalPrints.value - 1)
      message.success('打印记录已删除')
    },
  })
}

function formatTime(str: string | null | undefined): string {
  if (!str) return '暂无时间'
  try {
    return new Date(str).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return str
  }
}

function canDeletePrint(status: string): boolean {
  return ['failed', 'queued'].includes(status)
}

function getStatusText(status: string, paymentStatus?: string): string {
  if (paymentStatus === 'free') return '免费打印'
  if (paymentStatus === 'paid') return '已支付打印'
  if (paymentStatus === 'pending') return '待支付'

  const map: Record<string, string> = {
    queued: '排队中',
    printing: '打印中',
    completed: '已完成',
    success: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function getStatusClass(status: string, paymentStatus?: string): string {
  if (status === 'completed' || status === 'success') return 'completed'
  if (status === 'failed') return 'failed'
  if (status === 'printing') return 'printing'
  if (paymentStatus === 'pending') return 'pending'
  return 'active'
}

function getPaymentLabel(paymentStatus?: string): string {
  const map: Record<string, string> = { free: '免费', paid: '已付', pending: '待付' }
  return paymentStatus ? map[paymentStatus] || paymentStatus : '记录'
}

onMounted(() => {
  void loadPrints()
  void loadQuota()
  void loadAdminEntry()
})
</script>

<style scoped>
.personal-center {
  position: fixed;
  inset: 0;
  z-index: 1000;
  overflow-y: auto;
  background: #f6f7fb;
  color: #172033;
  -webkit-overflow-scrolling: touch;
}

.pc-header {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  height: 52px;
  padding: 0 12px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e7eaf0;
  backdrop-filter: blur(14px);
}

.pc-header h1 {
  flex: 1;
  margin: 0;
  text-align: center;
  font-size: 16px;
  font-weight: 700;
}

.icon-button {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 8px;
  background: #eef1f6;
  color: #172033;
}

.header-fill {
  width: 36px;
}

.pc-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 14px calc(24px + env(safe-area-inset-bottom, 0px));
}

.profile-panel {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e7eaf0;
}

.avatar-wrap,
.avatar {
  width: 58px;
  height: 58px;
  flex-shrink: 0;
  border-radius: 50%;
}

.avatar {
  object-fit: cover;
  display: block;
}

.avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e9f7f4;
  color: #0f766e;
}

.profile-info {
  min-width: 0;
}

.nickname {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.openid {
  margin: 0;
  color: #7a8495;
  font-size: 12px;
}

.editor-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border: 0;
  border-radius: 8px;
  background: #122033;
  color: #ffffff;
  text-align: left;
}

.admin-entry {
  background: #17463f;
}

.admin-entry .entry-icon {
  background: #f59e0b !important;
}

.entry-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 8px;
  background: #17a398;
}

.entry-copy {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.entry-copy strong {
  font-size: 16px;
  line-height: 1.25;
}

.entry-copy span {
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.stat-card {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e7eaf0;
  color: #4b5565;
}

.stat-value {
  color: #111827;
  font-size: 20px;
  line-height: 1;
  font-weight: 800;
}

.stat-label {
  color: #7a8495;
  font-size: 12px;
}

.records-panel {
  overflow: hidden;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e7eaf0;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid #edf0f5;
  background: #f8fafc;
}

.panel-title div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.panel-title strong {
  color: #122033;
  font-size: 15px;
}

.panel-title span {
  color: #7a8495;
  font-size: 12px;
}

.state-block {
  min-height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #98a2b3;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.record-list {
  min-height: 180px;
}

.record-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid #edf0f5;
}

.record-item:last-of-type {
  border-bottom: 0;
}

.record-thumb-wrap,
.record-thumb,
.record-thumb-placeholder,
.print-status-icon {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 8px;
}

.record-thumb {
  display: block;
  object-fit: cover;
  background: #eef1f6;
}

.record-thumb-placeholder,
.print-status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eef1f6;
  color: #7a8495;
}

.print-status-icon.completed {
  background: #eaf8ef;
  color: #16803c;
}

.print-status-icon.active {
  background: #eaf2ff;
  color: #2563eb;
}

.print-status-icon.printing {
  background: #fff4dd;
  color: #b45309;
}

.print-status-icon.pending {
  background: #fff0e5;
  color: #c2410c;
}

.print-status-icon.failed {
  background: #feecec;
  color: #dc2626;
}

.record-info {
  flex: 1;
  min-width: 0;
}

.record-info h2 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 14px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-info p {
  margin: 0;
  color: #8a94a6;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-dot {
  margin: 0 4px;
  color: #c3cad5;
}

.status-text.completed {
  color: #16803c;
}

.status-text.active {
  color: #2563eb;
}

.status-text.printing {
  color: #b45309;
}

.status-text.pending {
  color: #c2410c;
}

.status-text.failed {
  color: #dc2626;
}

.record-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.record-badge {
  padding: 4px 8px;
  border-radius: 8px;
  background: #eef1f6;
  color: #687386;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.record-badge.free {
  background: #eaf8ef;
  color: #16803c;
}

.record-badge.paid {
  background: #eaf2ff;
  color: #2563eb;
}

.record-badge.pending {
  background: #fff0e5;
  color: #c2410c;
}

.delete-btn {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 0;
  border-radius: 8px;
  background: #fff1f1;
  color: #d92d20;
}

.load-more {
  width: 100%;
  height: 44px;
  border: 0;
  border-top: 1px solid #edf0f5;
  background: #ffffff;
  color: #4b5565;
  font-size: 13px;
  font-weight: 700;
}

button {
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
</style>
