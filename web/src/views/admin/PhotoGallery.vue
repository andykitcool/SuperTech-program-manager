<template>
  <div>
    <div class="page-header">
      <div class="page-header-left">
        <a-button @click="$router.push('/admin/photo-manager')">
          <template #icon><ArrowLeftOutlined /></template>
          返回
        </a-button>
        <a-button danger :disabled="selectedIds.size === 0" :loading="deleting" @click="handleDeleteSelected">
          <template #icon><DeleteOutlined /></template>
          删除{{ selectedIds.size > 0 ? ` (${selectedIds.size})` : '' }}
        </a-button>
        <a-button danger type="primary" :disabled="total === 0" :loading="deletingAll" @click="handleDeleteAll">
          <template #icon><DeleteFilled /></template>
          全部删除
        </a-button>
      </div>
      <h2>{{ activity.name }} - 照片浏览</h2>
      <a-space>
        <span class="photo-total">共 {{ total }} 张照片</span>
      </a-space>
    </div>

    <div v-if="categories.length > 0" class="category-filter">
      <a-radio-group v-model:value="categoryId" button-style="solid" @change="handleCategoryChange">
        <a-radio-button value="">全部 {{ categoryTotal }}</a-radio-button>
        <a-radio-button
          v-for="category in categories"
          :key="category.category_id || category.category_name"
          :value="category.category_id"
          :disabled="!category.category_id"
        >
          {{ category.category_name || '未分类' }} {{ category.count }}
        </a-radio-button>
      </a-radio-group>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && photos.length === 0" description="暂无照片" />
      <div class="photo-grid" v-else>
        <div
          v-for="photo in photos"
          :key="photo.id"
          class="photo-item"
          :class="{ 'photo-item-selected': selectedIds.has(photo.id) }"
          @click="handlePhotoClick(photo, $event)"
        >
          <div class="photo-checkbox" @click.stop>
            <a-checkbox
              :checked="selectedIds.has(photo.id)"
              @change="(e: any) => toggleSelect(photo.id, e.target.checked)"
            />
          </div>
          <div class="photo-thumb">
            <img
              :src="getThumbUrl(photo.storage_url || photo.wotu_url) || fallbackImage"
              @error="($event.target as HTMLImageElement).src = fallbackImage"
            />
          </div>
          <div class="photo-info">
            <span class="photo-name" :title="photo.filename">{{ photo.filename }}</span>
            <a-tag v-if="photo.wotu_category_name" class="photo-category">{{ photo.wotu_category_name }}</a-tag>
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
        <p v-if="previewPhoto.wotu_category_name"><strong>分类：</strong>{{ previewPhoto.wotu_category_name }}</p>
        <p v-if="previewPhoto.shoot_time"><strong>拍摄时间：</strong>{{ formatShootTime(previewPhoto.shoot_time) }}</p>
        <p v-if="previewPhoto.width && previewPhoto.height"><strong>尺寸：</strong>{{ previewPhoto.width }} x {{ previewPhoto.height }}</p>
        <p v-if="previewPhoto.file_size"><strong>大小：</strong>{{ formatSize(previewPhoto.file_size) }}</p>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeftOutlined, DeleteFilled, DeleteOutlined } from '@ant-design/icons-vue'
import { message, Modal } from 'ant-design-vue'
import { photoApi, type PhotoCategoryInfo, type PhotoItemFull } from '@/api/admin'
import { getPreviewUrl, getThumbUrl } from '@/utils/image'

const route = useRoute()
const activityId = computed(() => Number(route.params.id))
const activity = ref({ id: 0, name: '', event_date: '' as string | null })
const photos = ref<PhotoItemFull[]>([])
const categories = ref<PhotoCategoryInfo[]>([])
const categoryId = ref('')
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(30)
const previewVisible = ref(false)
const previewPhoto = ref<PhotoItemFull | null>(null)

const selectedIds = ref<Set<number>>(new Set())
const deleting = ref(false)
const deletingAll = ref(false)

const categoryTotal = computed(() => categories.value.reduce((sum, item) => sum + item.count, 0))
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

function toggleSelect(photoId: number, checked: boolean) {
  const next = new Set(selectedIds.value)
  if (checked) {
    next.add(photoId)
  } else {
    next.delete(photoId)
  }
  selectedIds.value = next
}

function handlePhotoClick(photo: PhotoItemFull, event: MouseEvent) {
  if (event.ctrlKey || event.metaKey) {
    toggleSelect(photo.id, !selectedIds.value.has(photo.id))
  } else {
    previewPhoto.value = photo
    previewVisible.value = true
  }
}

async function handleDeleteSelected() {
  const ids = Array.from(selectedIds.value)
  if (ids.length === 0) return

  Modal.confirm({
    title: '确认删除',
    content: `确定要删除选中的 ${ids.length} 张照片吗？此操作不可恢复。`,
    okText: '确认删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      deleting.value = true
      try {
        await photoApi.batchDeletePhotos(ids)
        message.success(`已删除 ${ids.length} 张照片`)
        selectedIds.value = new Set()
        await fetchPhotos()
      } catch {
        message.error('删除照片失败')
      } finally {
        deleting.value = false
      }
    },
  })
}

function handleDeleteAll() {
  Modal.confirm({
    title: '确认全部删除',
    content: `确定要删除该活动下的全部 ${total.value} 张照片吗？此操作不可恢复。`,
    okText: '全部删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      deletingAll.value = true
      try {
        const res = await photoApi.deleteAllActivityPhotos(activityId.value)
        message.success(`已删除 ${res.data.count} 张照片`)
        selectedIds.value = new Set()
        categoryId.value = ''
        await fetchPhotos()
      } catch {
        message.error('删除照片失败')
      } finally {
        deletingAll.value = false
      }
    },
  })
}

async function fetchPhotos() {
  loading.value = true
  try {
    const res = await photoApi.getActivityPhotos(
      activityId.value,
      currentPage.value,
      pageSize.value,
      categoryId.value || undefined,
    )
    activity.value = res.data.activity
    photos.value = res.data.photos
    categories.value = res.data.categories || []
    total.value = res.data.total
  } catch {
    message.error('加载照片失败')
  } finally {
    loading.value = false
  }
}

function handleCategoryChange() {
  currentPage.value = 1
  selectedIds.value = new Set()
  fetchPhotos()
}

function onPageChange(page: number) {
  currentPage.value = page
  selectedIds.value = new Set()
  fetchPhotos()
}

onMounted(fetchPhotos)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  gap: 12px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.page-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.photo-total {
  color: #8c8c8c;
  font-size: 13px;
}

.category-filter {
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fafbfc;
  overflow-x: auto;
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
  position: relative;
}

.photo-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.photo-item-selected {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.photo-checkbox {
  position: absolute;
  top: 4px;
  right: 4px;
  z-index: 2;
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

.photo-category {
  margin: 5px 0 0;
  max-width: 100%;
}

.photo-time {
  display: block;
  font-size: 11px;
  color: #999;
  margin-top: 4px;
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
