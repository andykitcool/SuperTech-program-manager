<template>
  <div class="public-page">
    <div class="detail-nav">
      <span class="nav-title">{{ program?.name || '节目详情' }}</span>
    </div>

    <a-spin :spinning="loading">
      <template v-if="program">
        <div class="video-section" v-if="program.video_url">
          <video
            :src="program.video_url"
            controls
            playsinline
            preload="metadata"
            class="video-player"
          ></video>
        </div>

        <div class="photo-section">
          <div class="section-header">
            <h3>
              <CameraOutlined />
              精彩照片
              <span class="photo-count" v-if="photos.length > 0">（{{ totalPhotos }}张）</span>
            </h3>
          </div>

          <a-skeleton :loading="photosLoading" active :paragraph="{ rows: 6 }">
            <div v-if="photos.length > 0" class="photo-grid">
              <button
                v-for="(photo, index) in photos"
                :key="photo.id"
                type="button"
                class="photo-item"
                @click="openPreview(index)"
              >
                <img :src="getThumbUrl(getPhotoSource(photo))" :alt="`照片 ${index + 1}`" loading="lazy" />
              </button>
            </div>
            <a-empty v-else description="暂无照片" style="padding: 40px 0" />
          </a-skeleton>

          <div class="load-more" v-if="hasMorePhotos">
            <a-button @click="loadMorePhotos" :loading="loadingMore">
              加载更多
            </a-button>
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

    <Teleport to="body">
      <Transition name="viewer-fade">
        <div
          v-if="previewIndex >= 0 && currentPhoto"
          class="photo-viewer"
          @click.self="closePreview"
          @touchstart.passive="handleTouchStart"
          @touchend.passive="handleTouchEnd"
        >
          <div class="viewer-topbar">
            <button class="viewer-icon-button" type="button" aria-label="关闭" @click="closePreview">
              <CloseOutlined />
            </button>
            <div class="viewer-counter">{{ previewIndex + 1 }} / {{ photos.length }}</div>
            <div class="viewer-actions">
              <button
                class="viewer-icon-button"
                type="button"
                aria-label="打印"
                :disabled="!currentPhoto || printingPhoto"
                @click="printCurrentPhoto"
              >
                <PrinterOutlined />
              </button>
              <button
                class="viewer-icon-button"
                type="button"
                aria-label="下载"
                :disabled="!currentOriginalUrl"
                @click="downloadPhoto"
              >
                <DownloadOutlined />
              </button>
            </div>
          </div>

          <button
            class="viewer-nav-button viewer-nav-prev"
            type="button"
            aria-label="上一张"
            :disabled="previewIndex <= 0"
            @click.stop="showPrevPhoto"
          >
            <LeftOutlined />
          </button>
          <button
            class="viewer-nav-button viewer-nav-next"
            type="button"
            aria-label="下一张"
            :disabled="previewIndex >= photos.length - 1"
            @click.stop="showNextPhoto"
          >
            <RightOutlined />
          </button>

          <div class="viewer-stage">
            <img
              :key="currentPhoto.id"
              :src="currentPreviewUrl"
              class="viewer-image"
              :alt="`照片 ${previewIndex + 1}`"
              draggable="false"
            />
          </div>

          <div class="viewer-footer">
            <div class="viewer-meta">
              <strong>{{ program?.name }}</strong>
              <span v-if="currentPhoto.shoot_time">{{ formatShootTime(currentPhoto.shoot_time) }}</span>
            </div>
            <div class="viewer-thumb-strip">
              <button
                v-for="(photo, index) in photos"
                :key="photo.id"
                type="button"
                class="viewer-thumb"
                :class="{ active: index === previewIndex }"
                @click="previewIndex = index"
              >
                <img :src="getThumbUrl(getPhotoSource(photo))" :alt="`缩略图 ${index + 1}`" loading="lazy" />
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  CameraOutlined,
  CloseOutlined,
  DownloadOutlined,
  LeftOutlined,
  PrinterOutlined,
  RightOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { publicApi, type Program, type PhotoItem, type WechatProfile } from '@/api/admin'
import { getPhotoUrl, getPreviewUrl, getThumbUrl } from '@/utils/image'
import { ensureWechatProfile } from '@/utils/wechat'

type PublicPhotoItem = PhotoItem & {
  wotu_url?: string | null
}

const route = useRoute()
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
const previewIndex = ref(-1)
const touchStartX = ref(0)
const printingPhoto = ref(false)
const wechatProfile = ref<WechatProfile | null>(null)

const hasMorePhotos = computed(() => photos.value.length < totalPhotos.value)
const currentPhoto = computed(() => photos.value[previewIndex.value] || null)
const currentOriginalUrl = computed(() => getPhotoSource(currentPhoto.value))
const currentPreviewUrl = computed(() => getPreviewUrl(currentOriginalUrl.value))

function getPhotoSource(photo: PublicPhotoItem | null): string {
  if (!photo) return ''
  return getPhotoUrl(photo.storage_url, photo.wotu_url)
}

function openPreview(index: number) {
  previewIndex.value = index
}

function closePreview() {
  previewIndex.value = -1
}

function showPrevPhoto() {
  if (previewIndex.value > 0) {
    previewIndex.value--
  }
}

function showNextPhoto() {
  if (previewIndex.value < photos.value.length - 1) {
    previewIndex.value++
  }
}

