<template>
  <div class="decoration-manager">
    <div class="page-header">
      <h2>素材管理</h2>
      <a-button type="primary" @click="openUploadModal">
        <UploadOutlined /> 上传素材
      </a-button>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <a-radio-group v-model:value="currentTab" button-style="solid">
        <a-radio-button value="background">背景</a-radio-button>
        <a-radio-button value="frame">相框</a-radio-button>
        <a-radio-button value="sticker">装饰贴纸</a-radio-button>
      </a-radio-group>
    </div>

    <div v-if="currentTab === 'sticker'" class="category-bar">
      <a-segmented
        v-model:value="currentCategory"
        :options="stickerCategoryFilterOptions"
        size="small"
      />
    </div>

    <!-- 素材列表 -->
    <a-spin :spinning="loading">
      <div class="material-grid">
        <div v-for="item in items" :key="item.id" class="material-card">
          <div class="card-img">
            <img :src="item.thumbnail_url || item.storage_url" :alt="item.name" />
          </div>
          <div class="card-info">
            <div class="card-title-row">
              <p class="card-name">{{ item.name }}</p>
              <div class="inline-actions">
                <a-switch
                  v-model:checked="item.is_active"
                  size="small"
                  @change="toggleActive(item)"
                />
                <a-button type="text" size="small" danger @click="deleteItem(item)">
                  <DeleteOutlined />
                </a-button>
              </div>
            </div>
            <p class="card-category">{{ item.category || '未分类' }}</p>
          </div>
        </div>

        <div v-if="items.length === 0 && !loading" class="empty-tip">
          <PictureOutlined :style="{ fontSize: '48px', color: '#ccc' }" />
          <p>暂无{{ tabLabel }}素材</p>
          <a-button type="link" @click="openUploadModal">立即上传</a-button>
        </div>
      </div>
    </a-spin>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="pagination">
      <a-pagination
        v-model:current="page"
        :total="total"
        :page-size="pageSize"
        show-quick-jumper
        @change="loadData"
      />
    </div>

    <!-- 批量上传弹窗 -->
    <a-modal
      v-model:open="showUpload"
      title="上传素材"
      :confirm-loading="uploading"
      ok-text="开始上传"
      :ok-button-props="{ disabled: fileList.length === 0 }"
      @ok="handleBatchUpload"
    >
      <a-form :model="uploadForm" layout="vertical">
        <a-form-item label="素材类型" required>
          <a-select v-model:value="uploadForm.type" placeholder="选择素材类型">
            <a-select-option value="background">背景</a-select-option>
            <a-select-option value="frame">相框</a-select-option>
            <a-select-option value="sticker">装饰贴纸</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="上传项名称" required>
          <a-select v-model:value="uploadForm.category" placeholder="选择上传项名称">
            <a-select-option
              v-for="option in uploadCategoryOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="选择图片文件（支持多选）" required>
          <a-upload
            v-model:file-list="fileList"
            list-type="picture"
            :before-upload="beforeUpload"
            multiple
            accept="image/*,.svg"
            @remove="onFileRemove"
          >
            <a-button>
              <UploadOutlined /> 选择文件（可多选）
            </a-button>
          </a-upload>
          <p class="upload-tip">支持 JPG、PNG、WebP、GIF、SVG，可一次选择多个文件批量上传。建议尺寸：背景2000×2000px，相框1000×1000px，装饰500×500px</p>
        </a-form-item>
      </a-form>

      <!-- 上传进度 -->
      <div v-if="batchProgress.total > 0" class="batch-progress">
        <a-progress :percent="Math.round(batchProgress.done / batchProgress.total * 100)" :size="'small'" />
        <p class="batch-status">已上传 {{ batchProgress.done }} / {{ batchProgress.total }}，成功 {{ batchProgress.success }}，失败 {{ batchProgress.failed }}</p>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  UploadOutlined, DeleteOutlined, PictureOutlined
} from '@ant-design/icons-vue'
import { adminApi, materialApi } from '@/api/admin'

const currentTab = ref('background')
const currentCategory = ref('all')
const page = ref(1)
const pageSize = 24
const total = ref(0)
const loading = ref(false)
const items = ref<any[]>([])

const showUpload = ref(false)
const uploading = ref(false)
const fileList = ref<any[]>([])

const uploadForm = ref({
  type: 'background',
  category: '背景素材',
})

const batchProgress = ref({
  total: 0,
  done: 0,
  success: 0,
  failed: 0,
})

const tabLabel = computed(() => {
  const map: Record<string, string> = { background: '背景', frame: '相框', sticker: '装饰贴纸' }
  return map[currentTab.value] || ''
})

const stickerCategories = [
  '表情',
  '动画',
  '氛围',
  '搞怪',
  '花草',
  '科技',
  '食物',
  '贴纸',
  '小马',
  '心情',
  '印章',
  'SVG',
]

const stickerCategoryFilterOptions = computed(() => [
  { label: '全部', value: 'all' },
  ...stickerCategories.map(item => ({ label: item, value: item })),
])

const uploadCategoryOptions = computed(() => {
  if (uploadForm.value.type === 'background') {
    return [{ label: '背景素材', value: '背景素材' }]
  }
  if (uploadForm.value.type === 'frame') {
    return [{ label: '相框素材', value: '相框素材' }]
  }
  return stickerCategories.map(item => ({ label: item, value: item }))
})

