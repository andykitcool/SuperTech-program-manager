<template>
  <div>
    <div class="page-header">
      <a-button @click="$router.push('/admin/photo-manager')">
        <template #icon><ArrowLeftOutlined /></template>
        返回
      </a-button>
      <h2>{{ activity.name }} - 照片浏览</h2>
      <a-space>
        <span style="color: #8c8c8c; font-size: 13px">共 {{ total }} 张照片</span>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && photos.length === 0" description="暂无照片" />
      <div class="photo-grid" v-else>
        <div
          v-for="photo in photos"
          :key="photo.id"
          class="photo-item"
          @click="handlePreview(photo)"
        >
          <div class="photo-thumb">
            <img :src="getThumbUrl(photo.storage_url || photo.wotu_url) || fallbackImage" @error="($event.target as HTMLImageElement).src = fallbackImage" />
          </div>
          <div class="photo-info">
            <span class="photo-name" :title="photo.filename">{{ photo.filename }}</span>
            <span class="photo-time" v-if="photo.shoot_time">{{ formatShootTime(photo.shoot_time) }}</span>
          </div>
        </div>
      </div>

      <div class="pagination-wrapper" v-if="total > pageSize">
        <a-pagination
          v-model:current="currentPage"
          :total="total"
          :page-size="pageSize"
          :show-size-changer="false"
          @change="onPageChange"
        />
      </div>
    </a-spin>

    <a-modal
      v-model:open="previewVisible"
      :footer="null"
      :width="800"
      centered
      @cancel="previewVisible = false"
    >
      <img
        v-if="previewPhoto"
        :src="getPreviewUrl(previewPhoto.storage_url ?? previewPhoto.wotu_url ?? '')"
        style="width: 100%"
      />
      <div class="preview-info" v-if="previewPhoto">
        <p><strong>文件名：</strong>{{ previewPhoto.filename }}</p>
        <p v-if="previewPhoto.shoot_time"><strong>拍摄时间：</strong>{{ formatShootTime(previewPhoto.shoot_time) }}</p>
        <p v-if="previewPhoto.width && previewPhoto.height"><strong>尺寸：</strong>{{ previewPhoto.width }} x {{ previewPhoto.height }}</p>
        <p v-if="previewPhoto.file_size"><strong>大小：</strong>{{ formatSize(previewPhoto.file_size) }}</p>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeftOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { photoApi, type PhotoItemFull } from '@/api/admin'
import { getThumbUrl, getPreviewUrl } from '@/utils/image'

const route = useRoute()
const activityId = computed(() => Number(route.params.id))
const activity = ref({ id: 0, name: '', event_date: '' as string | null })
const photos = ref<PhotoItemFull[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(30)
const previewVisible = ref(false)
const previewPhoto = ref<PhotoItemFull | null>(null)

const fallbackImage = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 150"><rect fill="%23f0f0f0" width="200" height="150"/><text x="100" y="80" text-anchor="middle" fill="%23bfbfbf" font-size="14">加载失败</text></svg>'

function formatShootTime(time: string) {
  return time.replace('T', ' ').substring(0, 19)
}

function formatSize(bytes: number) {
  if (!bytes || bytes <= 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 3)
  return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + ' ' + units[i]
}

function handlePreview(photo: PhotoItemFull) {
  previewPhoto.value = photo
  previewVisible.value = true
}

async function fetchPhotos() {
  loading.value = true
  try {
    const res = await photoApi.getActivityPhotos(activityId.value, currentPage.value, pageSize.value)
    activity.value = res.data.activity
    photos.value = res.data.photos
    total.value = res.data.total
  } catch {
    message.error('加载照片失败')
  } finally {
    loading.value = false
  }
}

function onPageChange(page: number) {
  currentPage.value = page
  fetchPhotos()
}

onMounted(fetchPhotos)
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

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}

.photo-item {
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
  cursor: pointer;
  transition: box-shadow 0.3s, transform 0.2s;
  border: 1px solid #f0f0f0;
}

.photo-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.photo-thumb {
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
}

.photo-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: #f5f5f5;
}

.photo-info {
  padding: 6px 8px;
}

.photo-name {
  display: block;
  font-size: 12px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.photo-time {
  display: block;
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

.preview-info {
  padding: 12px 0;
}

.preview-info p {
  margin: 4px 0;
  font-size: 13px;
  color: #666;
}
</style>
