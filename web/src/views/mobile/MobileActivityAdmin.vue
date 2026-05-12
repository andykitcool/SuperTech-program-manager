<template>
  <div class="mobile-admin-page">
    <header class="mobile-header">
      <button class="icon-btn" type="button" @click="goBack">
        <ChevronLeft :size="21" />
      </button>
      <div>
        <h1>活动管理</h1>
        <p>微信端轻量工作台</p>
      </div>
      <button class="icon-btn" type="button" @click="loadData">
        <RefreshCw :size="18" />
      </button>
    </header>

    <main class="mobile-main">
      <section class="summary-band">
        <div>
          <span class="eyebrow">授权活动</span>
          <strong>{{ activities.length }}</strong>
        </div>
        <div>
          <span class="eyebrow">节目总数</span>
          <strong>{{ totalPrograms }}</strong>
        </div>
        <div>
          <span class="eyebrow">已就绪</span>
          <strong>{{ totalReady }}</strong>
        </div>
      </section>

      <a-spin :spinning="loading">
        <section v-if="activities.length" class="activity-strip">
          <button
            v-for="activity in activities"
            :key="activity.id"
            type="button"
            class="activity-chip"
            :class="{ active: selectedActivity?.id === activity.id }"
            @click="selectActivity(activity)"
          >
            <span>{{ activity.name }}</span>
            <small>{{ formatDate(activity.event_date || activity.start_time) }}</small>
          </button>
        </section>

        <a-empty v-else description="暂无可管理活动" />

        <section v-if="selectedActivity" class="work-card">
          <div class="cover-line">
            <img :src="selectedActivity.cover_image || defaultCover" alt="活动封面" />
            <div class="activity-info">
              <h2>{{ selectedActivity.name }}</h2>
              <p>{{ selectedActivity.venue || '未设置地点' }}</p>
              <div class="tag-row">
                <a-tag :color="selectedActivity.status === 'active' ? 'green' : 'default'">
                  {{ selectedActivity.status === 'active' ? '进行中' : '已结束' }}
                </a-tag>
                <a-tag color="blue">{{ selectedActivity.ready_mode === 'manual' ? '手动就绪' : '自动就绪' }}</a-tag>
              </div>
            </div>
          </div>

          <div class="quick-actions">
            <button type="button" @click="openActivityEdit">
              <Settings :size="17" />
              <span>编辑活动</span>
            </button>
            <button type="button" @click="openCreateProgram">
              <Plus :size="17" />
              <span>新增节目</span>
            </button>
          </div>
        </section>

        <section v-if="selectedActivity" class="section-card">
          <div class="section-title">
            <h3>节目管理</h3>
            <span>{{ programs.length }} 个节目</span>
          </div>

          <div v-if="programs.length" class="program-list">
            <article v-for="program in programs" :key="program.id" class="program-card">
              <div class="program-index">{{ program.sequence_number }}</div>
              <div class="program-main">
                <h4>{{ program.name }}</h4>
                <p>{{ program.photo_count }} 张照片 · {{ videoLabel(program.video_status) }}</p>
              </div>
              <a-switch
                :checked="program.ready_status === 'ready'"
                checked-children="就绪"
                un-checked-children="待定"
                @change="(checked: boolean) => updateReady(program, checked)"
              />
              <button class="text-btn" type="button" @click="openProgramEdit(program)">编辑</button>
            </article>
          </div>

          <a-empty v-else description="暂无节目" />
        </section>
      </a-spin>
    </main>

    <a-modal v-model:open="activityModalOpen" title="编辑活动" ok-text="保存" cancel-text="取消" @ok="saveActivity">
      <a-form layout="vertical">
        <a-form-item label="活动名称">
          <a-input v-model:value="activityForm.name" />
        </a-form-item>
        <a-form-item label="地点">
          <a-input v-model:value="activityForm.venue" />
        </a-form-item>
        <a-form-item label="状态">
          <a-select v-model:value="activityForm.status">
            <a-select-option value="active">进行中</a-select-option>
            <a-select-option value="completed">已结束</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="就绪模式">
          <a-select v-model:value="activityForm.ready_mode">
            <a-select-option value="auto">自动</a-select-option>
            <a-select-option value="manual">手动</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="programModalOpen" :title="programForm.id ? '编辑节目' : '新增节目'" ok-text="保存" cancel-text="取消" @ok="saveProgram">
      <a-form layout="vertical">
        <a-form-item label="节目序号">
          <a-input-number v-model:value="programForm.sequence_number" :min="1" style="width: 100%" />
        </a-form-item>
        <a-form-item label="节目名称">
          <a-input v-model:value="programForm.name" />
        </a-form-item>
        <a-form-item label="就绪状态">
          <a-select v-model:value="programForm.ready_status">
            <a-select-option value="pending">待定</a-select-option>
            <a-select-option value="ready">就绪</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ChevronLeft, Plus, RefreshCw, Settings } from 'lucide-vue-next'
