<template>
  <div class="public-page">
    <div class="detail-nav">
      <span class="nav-title">{{ program?.name || '节目详情' }}</span>
    </div>

    <a-spin :spinning="loading">
      <template v-if="program">
        <!-- Video Section -->
        <div class="video-section" v-if="program.video_url">
          <video
            :src="program.video_url"
            controls
            playsinline
            preload="metadata"
            class="video-player"
          ></video>
        </div>

        <!-- Photo Section -->
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
              <div
                v-for="photo in photos"
                :key="photo.id"
                class="photo-item"
                @click="previewIndex = photos.indexOf(photo)"
              >
                <img :src="getThumbUrl(photo.storage_url)" :alt="`照片 ${photo.id}`" loading="lazy" />
              </div>
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

    <!-- Photo Preview Modal -->
    <a-modal
      :open="previewIndex >= 0"
      :footer="null"
      :width="'100%'"
      :wrap-class-name="'photo-preview-modal'"
      @cancel="previewIndex = -1"
    >
      <div class="preview-container">
        <img
          v-if="previewIndex >= 0 && photos[previewIndex]"
          :src="getPreviewUrl(photos[previewIndex].storage_url)"
          class="preview-image"
        />
      </div>
      <div class="preview-nav">
        <a-button
          type="text"
          :disabled="previewIndex <= 0"
          @click="previewIndex--"
        >
          <LeftOutlined />
        </a-button>
        <span class="preview-counter">{{ previewIndex + 1 }} / {{ photos.length }}</span>
        <a-button
          type="text"
          :disabled="previewIndex >= photos.length - 1"
          @click="previewIndex++"
        >
          <RightOutlined />
        </a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { CameraOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { publicApi, type Program, type PhotoItem } from '@/api/admin'
import { getThumbUrl, getPreviewUrl } from '@/utils/image'

const route = useRoute()
const token = computed(() => String(route.params.token))
const program = ref<Program | null>(null)
const photos = ref<PhotoItem[]>([])
const loading = ref(false)
const photosLoading = ref(false)
const loadingMore = ref(false)
const notFound = ref(false)
const currentPage = ref(1)
const pageSize = 30
const totalPhotos = ref(0)
const previewIndex = ref(-1)

const hasMorePhotos = computed(() => photos.value.length < totalPhotos.value)

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
    const data = res.data
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

onMounted(async () => {
  await fetchProgram()
  if (program.value) {
    fetchPhotos(1)
  }
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

.photo-item img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  cursor: pointer;
  transition: opacity 0.2s;
}

.photo-item img:hover {
  opacity: 0.85;
}

.load-more {
  text-align: center;
  padding: 20px 0;
}
</style>

<style>
.photo-preview-modal .ant-modal-content {
  background: rgba(0, 0, 0, 0.95);
  max-height: 100vh;
  display: flex;
  flex-direction: column;
}

.photo-preview-modal .ant-modal-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  overflow: hidden;
}

.photo-preview-modal .ant-modal-close {
  color: #fff;
  font-size: 24px;
}

.preview-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 20px;
}

.preview-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border-radius: 4px;
}

.preview-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
}

.preview-nav .ant-btn {
  color: #fff !important;
  font-size: 20px;
}

.preview-counter {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}
</style>
