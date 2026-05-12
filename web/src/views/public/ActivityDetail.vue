<template>
  <div class="delivery-page">
    <header class="delivery-header">
      <button class="icon-button" type="button" aria-label="返回" @click="router.push('/p/index')">
        <ChevronLeft :size="22" />
      </button>
      <h1>{{ activity?.name || '素材交付' }}</h1>
      <span class="header-fill" />
    </header>

    <main class="delivery-content">
      <section class="search-panel">
        <a-input-search
          v-model:value="keyword"
          size="large"
          allow-clear
          placeholder="搜索节目号/节目名"
          enter-button="搜索"
          @search="searchPrograms"
          @change="handleKeywordChange"
        />
      </section>

      <section class="program-panel">
        <div class="panel-title">
          <div>
            <strong>节目列表</strong>
            <span>{{ activity?.program_count || programs.length }} 个节目</span>
          </div>
          <Search :size="18" />
        </div>

        <a-spin :spinning="loading || searching">
          <div class="program-table">
            <div class="program-head">
              <span>节目号</span>
              <span>节目名</span>
              <span>录制时间</span>
              <span>就绪状态</span>
            </div>

            <div v-if="programs.length === 0" class="state-block empty-state">
              <Search :size="34" />
              <p>{{ searched ? '未找到匹配节目' : '暂无节目' }}</p>
            </div>

            <button
              v-for="program in programs"
              :key="program.id"
              type="button"
              class="program-row"
              :class="{ disabled: program.ready_status !== 'ready' }"
              :disabled="program.ready_status !== 'ready'"
              @click="goProgram(program)"
            >
              <span class="program-number">{{ formatSequence(program.sequence_number) }}</span>
              <span class="program-name">{{ program.name }}</span>
              <span class="program-time">{{ formatRecordTime(program.recorded_at) }}</span>
              <span class="status-badge" :class="program.ready_status">
                {{ readyStatusText(program.ready_status) }}
              </span>
            </button>
          </div>
        </a-spin>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ChevronLeft, Search } from 'lucide-vue-next'
import { publicApi, type PublicActivity, type PublicProgramSearchItem } from '@/api/admin'
import { ensureWechatProfile } from '@/utils/wechat'

const route = useRoute()
const router = useRouter()
const activityId = Number(route.params.activityId)
const activity = ref<PublicActivity | null>(null)
const keyword = ref('')
const programs = ref<PublicProgramSearchItem[]>([])
const loading = ref(false)
const searching = ref(false)
const searched = ref(false)
let searchTimer: number | null = null

const fetchActivity = async () => {
  loading.value = true
  try {
    const res = await publicApi.getActivity(activityId)
    activity.value = res.data
  } catch {
    message.error('活动加载失败')
  } finally {
    loading.value = false
  }
}

const searchPrograms = async () => {
  searched.value = true
  searching.value = true
  try {
    const res = await publicApi.searchPrograms(activityId, keyword.value.trim())
    programs.value = res.data
  } catch {
    message.error('节目搜索失败')
  } finally {
    searching.value = false
  }
}

const handleKeywordChange = () => {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(searchPrograms, 260)
}

const formatSequence = (value?: number | null) => String(value ?? '').padStart(3, '0')

const formatRecordTime = (value?: string | null) => {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

const readyStatusText = (status?: string | null) => (status === 'ready' ? '已就绪' : '待就绪')

const goProgram = (program: PublicProgramSearchItem) => {
  const target = program.program_url || `/p/${program.access_token}`
  window.location.href = target
}

onMounted(async () => {
  await ensureWechatProfile(activityId)
  await fetchActivity()
  await searchPrograms()
})
</script>

<style scoped>
.delivery-page {
  min-height: 100vh;
  background: #f4f6fa;
  color: #111827;
}

.delivery-header {
  position: sticky;
  top: 0;
  z-index: 10;
  height: 54px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: rgba(255, 255, 255, 0.94);
  border-bottom: 1px solid #e7eaf0;
  backdrop-filter: blur(12px);
}

.delivery-header h1 {
  flex: 1;
  margin: 0;
  color: #122033;
  font-size: 17px;
  font-weight: 800;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-fill,
.icon-button {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
}

.icon-button {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 8px;
  background: #eef1f6;
  color: #122033;
}

.delivery-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: min(720px, 100%);
  margin: 0 auto;
  padding: 14px;
}

.search-panel {
  padding: 12px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e7eaf0;
}

.program-panel {
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

.program-table {
  min-height: 220px;
}

.program-head,
.program-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) 76px 76px;
  align-items: center;
  gap: 8px;
}

.program-head {
  padding: 10px 14px;
  background: #fbfcfe;
  color: #7a8495;
  font-size: 12px;
  font-weight: 700;
}

.program-row {
  width: 100%;
  min-height: 56px;
  padding: 10px 14px;
  border: 0;
  border-top: 1px solid #edf0f5;
  background: #ffffff;
  color: inherit;
  text-align: left;
}

.program-row:active {
  background: #f4f7fb;
}

.program-row.disabled {
  opacity: 0.72;
}

.program-number {
  width: 52px;
  padding: 5px 0;
  border-radius: 8px;
  background: #eef1f6;
  color: #122033;
  font-size: 13px;
  font-weight: 800;
  text-align: center;
}

.program-name {
  min-width: 0;
  color: #111827;
  font-size: 14px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.program-time {
  color: #687386;
  font-size: 13px;
}

.status-badge {
  justify-self: start;
  padding: 4px 8px;
  border-radius: 8px;
  background: #fff4dd;
  color: #b45309;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.status-badge.ready {
  background: #eaf8ef;
  color: #16803c;
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

@media (max-width: 420px) {
  .delivery-content {
    padding: 12px 10px 16px;
  }

  .program-head,
  .program-row {
    grid-template-columns: 58px minmax(0, 1fr) 60px 66px;
    gap: 6px;
    padding-left: 10px;
    padding-right: 10px;
  }

  .program-number {
    width: 46px;
    font-size: 12px;
  }

  .program-time,
  .status-badge {
    font-size: 11px;
  }
}
</style>