import { adminApi, type Activity, type Program } from '@/api/admin'

const router = useRouter()
const defaultCover = 'https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=900&q=80'
const loading = ref(false)
const activities = ref<Activity[]>([])
const programs = ref<Program[]>([])
const selectedActivity = ref<Activity | null>(null)
const activityModalOpen = ref(false)
const programModalOpen = ref(false)

const activityForm = reactive({
  name: '',
  venue: '',
  status: 'active',
  ready_mode: 'auto',
})

const programForm = reactive({
  id: 0,
  sequence_number: 1,
  name: '',
  ready_status: 'pending',
})

const totalPrograms = computed(() => activities.value.reduce((sum, item) => sum + (item.program_count || 0), 0))
const totalReady = computed(() => activities.value.reduce((sum, item) => sum + (item.ready_program_count || 0), 0))

function goBack() {
  router.back()
}

function formatDate(value?: string | null) {
  if (!value) return '未定日期'
  return new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function videoLabel(status: string) {
  const map: Record<string, string> = { ready: '视频已就绪', uploading: '上传中', none: '无视频' }
  return map[status] || status
}

async function loadData() {
  loading.value = true
  try {
    const res = await adminApi.listActivities()
    activities.value = res.data
    if (!selectedActivity.value || !activities.value.some(item => item.id === selectedActivity.value?.id)) {
      selectedActivity.value = activities.value[0] || null
    } else {
      selectedActivity.value = activities.value.find(item => item.id === selectedActivity.value?.id) || null
    }
    if (selectedActivity.value) await loadPrograms(selectedActivity.value.id)
  } finally {
    loading.value = false
  }
}

async function loadPrograms(activityId: number) {
  const res = await adminApi.listPrograms(activityId)
  programs.value = res.data
}

async function selectActivity(activity: Activity) {
  selectedActivity.value = activity
  await loadPrograms(activity.id)
}

function openActivityEdit() {
  if (!selectedActivity.value) return
  activityForm.name = selectedActivity.value.name
  activityForm.venue = selectedActivity.value.venue || ''
  activityForm.status = selectedActivity.value.status
  activityForm.ready_mode = selectedActivity.value.ready_mode
  activityModalOpen.value = true
}

async function saveActivity() {
  if (!selectedActivity.value) return
  await adminApi.updateActivity(selectedActivity.value.id, { ...activityForm })
  message.success('活动已更新')
  activityModalOpen.value = false
  await loadData()
}

function openCreateProgram() {
  if (!selectedActivity.value) return
  programForm.id = 0
  const lastProgram = programs.value[programs.value.length - 1]
  programForm.sequence_number = (lastProgram?.sequence_number || 0) + 1
  programForm.name = ''
  programForm.ready_status = 'pending'
  programModalOpen.value = true
}

function openProgramEdit(program: Program) {
  programForm.id = program.id
  programForm.sequence_number = program.sequence_number
  programForm.name = program.name
  programForm.ready_status = program.ready_status
  programModalOpen.value = true
}

async function saveProgram() {
  if (!selectedActivity.value) return
  if (!programForm.name.trim()) {
    message.warning('请填写节目名称')
    return
  }
  if (programForm.id) {
    await adminApi.updateProgram(programForm.id, {
      name: programForm.name.trim(),
      sequence_number: programForm.sequence_number,
      ready_status: programForm.ready_status,
    })
  } else {
    await adminApi.createProgram(selectedActivity.value.id, {
      name: programForm.name.trim(),
      sequence_number: programForm.sequence_number,
      ready_status: programForm.ready_status,
    })
  }
  message.success('节目已保存')
  programModalOpen.value = false
  await loadPrograms(selectedActivity.value.id)
}

async function updateReady(program: Program, checked: boolean) {
  await adminApi.updateProgram(program.id, { ready_status: checked ? 'ready' : 'pending' })
  program.ready_status = checked ? 'ready' : 'pending'
  message.success(checked ? '已设为就绪' : '已设为待定')
}

onMounted(loadData)
</script>

<style scoped>
.mobile-admin-page {
  min-height: 100vh;
  background: #f5f7f4;
  color: #16211d;
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
  background: rgba(250, 252, 248, 0.94);
  border-bottom: 1px solid #dfe7dc;
  backdrop-filter: blur(14px);
}

.mobile-header h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
}

