<template>
  <transition name="slide-up">
    <div v-if="visible" class="material-panel">
      <div class="panel-header">
        <div v-if="materialType !== 'sticker'" class="panel-title">
          {{ panelTitle }}
        </div>
        <div v-else class="panel-tabs">
          <button
            v-for="tab in stickerTabs"
            :key="tab.value"
            :class="['tab-btn', { active: currentCategory === tab.value }]"
            @click="switchCategory(tab.value)"
          >
            {{ tab.label }}
          </button>
        </div>
        <button class="close-btn" @click="$emit('close')">
          <X :size="20" />
        </button>
      </div>

      <div ref="scrollRef" class="panel-body" @scroll="onScroll">
        <div v-if="loading" class="loading-mask">
          <a-spin size="small" />
        </div>
        <div v-else-if="items.length === 0" class="empty-tip">
          <ImageOff :size="32" />
          <p>暂无素材</p>
        </div>
        <div v-else class="material-grid">
          <button
            v-for="item in items"
            :key="item.id"
            type="button"
            class="material-item"
            @click="selectMaterial(item)"
          >
            <img
              :src="item.thumbnail_url || item.storage_url"
              :alt="item.name"
              loading="lazy"
            />
            <span class="item-name">{{ item.name }}</span>
          </button>
        </div>

        <div v-if="hasMore && !loading" ref="loadMoreRef" class="load-more-tip">
          <a-spin v-if="loadingMore" size="small" />
          <span v-else>上拉加载更多</span>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { X, ImageOff } from 'lucide-vue-next'
import { publicApi2 } from '@/api/admin'

export interface MaterialItem {
  id: number
  type: string
  name: string
  storage_url: string
  thumbnail_url?: string
  category?: string
}

const props = defineProps<{
  visible: boolean
  materialType: 'background' | 'frame' | 'sticker'
}>()

const emit = defineEmits<{
  select: [item: MaterialItem]
  close: []
}>()

const stickerTabs = [
  { label: '表情', value: '表情' },
  { label: '动画', value: '动画' },
  { label: '氛围', value: '氛围' },
  { label: '搞怪', value: '搞怪' },
  { label: '花草', value: '花草' },
  { label: '科技', value: '科技' },
  { label: '食物', value: '食物' },
  { label: '贴纸', value: '贴纸' },
  { label: '小马', value: '小马' },
  { label: '心情', value: '心情' },
  { label: '印章', value: '印章' },
  { label: 'SVG', value: 'SVG' },
]

const currentCategory = ref(stickerTabs[0].value)
const items = ref<MaterialItem[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const page = ref(1)
const pageSize = 10
const hasMore = ref(true)
const scrollRef = ref<HTMLElement | null>(null)
const panelTitle = computed(() => props.materialType === 'background' ? '背景素材' : '相框素材')

function switchCategory(category: string) {
  currentCategory.value = category
  page.value = 1
  hasMore.value = true
  items.value = []
  loadMaterials()
}

async function loadMaterials(append = false) {
  if (!append) loading.value = true
  else loadingMore.value = true

  try {
    const category = props.materialType === 'sticker' ? currentCategory.value : undefined
    const res = await publicApi2.listMaterials(props.materialType, page.value, pageSize, category) as any
    const newItems = res?.data?.items || []
    if (append) {
      items.value.push(...newItems)
    } else {
      items.value = newItems
    }
    hasMore.value = newItems.length === pageSize
  } catch (e) {
    console.error('加载素材失败', e)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

function onScroll() {
  if (!scrollRef.value || !hasMore.value || loadingMore.value) return
  const { scrollTop, scrollHeight, clientHeight } = scrollRef.value
  if (scrollTop + clientHeight >= scrollHeight - 60) {
    page.value++
    loadMaterials(true)
  }
}

function selectMaterial(item: MaterialItem) {
  emit('select', item)
}

watch(() => props.visible, (visible) => {
  if (visible) {
    page.value = 1
    items.value = []
    currentCategory.value = stickerTabs[0].value
    loadMaterials()
  }
})

watch(() => props.materialType, () => {
  if (!props.visible) return
  page.value = 1
  hasMore.value = true
  items.value = []
  currentCategory.value = stickerTabs[0].value
  loadMaterials()
})

onMounted(() => {
  if (props.visible) loadMaterials()
})
</script>

<style scoped>
.material-panel {
  position: fixed;
  bottom: 56px;
  left: 0;
  right: 0;
  height: 260px;
  background: #fff;
  border-radius: 16px 16px 0 0;
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.12);
  z-index: 90;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  padding: 12px 16px 8px;
  border-bottom: 1px solid #f0f0f0;
  gap: 8px;
}

.panel-tabs {
  display: flex;
  gap: 4px;
  flex: 1;
  overflow-x: auto;
  padding-bottom: 2px;
  scrollbar-width: none;
}

.panel-tabs::-webkit-scrollbar {
  display: none;
}

.panel-title {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.tab-btn {
  flex: 0 0 auto;
  padding: 6px 14px;
  border: none;
  background: #f5f5f5;
  border-radius: 16px;
  font-size: 13px;
  color: #4b5563;
}

.tab-btn.active {
  background: #1677ff;
  color: #fff;
  font-weight: 700;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: #f3f4f6;
  color: #374151;
  display: flex;
  align-items: center;
  justify-content: center;
}

.panel-body {
  flex: 1;
  position: relative;
  overflow-y: auto;
  padding: 12px;
}

.loading-mask,
.empty-tip {
  height: 100%;
  min-height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  color: #9ca3af;
  gap: 8px;
}

.material-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.material-item {
  min-width: 0;
  border: 1px solid #eef1f5;
  border-radius: 8px;
  background: #fff;
  padding: 6px;
}

.material-item img {
  width: 100%;
  aspect-ratio: 1;
  display: block;
  object-fit: contain;
  background: #f8fafc;
  border-radius: 6px;
}

.item-name {
  display: block;
  margin-top: 5px;
  overflow: hidden;
  color: #4b5563;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.load-more-tip {
  display: flex;
  justify-content: center;
  padding: 12px 0 4px;
  color: #9ca3af;
  font-size: 12px;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.22s ease, opacity 0.22s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