function downloadPhoto() {
  if (!currentOriginalUrl.value) return
  const link = document.createElement('a')
  link.href = currentOriginalUrl.value
  link.download = `${program.value?.name || 'photo'}-${previewIndex.value + 1}.jpg`
  link.target = '_blank'
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

async function printCurrentPhoto() {
  if (!currentPhoto.value || printingPhoto.value) return
  printingPhoto.value = true
  try {
    await publicApi.printPhoto(token.value, currentPhoto.value.id, 1, wechatProfile.value)
    message.success('已提交打印任务')
  } catch {
    message.error('提交打印失败')
  } finally {
    printingPhoto.value = false
  }
}

function handleTouchStart(event: TouchEvent) {
  touchStartX.value = event.changedTouches[0]?.clientX || 0
}

function handleTouchEnd(event: TouchEvent) {
  const endX = event.changedTouches[0]?.clientX || 0
  const distance = endX - touchStartX.value
  if (Math.abs(distance) < 48) return
  if (distance > 0) {
    showPrevPhoto()
  } else {
    showNextPhoto()
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (previewIndex.value < 0) return
  if (event.key === 'Escape') closePreview()
  if (event.key === 'ArrowLeft') showPrevPhoto()
  if (event.key === 'ArrowRight') showNextPhoto()
}

function formatShootTime(value: string): string {
  const date = new Date(value.replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const fetchProgram = async () => {
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

const fetchPhotos = async (page: number, append = false) => {
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

const loadMorePhotos = () => {
  currentPage.value++
  fetchPhotos(currentPage.value, true)
}

watch(previewIndex, index => {
  document.body.style.overflow = index >= 0 ? 'hidden' : ''
})

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  await fetchProgram()
  if (program.value) {
    wechatProfile.value = await ensureWechatProfile(program.value.activity_id)
    fetchPhotos(1)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.detail-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 10;
}

.nav-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
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

.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
}

.photo-item {
  appearance: none;
  border: 0;
  border-radius: 0;
  background: #f3f3f3;
  padding: 0;
  overflow: hidden;
  cursor: pointer;
  aspect-ratio: 1;
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.24s ease, opacity 0.2s ease;
}

.photo-item:hover img {
  opacity: 0.9;
  transform: scale(1.025);
}

.load-more {
  text-align: center;
  padding: 20px 0;
}
</style>

<style>
.photo-viewer {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  background:
    radial-gradient(circle at 50% 24%, rgba(80, 88, 105, 0.24), transparent 34%),
    #050505;
  color: #fff;
  overflow: hidden;
  touch-action: pan-y;
}

.viewer-topbar,
.viewer-footer {
  position: relative;
  z-index: 3;
}

.viewer-topbar {
  display: grid;
  grid-template-columns: 52px 1fr auto;
  align-items: center;
  padding: max(12px, env(safe-area-inset-top)) 12px 10px;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.78), rgba(0, 0, 0, 0));
}

.viewer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.viewer-counter {
  justify-self: center;
  min-width: 70px;
  border-radius: 999px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.88);
  font-size: 13px;
  line-height: 1;
  text-align: center;
  backdrop-filter: blur(14px);
}

.viewer-icon-button,
.viewer-nav-button {
  appearance: none;
  border: 0;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.viewer-icon-button {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  font-size: 19px;
  backdrop-filter: blur(14px);
}

.viewer-icon-button:disabled,
.viewer-nav-button:disabled {
  cursor: default;
  opacity: 0.28;
}

.viewer-stage {
  position: relative;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 18px;
}

.viewer-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 2px;
  box-shadow: 0 18px 70px rgba(0, 0, 0, 0.55);
  user-select: none;
}

.viewer-nav-button {
  position: absolute;
  z-index: 4;
  top: 50%;
  width: 48px;
  height: 74px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.11);
  font-size: 24px;
  transform: translateY(-50%);
  backdrop-filter: blur(14px);
}

.viewer-nav-prev {
  left: 14px;
}

.viewer-nav-next {
  right: 14px;
}

.viewer-footer {
  padding: 8px 14px max(14px, env(safe-area-inset-bottom));
  background: linear-gradient(0deg, rgba(0, 0, 0, 0.86), rgba(0, 0, 0, 0));
}

.viewer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
}

.viewer-meta strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.viewer-meta span {
  flex: none;
  color: rgba(255, 255, 255, 0.62);
}

.viewer-thumb-strip {
  display: flex;
  gap: 7px;
  overflow-x: auto;
  padding: 2px 0;
  scrollbar-width: none;
}

.viewer-thumb-strip::-webkit-scrollbar {
  display: none;
}

.viewer-thumb {
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  border: 2px solid transparent;
  border-radius: 4px;
  padding: 0;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
  opacity: 0.58;
  cursor: pointer;
}

.viewer-thumb.active {
  border-color: #fff;
  opacity: 1;
}

.viewer-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.viewer-fade-enter-active,
.viewer-fade-leave-active {
  transition: opacity 0.2s ease;
}

.viewer-fade-enter-from,
.viewer-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .viewer-stage {
    padding: 0;
  }

  .viewer-image {
    width: 100%;
    max-height: 100%;
    border-radius: 0;
    box-shadow: none;
  }

  .viewer-nav-button {
    display: none;
  }

  .viewer-footer {
    padding-left: 10px;
    padding-right: 10px;
  }

  .viewer-thumb {
    flex-basis: 42px;
    width: 42px;
    height: 42px;
  }
}
</style>