.mobile-header p {
  margin: 2px 0 0;
  color: #6f7b73;
  font-size: 12px;
}

.icon-btn {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: #e7eee3;
  color: #223028;
}

.mobile-main {
  padding: 14px 14px 28px;
}

.summary-band {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  overflow: hidden;
  border-radius: 8px;
  background: #dfe7dc;
  border: 1px solid #dfe7dc;
}

.summary-band > div {
  padding: 14px 10px;
  background: #ffffff;
}

.eyebrow {
  display: block;
  color: #778279;
  font-size: 11px;
}

.summary-band strong {
  display: block;
  margin-top: 4px;
  font-size: 23px;
}

.activity-strip {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  margin: 14px -14px 12px;
  padding: 0 14px 4px;
}

.activity-chip {
  min-width: 138px;
  padding: 11px 12px;
  border: 1px solid #dce5d8;
  border-radius: 8px;
  background: #ffffff;
  text-align: left;
}

.activity-chip.active {
  border-color: #1f8a5b;
  background: #e8f6ed;
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
  color: #6f7b73;
}

.work-card,
.section-card {
  margin-top: 12px;
  padding: 14px;
  border: 1px solid #dfe7dc;
  border-radius: 8px;
  background: #ffffff;
}

.cover-line {
  display: flex;
  gap: 12px;
}

.cover-line img {
  width: 86px;
  height: 86px;
  border-radius: 8px;
  object-fit: cover;
  background: #edf2e9;
}

.activity-info {
  min-width: 0;
  flex: 1;
}

.activity-info h2 {
  margin: 2px 0 5px;
  font-size: 17px;
  font-weight: 850;
}

.activity-info p {
  margin: 0 0 8px;
  color: #6f7b73;
  font-size: 13px;
}

.tag-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: 14px;
}

.quick-actions button {
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 0;
  border-radius: 8px;
  background: #16211d;
  color: #ffffff;
  font-weight: 800;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.section-title h3 {
  margin: 0;
  font-size: 16px;
}

.section-title span {
  color: #778279;
  font-size: 12px;
}

.program-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.program-card {
  display: grid;
  grid-template-columns: 34px 1fr auto auto;
  gap: 9px;
  align-items: center;
  padding: 10px;
  border: 1px solid #edf1eb;
  border-radius: 8px;
  background: #fbfcfa;
}

.program-index {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #e8f6ed;
  color: #14724a;
  font-weight: 850;
}

.program-main {
  min-width: 0;
}

.program-main h4,
.program-main p {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.program-main h4 {
  font-size: 14px;
}

.program-main p {
  margin-top: 3px;
  color: #7a857c;
  font-size: 12px;
}

.text-btn {
  border: 0;
  background: transparent;
  color: #14724a;
  font-weight: 800;
}

button {
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
</style>
