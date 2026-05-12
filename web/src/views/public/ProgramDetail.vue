<template>
  <!-- 微信授权门控 -->
  <WeChatAuthGate
    v-if="program?.activity_id"
    :activity-id="program.activity_id"
    :redirect-path="currentPath"
    @authorized="onWechatAuthorized"
  >
    <template #default="{ profile }">
      <div class="public-page">
        <!-- 顶部导航 -->
        <div class="detail-nav">
          <button class="nav-back" @click="goBack">
            <ChevronLeft :size="22" />
          </button>
          <span class="nav-title">{{ program?.name || '节目详情' }}</span>
          <button class="nav-user" @click="showPersonalCenter = true">
            <Menu :size="20" />
          </button>
        </div>

        <a-spin :spinning="loading">
          <template v-if="program">
            <!-- 视频区 -->
            <div class="video-section" v-if="program.video_url">
              <video
                :src="program.video_url"
                controls
                playsinline
                preload="metadata"
                class="video-player"
              ></video>
            </div>

            <!-- 照片区 -->
            <div class="photo-section">
              <div class="section-header">
                <h3>
                  <CameraOutlined />
                  精彩照片
                  <span class="photo-count" v-if="photos.length > 0">（{{ totalPhotos }}张）</span>
                </h3>
                <button class="edit-hint" @click="showEditTip = !showEditTip">
                  <EditOutlined :size="16" />
                  <span v-if="showEditTip">点击照片进入编辑器</span>
                </button>
              </div>

              <a-skeleton :loading="photosLoading" active :paragraph="{ rows: 6 }">
                <div v-if="photos.length > 0" class="photo-grid">
                  <button
                    v-for="(photo, index) in photos"
                    :key="photo.id"
                    type="button"
                    class="photo-item"
                    :class="{ selected: selectedPhotoIds.has(photo.id), selecting: photoSelectMode }"
                    @click="handlePhotoTap(photo, index)"
                    @touchstart.passive="startPhotoLongPress(photo.id)"
                    @touchend="clearPhotoLongPress"
                    @touchcancel="clearPhotoLongPress"
                    @mousedown="startPhotoLongPress(photo.id)"
                    @mouseup="clearPhotoLongPress"
                    @mouseleave="clearPhotoLongPress"
                    @contextmenu.prevent="enterPhotoSelectMode(photo.id)"
                  >
                    <img :src="getThumbUrl(getPhotoSource(photo))" :alt="`照片 ${index + 1}`" loading="lazy" />
                    <span v-if="photoSelectMode" class="photo-select-dot" :class="{ checked: selectedPhotoIds.has(photo.id) }">
                      <Check v-if="selectedPhotoIds.has(photo.id)" :size="14" />
                    </span>
                    <div class="photo-edit-overlay">
                      <EditOutlined :size="20" />
                    </div>
                  </button>
                </div>
                <a-empty v-else description="暂无照片" style="padding: 40px 0" />
              </a-skeleton>

              <div class="load-more" v-if="hasMorePhotos">
                <a-button @click="loadMorePhotos" :loading="loadingMore">
                  加载更多
                </a-button>
              </div>

              <div v-if="photoSelectMode" class="photo-select-bar">
                <span>已选择 {{ selectedPhotoIds.size }} 张</span>
                <div class="photo-select-actions">
                  <button type="button" class="confirm" @click="confirmPhotoSelection">确定</button>
                  <button type="button" @click="clearPhotoSelection">取消</button>
                </div>
              </div>
            </div>
          </template>

          <a-result
            v-if="notFound"
            status="404"
            title="节目未找到"
            sub-title="该节目不存在或素材尚未就绪，请通过公众号对话获取节目链接"
          />
        </a-spin>
      </div>

      <!-- 个人中心 -->
      <PersonalCenter
        v-if="showPersonalCenter"
        :activity-id="program?.activity_id || 0"
        :profile="authorizedProfile"
        @back="showPersonalCenter = false"
        @open-editor="openEditorFromCenter"
      />

      <!-- 画布编辑器 -->
      <PhotoEditor
        v-if="editingPhotos.length"
        :photo-url="editingPhotos[0]?.url || ''"
        :photo-id="editingPhotos[0]?.id || 0"
        :photos="editingPhotos"
        :program-token="token"
        :activity-id="program?.activity_id || 0"
        :wechat-profile="authorizedProfile"
        :canvas-width="canvasWidth"
        :canvas-height="canvasHeight"
        :photo-init-x="photoInitX"
        :photo-init-y="photoInitY"
        :photo-init-scale="photoInitScale"
        :photo-margin="photoMargin"
        :template-name="templateName"
        :paper-size="paperSize"
        :photo-slots="photoSlots"
        :template-canvas-json="templateCanvasJson"
        @back="editingPhotos = []"
      />
    </template>
  </WeChatAuthGate>

  <!-- 加载中但未获取到activity_id -->
  <div v-if="!program?.activity_id && !notFound" class="loading-initial">
    <a-spin size="large" />
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  CameraOutlined,
  EditOutlined,
} from '@ant-design/icons-vue'
import { Check, ChevronLeft, Menu } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import { publicApi, publicApi2, type Program, type PhotoItem, type WechatProfile } from '@/api/admin'
import { getPhotoUrl, getPreviewUrl, getThumbUrl } from '@/utils/image'
import WeChatAuthGate from './WeChatAuthGate.vue'
import PersonalCenter from './PersonalCenter.vue'