const activeCategoryFilter = computed(() => (
  currentTab.value === 'sticker' && currentCategory.value !== 'all'
    ? currentCategory.value
    : undefined
))

function getDefaultUploadCategory(type: string) {
  if (type === 'background') return '背景素材'
  if (type === 'frame') return '相框素材'
  if (currentCategory.value !== 'all') return currentCategory.value
  return stickerCategories[0]
}

async function loadData() {
  loading.value = true
  try {
    const res = await materialApi.listDecorationMaterials(
      currentTab.value,
      undefined,
      page.value,
      pageSize,
      activeCategoryFilter.value,
    ) as any
    items.value = res?.data?.items || []
    total.value = res?.data?.total || 0
  } catch (e: any) {
    message.error('加载素材失败: ' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

function openUploadModal() {
  uploadForm.value.type = currentTab.value
  uploadForm.value.category = getDefaultUploadCategory(currentTab.value)
  fileList.value = []
  batchProgress.value = { total: 0, done: 0, success: 0, failed: 0 }
  showUpload.value = true
}

function beforeUpload(file: File) {
  return false // 阻止自动上传
}

function onFileRemove(file: any) {
  const index = fileList.value.indexOf(file)
  if (index > -1) fileList.value.splice(index, 1)
}

async function handleBatchUpload() {
  if (fileList.value.length === 0) {
    message.warning('请先选择图片文件')
    return
  }

  uploading.value = true
  const files = fileList.value.map(f => f.originFileObj || f).filter((f): f is File => f instanceof File)
  batchProgress.value = { total: files.length, done: 0, success: 0, failed: 0 }

  for (const file of files) {
    try {
      // 先上传文件获取URL
      const uploadRes = await materialApi.uploadDecorationMaterial(file) as any
      const storageUrl = uploadRes?.data?.url || uploadRes?.data?.storage_url || ''

      if (!storageUrl) {
        batchProgress.value.done++
        batchProgress.value.failed++
        continue
      }

      // 自动生成名称（去掉扩展名）
      const autoName = file.name.replace(/\.[^.]+$/, '')

      // 创建素材记录
      await materialApi.createDecorationMaterial({
        type: uploadForm.value.type,
        name: autoName,
        storage_url: storageUrl,
        thumbnail_url: storageUrl,
        category: uploadForm.value.category,
        sort_order: 0,
        is_active: true,
      }) as any

      batchProgress.value.success++
    } catch (e: any) {
      batchProgress.value.failed++
      console.error(`上传 ${file.name} 失败:`, e)
    } finally {
      batchProgress.value.done++
    }
  }

  uploading.value = false

  if (batchProgress.value.failed === 0) {
    message.success(`全部 ${batchProgress.value.success} 个素材上传成功`)
    showUpload.value = false
  } else {
    message.warning(`上传完成：成功 ${batchProgress.value.success} 个，失败 ${batchProgress.value.failed} 个`)
  }

  fileList.value = []
  batchProgress.value = { total: 0, done: 0, success: 0, failed: 0 }
  loadData()
}

async function toggleActive(item: any) {
  try {
    await materialApi.updateDecorationMaterial(item.id, { is_active: item.is_active }) as any
    message.success(item.is_active ? '已启用' : '已禁用')
  } catch {
    item.is_active = !item.is_active
    message.error('操作失败')
  }
}

async function deleteItem(item: any) {
  try {
    await materialApi.deleteDecorationMaterial(item.id) as any
    items.value = items.value.filter(i => i.id !== item.id)
    message.success('删除成功')
  } catch {
    message.error('删除失败')
  }
}

watch(currentTab, () => {
  currentCategory.value = 'all'
  page.value = 1
  loadData()
})

watch(currentCategory, () => {
  page.value = 1
  loadData()
})

watch(() => uploadForm.value.type, (type) => {
  uploadForm.value.category = getDefaultUploadCategory(type)
})

loadData()
</script>

<style scoped>
.decoration-manager { padding: 24px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 18px; }
.tab-bar { margin-bottom: 20px; }
.category-bar {
  margin: -8px 0 18px;
  overflow-x: auto;
  padding-bottom: 2px;
}
.category-bar :deep(.ant-segmented) {
  white-space: nowrap;
}
.material-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}
.material-card {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.material-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.card-img {
  height: 140px;
  overflow: hidden;
  background:
    linear-gradient(45deg, #f2f4f7 25%, transparent 25%),
    linear-gradient(-45deg, #f2f4f7 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #f2f4f7 75%),
    linear-gradient(-45deg, transparent 75%, #f2f4f7 75%),
    #ffffff;
  background-position: 0 0, 0 8px, 8px -8px, -8px 0;
  background-size: 16px 16px;
}
.card-img img { width: 100%; height: 100%; object-fit: contain; padding: 8px; }
.card-info { padding: 8px 12px 10px; }
.card-title-row { display: flex; align-items: center; gap: 8px; min-height: 28px; }
.card-name { flex: 1; min-width: 0; margin: 0; font-size: 13px; font-weight: 500; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.inline-actions { flex-shrink: 0; display: flex; align-items: center; gap: 6px; }
.card-category { margin: 2px 0 0; font-size: 11px; color: #999; }
.empty-tip { text-align: center; padding: 60px 20px; color: #999; }
.pagination { margin-top: 24px; text-align: right; }
.upload-tip { font-size: 12px; color: #999; margin-top: 4px; }
.batch-progress { margin-top: 12px; }
.batch-status { font-size: 12px; color: #666; margin-top: 4px; }
</style>