const PhotoEditor = defineAsyncComponent(() => import('./PhotoEditor.vue'))

type PublicPhotoItem = PhotoItem & { wotu_url?: string | null }
type EditorPhotoItem = { id: number; url: string }
type PrintPhotoSlot = { id: string; x: number; y: number; width: number; height: number }

const route = useRoute()
const router = useRouter()
const token = computed(() => String(route.params.token))

const program = ref<Program | null>(null)
const photos = ref<PublicPhotoItem[]>([])
const loading = ref(false)
const photosLoading = ref(false)
const loadingMore = ref(false)
const notFound = ref(false)
const currentPage = ref(1)
const pageSize = 30
const totalPhotos = ref(0)

// 个人中心
const showPersonalCenter = ref(false)
const authorizedProfile = ref<WechatProfile | null>(null)

// 画布编辑器
const editingPhotos = ref<EditorPhotoItem[]>([])

// 编辑提示
const showEditTip = ref(true)
const photoSelectMode = ref(false)
const selectedPhotoIds = ref<Set<number>>(new Set())
let photoLongPressTimer: number | null = null
let photoLongPressTriggered = false

// 画布尺寸和照片初始配置（从打印模板获取）
const canvasWidth = ref(800)
const canvasHeight = ref(600)
const photoInitX = ref(50)
const photoInitY = ref(50)
const photoInitScale = ref(100)
const photoMargin = ref(20)
const templateName = ref('')
const paperSize = ref<string | null>(null)
const photoSlots = ref<PrintPhotoSlot[]>([])
const templateCanvasJson = ref<any>(null)

const hasMorePhotos = computed(() => photos.value.length < totalPhotos.value)

const currentPath = computed(() => window.location.pathname + window.location.search)

function getPhotoSource(photo: PublicPhotoItem | null): string {
  if (!photo) return ''
  return getPhotoUrl(photo.storage_url, photo.wotu_url)
}

function toEditorPhoto(photo: PublicPhotoItem): EditorPhotoItem {
  return {
    id: photo.id,
    url: getPhotoSource(photo),
  }
}

function openEditor(index: number) {
  const photo = photos.value[index]
  if (!photo) return
  editingPhotos.value = [toEditorPhoto(photo)]
}

function startPhotoLongPress(photoId: number) {
  clearPhotoLongPress()
  photoLongPressTriggered = false
  photoLongPressTimer = window.setTimeout(() => {
    photoLongPressTriggered = true
    enterPhotoSelectMode(photoId)
  }, 520)
}

function clearPhotoLongPress() {
  if (photoLongPressTimer) {
    window.clearTimeout(photoLongPressTimer)
    photoLongPressTimer = null
  }
}

function enterPhotoSelectMode(photoId: number) {
  photoSelectMode.value = true
  selectedPhotoIds.value = new Set([photoId])
}

function togglePhotoSelection(photoId: number) {
  const next = new Set(selectedPhotoIds.value)
  if (next.has(photoId)) {
    next.delete(photoId)
  } else {
    next.add(photoId)
  }
  selectedPhotoIds.value = next
  if (next.size === 0) {
    photoSelectMode.value = false
  }
}

function clearPhotoSelection() {
  selectedPhotoIds.value = new Set()
  photoSelectMode.value = false
}

function confirmPhotoSelection() {
  const selected = photos.value.filter(photo => selectedPhotoIds.value.has(photo.id)).map(toEditorPhoto)
  if (!selected.length) {
    message.info('请选择照片')
    return
  }
  editingPhotos.value = selected
  clearPhotoSelection()
}

function handlePhotoTap(photo: PublicPhotoItem, index: number) {
  if (photoLongPressTriggered) {
    photoLongPressTriggered = false
    return
  }
  if (photoSelectMode.value) {
    togglePhotoSelection(photo.id)
    return
  }
  openEditor(index)
}

async function openEditorFromCenter() {
  showPersonalCenter.value = false

  if (photos.value.length === 0) {
    currentPage.value = 1
    await fetchPhotos(1)
  }

  const firstPhoto = photos.value[0]
  if (!firstPhoto) {
    message.info('暂无可编辑照片')
    return
  }

  editingPhotos.value = [toEditorPhoto(firstPhoto)]
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

function onWechatAuthorized(profile: WechatProfile) {
  authorizedProfile.value = profile
}

async function fetchProgram() {
  loading.value = true
  notFound.value = false
  try {
    const res = await publicApi.getProgram(token.value)
    program.value = res.data
  } catch (e: any) {
    if (e.response?.status === 404) {
      notFound.value = true
    } else {
      message.error('加载失败')
    }
  } finally {
    loading.value = false
  }
}

async function fetchPhotos(page: number, append = false) {
  photosLoading.value = !append
  loadingMore.value = append
  try {
    const res = await publicApi.listPhotos(token.value, page, pageSize)
    const data = res.data as PublicPhotoItem[]
    if (append) {
      photos.value = [...photos.value, ...data]
    } else {
      photos.value = data
    }
    if (data.length < pageSize) {
      totalPhotos.value = photos.value.length
    } else {
      totalPhotos.value = photos.value.length + 1
    }
  } catch {
    if (!append) message.error('加载照片失败')
  } finally {
    photosLoading.value = false
    loadingMore.value = false
  }
}

function loadMorePhotos() {
  currentPage.value++
  fetchPhotos(currentPage.value, true)
}

onMounted(async () => {
  await fetchProgram()
  if (program.value) {
    fetchPhotos(1)
    await loadPrintTemplate()
  }
})

// 从活动打印模板加载画布配置
async function loadPrintTemplate() {
  if (!program.value?.activity_id) return
  try {
    const res = await publicApi2.getCanvasConfig(program.value.activity_id) as any
    const config = res?.data || res
    if (config.canvasWidth) canvasWidth.value = config.canvasWidth
    if (config.canvasHeight) canvasHeight.value = config.canvasHeight
    if (config.photoInitX !== undefined) photoInitX.value = config.photoInitX
    if (config.photoInitY !== undefined) photoInitY.value = config.photoInitY
    if (config.photoInitScale !== undefined) photoInitScale.value = config.photoInitScale
    if (config.photoMargin !== undefined) photoMargin.value = config.photoMargin
    templateName.value = config.templateName || ''
    paperSize.value = config.paperSize || null
    photoSlots.value = Array.isArray(config.photoSlots) ? config.photoSlots : []
    templateCanvasJson.value = config.canvasJson || null
  } catch {
    // 使用默认值
  }
}
</script>

<style scoped>
.public-page {
  min-height: 100vh;
  background: #f8f8f8;
}

.detail-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.nav-back, .nav-user {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  color: #333;
  display: flex;
}

.nav-back:hover, .nav-user:hover {
  background: #f5f5f5;
}

.nav-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  text-align: center;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 12px;
}

.video-section {
  background: #000;
}

.video-player {
  width: 100%;
  max-height: 300px;
  object-fit: contain;
  display: block;
}

.photo-section {
  padding: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.photo-count {
  font-size: 13px;
  font-weight: 400;
  color: #8c8c8c;
}

.edit-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: #fff3e0;
  color: #fa8c16;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.edit-hint:hover {
  background: #ffe0b2;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
}

.photo-item {
  position: relative;
  appearance: none;
  border: 0;
  border-radius: 0;
  background: #f3f3f3;
  padding: 0;
  overflow: hidden;
  cursor: pointer;
  aspect-ratio: 1;
  -webkit-touch-callout: none;
  user-select: none;
}

.photo-item.selecting img {
  transform: scale(1.02);
}

.photo-item.selected::after {
  position: absolute;
  inset: 0;
  border: 2px solid #1677ff;
  content: '';
  pointer-events: none;
}

.photo-select-dot {
  position: absolute;
  top: 7px;
  right: 7px;
  z-index: 2;
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.95);
  border-radius: 50%;
  background: rgba(17, 24, 39, 0.35);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.22);
}

.photo-select-dot.checked {
  background: #1677ff;
  border-color: #fff;
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.24s ease;
}

.photo-item:hover img {
  transform: scale(1.05);
}

.photo-edit-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  opacity: 0;
  transition: opacity 0.2s;
  backdrop-filter: blur(2px);
}

.photo-item:hover .photo-edit-overlay {
  opacity: 1;
}

.photo-item.selecting .photo-edit-overlay {
  opacity: 0;
}

.photo-select-bar {
  position: fixed;
  left: 12px;
  right: 12px;
  bottom: calc(14px + env(safe-area-inset-bottom, 0px));
  z-index: 30;
  height: 48px;
  padding: 0 14px;
  border-radius: 24px;
  background: rgba(17, 24, 39, 0.92);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.28);
}

.photo-select-bar button {
  border: 0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  padding: 6px 14px;
}

.photo-select-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.photo-select-actions .confirm {
  min-width: 64px;
  background: #1677ff;
  font-weight: 700;
}

.load-more {
  text-align: center;
  padding: 20px 0;
}

.loading-initial {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
}
</style>
