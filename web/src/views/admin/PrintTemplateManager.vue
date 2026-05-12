<template>
  <div class="template-manager">
    <template v-if="mode === 'list'">
      <div class="panel-toolbar">
        <div>
          <h3>模版列表</h3>
          <p>选择当前活动使用的打印模版。纸张尺寸、打印画布尺寸会跟随当前模版生效。</p>
        </div>
        <a-space>
          <a-button @click="loadTemplates" :loading="loading">刷新</a-button>
          <a-button type="primary" @click="openCreateModal">
            <template #icon><PlusOutlined /></template>
            新建模版
          </a-button>
        </a-space>
      </div>

      <a-spin :spinning="loading">
        <div v-if="templates.length" class="template-grid">
          <div v-for="item in templates" :key="item.id" class="template-card" :class="{ active: item.id === activeTemplateId }">
            <div class="template-preview" :style="previewBoxStyle(item)">
              <span>{{ item.width }} x {{ item.height }}</span>
            </div>
            <div class="template-meta">
              <strong>{{ item.name }}</strong>
              <span>{{ item.paperLabel }} / {{ item.paperWidthMm }} x {{ item.paperHeightMm }} mm / {{ item.photoCount }} 张照片</span>
            </div>
            <div class="template-actions">
              <a-button size="small" @click.stop="editTemplate(item)">编辑</a-button>
              <a-button size="small" type="link" @click.stop="setActiveTemplate(item)">设为当前</a-button>
              <a-popconfirm title="确定删除该模版？" @confirm="deleteTemplate(item.id)">
                <a-button size="small" danger type="link" @click.stop>删除</a-button>
              </a-popconfirm>
            </div>
          </div>
        </div>
        <a-empty v-else description="暂无模版，请点击新建模版" />
      </a-spin>
    </template>

    <template v-else>
      <div class="editor-shell">
        <aside class="editor-sidebar">
          <a-button type="link" class="back-link" @click="backToList">
            <template #icon><ArrowLeftOutlined /></template>
            返回模版列表
          </a-button>

          <div class="side-section">
            <label>模版名称</label>
            <a-input v-model:value="editingTemplate.name" :maxlength="50" placeholder="请输入模版名称" />
            <div class="template-facts">
              <span>{{ editingTemplate.paperLabel }}</span>
              <span>{{ editingTemplate.paperWidthMm }} x {{ editingTemplate.paperHeightMm }} mm</span>
              <span>{{ editingTemplate.width }} x {{ editingTemplate.height }} px</span>
            </div>
          </div>

          <div class="side-section">
            <div class="side-title">添加素材</div>
            <div class="material-actions">
              <a-button @click="openMaterialPicker('background')">
                <template #icon><PictureOutlined /></template>
                背景
              </a-button>
              <a-button @click="openMaterialPicker('frame')">
                <template #icon><BorderOutlined /></template>
                相框
              </a-button>
              <a-button @click="openMaterialPicker('sticker')">
                <template #icon><BgColorsOutlined /></template>
                贴纸
              </a-button>
              <a-button @click="addText">
                <template #icon><FontSizeOutlined /></template>
                文字
              </a-button>
            </div>
            <a-button block @click="addPhotoSlot">
              <template #icon><PlusOutlined /></template>
              添加照片区域
            </a-button>
          </div>

          <div class="editor-actions">
            <a-button block @click="backToList">取消</a-button>
            <a-button block type="primary" :loading="saving" @click="saveEditingTemplate">保存</a-button>
          </div>

          <div class="side-section layer-list-section">
            <div class="side-title">元素选择</div>
            <div v-if="layerItems.length" class="layer-list">
              <button
                v-for="item in layerItems"
                :key="item.id"
                type="button"
                class="layer-list-item"
                :class="{ active: item.object === selectedObject }"
                @click="selectLayerObject(item.object)"
              >
                <span class="layer-name">{{ item.name }}</span>
                <span class="layer-role">{{ item.roleLabel }}</span>
              </button>
            </div>
            <a-empty v-else class="layer-empty" description="暂无元素" />
          </div>
        </aside>

        <main class="editor-main">
          <div class="canvas-size-label">{{ editingTemplate.width }} x {{ editingTemplate.height }} px</div>
          <div class="design-stage-wrap">
            <div class="canvas-frame" :style="canvasFrameStyle">
              <canvas ref="canvasRef" />
            </div>
          </div>
        </main>

        <aside class="inspector-panel">
          <div class="side-section">
            <div class="side-title">图层控件</div>
            <div class="layer-actions">
              <a-button :disabled="!selectedObject" @click="bringForward">上移</a-button>
              <a-button :disabled="!selectedObject" @click="sendBackward">下移</a-button>
              <a-button :disabled="!selectedObject" @click="toggleLock">
                {{ selectedLocked ? '解锁' : '锁定' }}
              </a-button>
              <a-button danger :disabled="!selectedObject" @click="deleteSelected">删除</a-button>
              <a-button :disabled="!selectedObject" @click="alignSelected('horizontal')">左右居中</a-button>
              <a-button :disabled="!selectedObject" @click="alignSelected('vertical')">上下居中</a-button>
              <a-button :disabled="!selectedObject" @click="alignSelected('center')">中心点居中</a-button>
              <a-button :disabled="!selectedObject" @click="bringToFront">置顶</a-button>
              <a-button :disabled="!selectedObject" @click="sendToBack">置底</a-button>
            </div>
          </div>

          <div v-if="selectedIsText" class="side-section property-panel">
            <div class="side-title">文字属性</div>
            <label><span>文字内容</span><a-input v-model:value="inspector.text" @change="applyTextProps" /></label>
            <div class="property-grid">
              <label><span>字号</span><a-input-number v-model:value="inspector.fontSize" :min="8" :max="400" @change="applyTextProps" /></label>
              <label>
                <span>字体</span>
                <a-select v-model:value="inspector.fontFamily" :options="fontOptions" @change="applyTextProps" />
              </label>
              <label><span>颜色</span><input v-model="inspector.fill" class="color-field" type="color" @input="applyTextProps" /></label>
              <label>
                <span>对齐</span>
                <a-select v-model:value="inspector.textAlign" :options="textAlignOptions" @change="applyTextProps" />
              </label>
            </div>
            <div class="inline-checks">
              <a-checkbox v-model:checked="inspector.bold" @change="applyTextProps">粗体</a-checkbox>
              <a-checkbox v-model:checked="inspector.italic" @change="applyTextProps">斜体</a-checkbox>
              <a-checkbox v-model:checked="inspector.underline" @change="applyTextProps">下划线</a-checkbox>
              <a-checkbox v-model:checked="inspector.shadowEnabled" @change="applyTextProps">阴影</a-checkbox>
            </div>
            <div v-if="inspector.shadowEnabled" class="property-grid">
              <label><span>阴影色</span><input v-model="inspector.shadowColor" class="color-field" type="color" @input="applyTextProps" /></label>
              <label><span>模糊</span><a-input-number v-model:value="inspector.shadowBlur" :min="0" :max="80" @change="applyTextProps" /></label>
              <label><span>X</span><a-input-number v-model:value="inspector.shadowOffsetX" :min="-100" :max="100" @change="applyTextProps" /></label>
              <label><span>Y</span><a-input-number v-model:value="inspector.shadowOffsetY" :min="-100" :max="100" @change="applyTextProps" /></label>
            </div>
          </div>

          <div v-if="selectedIsGraphic" class="side-section property-panel">
            <div class="side-title">{{ selectedIsSvg ? 'SVG属性' : '图形属性' }}</div>
            <div class="property-grid">
              <label><span>X</span><a-input-number v-model:value="inspector.x" :min="-editingTemplate.width" :max="editingTemplate.width * 2" @change="applyObjectBox" /></label>
              <label><span>Y</span><a-input-number v-model:value="inspector.y" :min="-editingTemplate.height" :max="editingTemplate.height * 2" @change="applyObjectBox" /></label>
              <label><span>宽</span><a-input-number v-model:value="inspector.width" :min="1" :max="editingTemplate.width * 2" @change="applyObjectBox" /></label>
              <label><span>高</span><a-input-number v-model:value="inspector.height" :min="1" :max="editingTemplate.height * 2" @change="applyObjectBox" /></label>
              <label><span>旋转</span><a-input-number v-model:value="inspector.angle" :min="-360" :max="360" @change="applyObjectVisualProps" /></label>
              <label><span>透明度</span><a-input-number v-model:value="inspector.opacity" :min="0" :max="100" @change="applyObjectVisualProps" /></label>
            </div>
            <div v-if="selectedIsSvg" class="property-grid">
              <label><span>填充</span><input v-model="inspector.fill" class="color-field" type="color" @input="applyObjectVisualProps" /></label>
              <label><span>描边</span><input v-model="inspector.stroke" class="color-field" type="color" @input="applyObjectVisualProps" /></label>
              <label><span>线宽</span><a-input-number v-model:value="inspector.strokeWidth" :min="0" :max="80" @change="applyObjectVisualProps" /></label>
            </div>
          </div>

          <div v-if="selectedAllowsObjectMargin" class="side-section property-panel">
            <div class="side-title">元素边距</div>
            <div class="margin-form">
              <label><span>margin-left</span><a-input-number :value="objectMargin('left')" :min="0" :max="editingTemplate.width" @change="setObjectMarginLeft" /></label>
              <label><span>margin-right</span><a-input-number :value="objectMargin('right')" :min="0" :max="editingTemplate.width" @change="setObjectMarginRight" /></label>
              <label><span>margin-top</span><a-input-number :value="objectMargin('top')" :min="0" :max="editingTemplate.height" @change="setObjectMarginTop" /></label>
              <label><span>margin-bottom</span><a-input-number :value="objectMargin('bottom')" :min="0" :max="editingTemplate.height" @change="setObjectMarginBottom" /></label>
            </div>
          </div>

          <div v-if="selectedIsPhotoSlot" class="side-section">
            <div class="side-title">照片区域</div>
            <a-segmented v-model:value="selectedSlotId" :options="slotOptions" @change="selectSlot" />
            <div v-if="selectedSlot" class="ratio-actions">
              <button
                v-for="option in aspectRatioOptions"
                :key="option.label"
                type="button"
                :class="{ active: isSlotRatioActive(option.value) }"
                @click="applySlotAspectRatio(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
            <div v-if="selectedSlot" class="slot-form">
              <label><span>X</span><a-input-number v-model:value="selectedSlot.x" :min="0" :max="editingTemplate.width" @change="syncSelectedSlot" /></label>
              <label><span>Y</span><a-input-number v-model:value="selectedSlot.y" :min="0" :max="editingTemplate.height" @change="syncSelectedSlot" /></label>
              <label><span>宽</span><a-input-number v-model:value="selectedSlot.width" :min="20" :max="editingTemplate.width" @change="syncSelectedSlot" /></label>
              <label><span>高</span><a-input-number v-model:value="selectedSlot.height" :min="20" :max="editingTemplate.height" @change="syncSelectedSlot" /></label>
            </div>

            <div v-if="selectedSlot" class="margin-form">
              <div class="side-subtitle">相对画布边距</div>
              <label>
                <span>margin-left</span>
                <a-input-number :value="slotMargin('left')" :min="0" :max="editingTemplate.width" @change="setSlotMarginLeft" />
              </label>
              <label>
                <span>margin-right</span>
                <a-input-number :value="slotMargin('right')" :min="0" :max="editingTemplate.width" @change="setSlotMarginRight" />
              </label>
              <label>
                <span>margin-top</span>
                <a-input-number :value="slotMargin('top')" :min="0" :max="editingTemplate.height" @change="setSlotMarginTop" />
              </label>
              <label>
                <span>margin-bottom</span>
                <a-input-number :value="slotMargin('bottom')" :min="0" :max="editingTemplate.height" @change="setSlotMarginBottom" />
              </label>
            </div>
          </div>
        </aside>
      </div>
    </template>

    <a-modal v-model:open="createModalOpen" title="选择模版尺寸" width="640px" ok-text="确定" cancel-text="取消" @ok="createTemplate">
      <div class="create-form">
        <div class="create-field">
          <label>照片数量</label>
          <a-segmented v-model:value="createForm.photoCount" :options="photoCountOptions" />
        </div>
        <div class="create-field">
          <label>模版尺寸</label>
          <div class="size-grid">
            <button
              v-for="size in sizeOptions"
              :key="size.key"
              type="button"
              class="size-card"
              :class="{ active: createForm.sizeKey === size.key }"
              @click="createForm.sizeKey = size.key"
            >
              <span class="size-icon" :class="{ portrait: size.height > size.width }" />
              <strong>{{ size.label }}</strong>
              <small>{{ size.width }}x{{ size.height }}</small>
              <small>{{ size.paperWidthMm }}x{{ size.paperHeightMm }}mm</small>
            </button>
          </div>
        </div>
      </div>
    </a-modal>

    <a-modal v-model:open="materialModalOpen" :title="materialModalTitle" width="820px" :footer="null">
      <a-spin :spinning="materialsLoading">
        <div class="material-modal-toolbar">
          <a-upload :show-upload-list="false" accept="image/*,.svg" :before-upload="uploadToCanvas">
            <a-button>
              <template #icon><UploadOutlined /></template>
              本地上传
            </a-button>
          </a-upload>
        </div>
        <div v-if="materials.length" class="material-picker">
          <div class="material-categories">
            <button
              v-for="category in materialCategories"
              :key="category"
              type="button"
              :class="{ active: activeMaterialCategory === category }"
              @click="activeMaterialCategory = category"
            >
              {{ category }}
            </button>
          </div>
          <div class="material-grid">
            <button v-for="item in visibleMaterials" :key="item.id" type="button" class="material-item" @click="selectMaterial(item)">
              <img :src="item.thumbnail_url || item.storage_url" :alt="item.name" />
              <span>{{ item.name }}</span>
            </button>
          </div>
        </div>
        <a-empty v-if="!materials.length && !materialsLoading" description="暂无素材" />
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { Canvas, FabricImage, FabricObject, IText, Point, Rect, Shadow, loadSVGFromURL, util } from 'fabric'
import {
  ArrowLeftOutlined,
  BgColorsOutlined,
  BorderOutlined,
  FontSizeOutlined,
  PictureOutlined,
  PlusOutlined,
  UploadOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'
import { materialApi, type DecorationMaterialItem } from '@/api/admin'

FabricObject.customProperties = ['_templateRole', '_slotId', '_isSvg', '_lockedAspectRatio', '_locked']

interface PhotoSlot {
  id: string
  x: number
  y: number
  width: number
  height: number
  aspectRatio?: number | null
}

interface TemplateSize {
  key: string
  label: string
  width: number
  height: number
  paperWidthMm: number
  paperHeightMm: number
}

interface PrintTemplateItem {
  id: string
  name: string
  width: number
  height: number
  paperWidthMm: number
  paperHeightMm: number
  dmPaperSize: string
  paperLabel: string
  photoCount: number
  sizeKey: string
  photoSlots: PhotoSlot[]
  canvasJson?: any
}

type SlotMarginSide = 'left' | 'right' | 'top' | 'bottom'
type TemplateRole = 'photo-slot' | 'photo-label' | 'background' | 'frame' | 'sticker' | 'upload' | 'text' | 'svg' | ''

interface LayerItem {
  id: string
  name: string
  roleLabel: string
  object: FabricObject
}

const props = defineProps<{
  activityId: number
}>()

const settingKey = computed(() => `activity_${props.activityId}_print_template`)
const loading = ref(false)
const saving = ref(false)
const mode = ref<'list' | 'editor'>('list')
const createModalOpen = ref(false)
const materialModalOpen = ref(false)
const materialType = ref<'background' | 'frame' | 'sticker'>('background')
const templates = ref<PrintTemplateItem[]>([])
const activeTemplateId = ref('')
const selectedSlotId = ref('')
const canvasRef = ref<HTMLCanvasElement | null>(null)
const fabricCanvas = shallowRef<Canvas | null>(null)
const selectedObject = shallowRef<FabricObject | null>(null)
const selectedLocked = ref(false)
const layerItems = shallowRef<LayerItem[]>([])
const layerObjectIds = new WeakMap<object, string>()
let layerObjectSeed = 0
const materials = ref<DecorationMaterialItem[]>([])
const materialsLoading = ref(false)
const activeMaterialCategory = ref('全部')
const inspector = reactive({
  text: '',
  x: 0,
  y: 0,
  width: 0,
  height: 0,
  angle: 0,
  opacity: 100,
  fill: '#111827',
  stroke: '#000000',
  strokeWidth: 0,
  fontSize: 60,
  fontFamily: 'sans-serif',
  bold: false,
  italic: false,
  underline: false,
  textAlign: 'left',
  shadowEnabled: false,
  shadowColor: '#000000',
  shadowBlur: 8,
  shadowOffsetX: 4,
  shadowOffsetY: 4,
})

const baseConfig = reactive<Record<string, any>>({
  templateName: '活动照片贴纸',
  freePrintLimit: 2,
  printConfigMode: 'activity',
  paperKey: 'template',
  dmPaperSize: '0',
  paperWidthMm: 127,
  paperHeightMm: 127,
  canvasWidth: 1500,
  canvasHeight: 1500,
  photoInitX: 50,
  photoInitY: 50,
  photoInitScale: 100,
  photoMargin: 120,
  templates: [],
  activeTemplateId: '',
})

const editingTemplate = reactive<PrintTemplateItem>({
  id: '',
  name: '',
  width: 1500,
  height: 1500,
  paperWidthMm: 127,
  paperHeightMm: 127,
  dmPaperSize: '0',
  paperLabel: '方5寸',
  photoCount: 1,
  sizeKey: 'square-5',
  photoSlots: [],
})

const createForm = reactive({
  photoCount: 1,
  sizeKey: 'square-5',
})

const photoCountOptions = [
  { label: '1', value: 1 },
  { label: '2', value: 2 },
  { label: '3', value: 3 },
  { label: '4', value: 4 },
]

const sizeOptions: TemplateSize[] = [
  { key: 'h4', label: '横4寸', width: 1500, height: 1050, paperWidthMm: 102, paperHeightMm: 71 },
  { key: 'v4', label: '竖4寸', width: 1050, height: 1500, paperWidthMm: 71, paperHeightMm: 102 },
  { key: 'square-5', label: '方5寸', width: 1500, height: 1500, paperWidthMm: 127, paperHeightMm: 127 },
  { key: 'h5', label: '横5寸', width: 1500, height: 1050, paperWidthMm: 127, paperHeightMm: 89 },
  { key: 'v5', label: '竖5寸', width: 1050, height: 1500, paperWidthMm: 89, paperHeightMm: 127 },
  { key: 'h6', label: '横6寸', width: 1800, height: 1200, paperWidthMm: 152, paperHeightMm: 102 },
  { key: 'v6', label: '竖6寸', width: 1200, height: 1800, paperWidthMm: 102, paperHeightMm: 152 },
]

const selectedSlot = computed(() => editingTemplate.photoSlots.find(slot => slot.id === selectedSlotId.value) || null)
const slotOptions = computed(() => editingTemplate.photoSlots.map((slot, index) => ({ label: `照片 ${index + 1}`, value: slot.id })))
const materialModalTitle = computed(() => ({ background: '选择背景', frame: '选择相框', sticker: '选择贴纸' }[materialType.value]))
const materialCategories = computed(() => {
  const categories = new Set(materials.value.map(item => item.category || '未分类'))
  return ['全部', ...Array.from(categories)]
})
const visibleMaterials = computed(() => {
  if (activeMaterialCategory.value === '全部') return materials.value
  return materials.value.filter(item => (item.category || '未分类') === activeMaterialCategory.value)
})
const selectedRole = computed<TemplateRole>(() => ((selectedObject.value as any)?._templateRole || '') as TemplateRole)
const selectedIsPhotoSlot = computed(() => selectedRole.value === 'photo-slot')
const selectedIsText = computed(() => selectedRole.value === 'text')
const selectedIsSvg = computed(() => !!(selectedObject.value as any)?._isSvg)
const selectedIsGraphic = computed(() => !!selectedObject.value && !selectedIsPhotoSlot.value && !selectedIsText.value)
const selectedAllowsObjectMargin = computed(() => selectedRole.value === 'background' || selectedRole.value === 'frame')

const fontOptions = [
  { label: '默认黑体', value: 'sans-serif' },
  { label: '宋体', value: 'SimSun' },
  { label: '微软雅黑', value: 'Microsoft YaHei' },
  { label: '思源黑体', value: 'Noto Sans CJK SC' },
  { label: 'Arial', value: 'Arial' },
  { label: 'Georgia', value: 'Georgia' },
]

const textAlignOptions = [
  { label: '左对齐', value: 'left' },
  { label: '居中', value: 'center' },
  { label: '右对齐', value: 'right' },
]

const aspectRatioOptions = [
  { label: '1:1', value: 1 },
  { label: '16:9', value: 16 / 9 },
  { label: '9:16', value: 9 / 16 },
  { label: '4:3', value: 4 / 3 },
  { label: '3:4', value: 3 / 4 },
]

const stageScale = computed(() => {
  const maxW = 860
  const maxH = 620
  return Math.min(maxW / editingTemplate.width, maxH / editingTemplate.height, 1)
})

const canvasFrameStyle = computed(() => ({
  width: `${Math.round(editingTemplate.width * stageScale.value)}px`,
  height: `${Math.round(editingTemplate.height * stageScale.value)}px`,
}))

function previewBoxStyle(template: PrintTemplateItem) {
  const width = template.width >= template.height ? 230 : Math.round(230 * template.width / template.height)
  const height = template.width >= template.height ? Math.round(230 * template.height / template.width) : 230
  return {
    width: `${width}px`,
    height: `${height}px`,
  }
}

const slotPalette = [
  { fill: 'rgba(59, 130, 246, 0.22)', stroke: '#2563eb' },
  { fill: 'rgba(236, 72, 153, 0.22)', stroke: '#db2777' },
  { fill: 'rgba(16, 185, 129, 0.22)', stroke: '#059669' },
  { fill: 'rgba(245, 158, 11, 0.24)', stroke: '#d97706' },
]

function slotVisual(slotId: string) {
  const matched = String(slotId || '').match(/\d+$/)
  const index = Math.max(0, Number(matched?.[0] || 1) - 1)
  return slotPalette[index % slotPalette.length]
}

function generateSlots(count: number, width: number, height: number): PhotoSlot[] {
  const margin = Math.round(Math.min(width, height) * 0.08)
  const gap = Math.round(Math.min(width, height) * 0.035)
  if (count === 1) {
    return [{ id: 'photo-1', x: margin, y: margin, width: width - margin * 2, height: height - margin * 2 }]
  }
  const cols = 2
  const rows = Math.ceil(count / cols)
  const slotW = Math.round((width - margin * 2 - gap * (cols - 1)) / cols)
  const slotH = Math.round((height - margin * 2 - gap * (rows - 1)) / rows)
  return Array.from({ length: count }, (_, index) => {
    const col = index % cols
    const row = Math.floor(index / cols)
    return {
      id: `photo-${index + 1}`,
      x: margin + col * (slotW + gap),
      y: margin + row * (slotH + gap),
      width: slotW,
      height: slotH,
    }
  })
}

function makePhotoSlot(slot: PhotoSlot) {
  const visual = slotVisual(slot.id)
  const rect = new Rect({
    left: slot.x,
    top: slot.y,
    width: slot.width,
    height: slot.height,
    fill: visual.fill,
    stroke: visual.stroke,
    strokeWidth: 2,
    strokeDashArray: [10, 8],
    originX: 'left',
    originY: 'top',
    hasControls: true,
    hasBorders: true,
    lockScalingFlip: true,
  }) as any
  rect._templateRole = 'photo-slot'
  rect._slotId = slot.id
  rect._lockedAspectRatio = slot.aspectRatio || null
  return rect
}

function getSlotObject(slotId: string) {
  return fabricCanvas.value?.getObjects().find((item: any) => item._templateRole === 'photo-slot' && item._slotId === slotId) as any
}

function updatePhotoSlotLabel(slotId: string) {
  const canvas = fabricCanvas.value
  const slot = editingTemplate.photoSlots.find(item => item.id === slotId)
  if (!canvas || !slot) return
  const obj = getSlotObject(slotId)
  if (!obj) return
  const visual = slotVisual(slotId)
  obj.set({ fill: visual.fill, stroke: visual.stroke, strokeDashArray: [10, 8] })
  obj.setCoords()
  canvas.renderAll()
}

function applyObjectLockState(obj: any, locked = !!obj?.lockMovementX) {
  if (!obj) return
  obj.set({
    lockMovementX: locked,
    lockMovementY: locked,
    lockScalingX: locked,
    lockScalingY: locked,
    lockRotation: locked,
    selectable: !locked,
    evented: !locked,
    hasControls: !locked,
    hasBorders: !locked,
    hoverCursor: locked ? 'default' : 'move',
  })
  obj._locked = locked
}

function ensurePhotoSlotLabels() {
  const canvas = fabricCanvas.value
  if (!canvas) return
  canvas.getObjects()
    .filter((item: any) => item._templateRole === 'photo-label')
    .forEach(item => canvas.remove(item))

  editingTemplate.photoSlots.forEach((slot) => {
    const obj = getSlotObject(slot.id)
    if (obj) {
      const visual = slotVisual(slot.id)
      obj.set({ fill: visual.fill, stroke: visual.stroke, strokeDashArray: [10, 8] })
    }
  })
  canvas.renderAll()
}

function layerObjectId(obj: FabricObject) {
  let id = layerObjectIds.get(obj)
  if (!id) {
    layerObjectSeed += 1
    id = `layer-${layerObjectSeed}`
    layerObjectIds.set(obj, id)
  }
  return id
}

function layerRoleLabel(obj: any) {
  const role = obj?._templateRole as TemplateRole
  if (role === 'photo-slot') return '\u7167\u7247\u533a\u57df'
  if (role === 'background') return '\u80cc\u666f'
  if (role === 'frame') return '\u76f8\u6846'
  if (role === 'sticker') return '\u8d34\u7eb8'
  if (role === 'upload') return '\u4e0a\u4f20\u56fe\u7247'
  if (role === 'text') return '\u6587\u5b57'
  if (role === 'svg' || obj?._isSvg) return 'SVG'
  const type = String(obj?.type || '').toLowerCase()
  if (type === 'image') return '\u56fe\u7247'
  if (type.includes('text')) return '\u6587\u5b57'
  if (type === 'rect') return '\u77e9\u5f62'
  return '\u5143\u7d20'
}

function layerObjectName(obj: any, stackIndex: number) {
  if (obj?._templateRole === 'photo-slot') {
    const index = editingTemplate.photoSlots.findIndex(slot => slot.id === obj._slotId)
    return `\u7167\u7247\u533a\u57df ${index >= 0 ? index + 1 : stackIndex + 1}`
  }
  if (obj?._templateRole === 'text') {
    const text = String(obj.text || '').trim()
    return text ? `\u6587\u5b57: ${text.slice(0, 18)}` : '\u6587\u5b57'
  }
  const roleLabel = layerRoleLabel(obj)
  return `${roleLabel} ${stackIndex + 1}`
}

function refreshLayerList() {
  const canvas = fabricCanvas.value
  if (!canvas) {
    layerItems.value = []
    return
  }
  const objects = canvas.getObjects()
    .filter((obj: any) => obj._templateRole !== 'photo-label')
  layerItems.value = objects
    .map((obj: any, index) => ({
      id: layerObjectId(obj),
      name: layerObjectName(obj, index),
      roleLabel: layerRoleLabel(obj),
      object: obj as FabricObject,
    }))
    .reverse()
}

function selectLayerObject(obj: FabricObject) {
  const canvas = fabricCanvas.value
  if (!canvas) return
  canvas.setActiveObject(obj)
  selectedObject.value = obj
  selectedLocked.value = !!(obj as any).lockMovementX
  if ((obj as any)._templateRole === 'photo-slot' && (obj as any)._slotId) {
    selectedSlotId.value = (obj as any)._slotId
  }
  refreshInspectorFromObject()
  canvas.requestRenderAll()
}

async function initEditorCanvas() {
  await nextTick()
  if (!canvasRef.value) return
  disposeCanvas()

  const displayW = Math.round(editingTemplate.width * stageScale.value)
  const displayH = Math.round(editingTemplate.height * stageScale.value)
  const canvas = new Canvas(canvasRef.value, {
    width: displayW,
    height: displayH,
    backgroundColor: '#ffffff',
    preserveObjectStacking: true,
    selection: true,
  })
  canvas.setZoom(stageScale.value)
  fabricCanvas.value = canvas
  canvas.on('selection:created', syncSelection)
  canvas.on('selection:updated', syncSelection)
  canvas.on('selection:cleared', () => {
    selectedObject.value = null
    selectedLocked.value = false
  })
  canvas.on('object:added', refreshLayerList)
  canvas.on('object:removed', refreshLayerList)
  canvas.on('object:scaling', maintainPhotoSlotAspectRatio)
  canvas.on('object:modified', handleObjectModified)

  if (editingTemplate.canvasJson) {
    try {
      await canvas.loadFromJSON(editingTemplate.canvasJson)
      canvas.getObjects().forEach((obj: any) => {
        applyObjectLockState(obj, !!obj.lockMovementX || !!obj._locked)
        if (obj._templateRole === 'photo-slot' && obj._slotId) {
          const slot = editingTemplate.photoSlots.find(item => item.id === obj._slotId)
          obj._lockedAspectRatio = slot?.aspectRatio || null
          const visual = slotVisual(obj._slotId)
          obj.set({ fill: visual.fill, stroke: visual.stroke, strokeDashArray: [10, 8], lockScalingFlip: true })
        } else if (obj._templateRole === 'photo-label') {
          canvas.remove(obj)
        }
      })
      ensurePhotoSlotLabels()
      refreshLayerList()
      canvas.renderAll()
    } catch {
      addInitialSlots()
    }
  } else {
    addInitialSlots()
  }

  const firstSlot = editingTemplate.photoSlots[0]
  if (firstSlot) selectSlot(firstSlot.id)
  refreshLayerList()
}

function addInitialSlots() {
  const canvas = fabricCanvas.value
  if (!canvas) return
  canvas.clear()
  canvas.backgroundColor = '#ffffff'
  editingTemplate.photoSlots.forEach((slot) => {
    canvas.add(makePhotoSlot(slot))
  })
  canvas.renderAll()
}

function disposeCanvas() {
  fabricCanvas.value?.dispose()
  fabricCanvas.value = null
  selectedObject.value = null
  selectedLocked.value = false
  layerItems.value = []
}

function syncSelection(event: any) {
  const obj = event.selected?.[0] || null
  selectedObject.value = obj
  selectedLocked.value = !!obj?.lockMovementX
  if (obj?._templateRole === 'photo-slot' && obj._slotId) {
    selectedSlotId.value = obj._slotId
  }
  refreshInspectorFromObject()
}

function handleObjectModified(event: any) {
  maintainPhotoSlotAspectRatio(event)
  syncSlotFromObject(event)
  refreshInspectorFromObject()
  refreshLayerList()
}

function maintainPhotoSlotAspectRatio(event: any) {
  const obj = event.target as any
  if (!obj || obj._templateRole !== 'photo-slot' || !obj._lockedAspectRatio) return
  const ratio = Number(obj._lockedAspectRatio)
  if (!Number.isFinite(ratio) || ratio <= 0) return
  const width = Math.max(20, (obj.width || 20) * (obj.scaleX || 1))
  const nextHeight = width / ratio
  obj.set({ scaleY: nextHeight / Math.max(1, obj.height || 1) })
  obj.setCoords()
}

function syncSlotFromObject(event: any) {
  const obj = event.target as any
  if (!obj || obj._templateRole !== 'photo-slot') return
  const slot = editingTemplate.photoSlots.find(item => item.id === obj._slotId)
  if (!slot) return
  slot.x = Math.round(obj.left || 0)
  slot.y = Math.round(obj.top || 0)
  slot.width = Math.round((obj.width || slot.width) * (obj.scaleX || 1))
  slot.height = Math.round((obj.height || slot.height) * (obj.scaleY || 1))
  if (obj._lockedAspectRatio) {
    slot.aspectRatio = Number(obj._lockedAspectRatio)
    slot.height = Math.round(slot.width / slot.aspectRatio)
  }
  obj.set({ width: slot.width, height: slot.height, scaleX: 1, scaleY: 1 })
  obj._lockedAspectRatio = slot.aspectRatio || null
  obj.setCoords()
  updatePhotoSlotLabel(slot.id)
}

function syncSelectedSlot() {
  const slot = selectedSlot.value
  const canvas = fabricCanvas.value
  if (!slot || !canvas) return
  normalizeSlotAspect(slot, 'width')
  const obj = canvas.getObjects().find((item: any) => item._slotId === slot.id) as any
  if (!obj) return
  obj.set({ left: slot.x, top: slot.y, width: slot.width, height: slot.height, scaleX: 1, scaleY: 1 })
  obj._lockedAspectRatio = slot.aspectRatio || null
  obj.setCoords()
  canvas.setActiveObject(obj)
  updatePhotoSlotLabel(slot.id)
  canvas.renderAll()
}

function normalizeSlotAspect(slot: PhotoSlot, source: 'width' | 'height' = 'width') {
  if (!slot.aspectRatio) return
  const ratio = Number(slot.aspectRatio)
  if (!Number.isFinite(ratio) || ratio <= 0) return
  if (source === 'height') {
    slot.width = Math.max(20, Math.round(slot.height * ratio))
    if (slot.x + slot.width > editingTemplate.width) {
      slot.width = Math.max(20, editingTemplate.width - slot.x)
      slot.height = Math.max(20, Math.round(slot.width / ratio))
    }
  } else {
    slot.height = Math.max(20, Math.round(slot.width / ratio))
    if (slot.y + slot.height > editingTemplate.height) {
      slot.height = Math.max(20, editingTemplate.height - slot.y)
      slot.width = Math.max(20, Math.round(slot.height * ratio))
    }
  }
}

function slotMargin(side: SlotMarginSide) {
  const slot = selectedSlot.value
  if (!slot) return 0
  if (side === 'left') return Math.max(0, Math.round(slot.x))
  if (side === 'right') return Math.max(0, Math.round(editingTemplate.width - slot.x - slot.width))
  if (side === 'top') return Math.max(0, Math.round(slot.y))
  return Math.max(0, Math.round(editingTemplate.height - slot.y - slot.height))
}

function setSlotMargin(side: SlotMarginSide, rawValue: number | string | null) {
  const slot = selectedSlot.value
  if (!slot) return
  const value = Math.max(0, Math.round(Number(rawValue) || 0))
  const minSize = 20
  const right = slotMargin('right')
  const bottom = slotMargin('bottom')

  if (side === 'left') {
    slot.x = Math.min(value, editingTemplate.width - minSize - right)
    slot.width = Math.max(minSize, editingTemplate.width - slot.x - right)
    normalizeSlotAspect(slot, 'width')
  } else if (side === 'right') {
    const nextRight = Math.min(value, editingTemplate.width - minSize - slot.x)
    slot.width = Math.max(minSize, editingTemplate.width - slot.x - nextRight)
    normalizeSlotAspect(slot, 'width')
  } else if (side === 'top') {
    slot.y = Math.min(value, editingTemplate.height - minSize - bottom)
    slot.height = Math.max(minSize, editingTemplate.height - slot.y - bottom)
    normalizeSlotAspect(slot, 'height')
  } else {
    const nextBottom = Math.min(value, editingTemplate.height - minSize - slot.y)
    slot.height = Math.max(minSize, editingTemplate.height - slot.y - nextBottom)
    normalizeSlotAspect(slot, 'height')
  }

  syncSelectedSlot()
}

function setSlotMarginLeft(value: number | string | null) {
  setSlotMargin('left', value)
}

function setSlotMarginRight(value: number | string | null) {
  setSlotMargin('right', value)
}

function setSlotMarginTop(value: number | string | null) {
  setSlotMargin('top', value)
}

function setSlotMarginBottom(value: number | string | null) {
  setSlotMargin('bottom', value)
}

function isSlotRatioActive(ratio: number) {
  return Math.abs(Number(selectedSlot.value?.aspectRatio || 0) - ratio) < 0.001
}

function applySlotAspectRatio(ratio: number) {
  const slot = selectedSlot.value
  if (!slot) return
  const maxWidth = Math.max(20, editingTemplate.width - slot.x)
  const maxHeight = Math.max(20, editingTemplate.height - slot.y)
  let width = Math.max(20, slot.width)
  let height = Math.round(width / ratio)
  if (height > maxHeight) {
    height = maxHeight
    width = Math.round(height * ratio)
  }
  if (width > maxWidth) {
    width = maxWidth
    height = Math.round(width / ratio)
  }
  slot.width = Math.max(20, width)
  slot.height = Math.max(20, height)
  slot.aspectRatio = ratio
  syncSelectedSlot()
  refreshInspectorFromObject()
}

function nextPhotoSlotId() {
  let index = editingTemplate.photoSlots.length + 1
  const used = new Set(editingTemplate.photoSlots.map(slot => slot.id))
  while (used.has(`photo-${index}`)) index += 1
  return `photo-${index}`
}

function addPhotoSlot() {
  const canvas = fabricCanvas.value
  if (!canvas) return
  const size = Math.round(Math.min(editingTemplate.width, editingTemplate.height) * 0.38)
  const slot: PhotoSlot = {
    id: nextPhotoSlotId(),
    x: Math.round((editingTemplate.width - size) / 2),
    y: Math.round((editingTemplate.height - size) / 2),
    width: size,
    height: size,
    aspectRatio: 1,
  }
  editingTemplate.photoSlots.push(slot)
  const rect = makePhotoSlot(slot)
  canvas.add(rect)
  selectedSlotId.value = slot.id
  canvas.setActiveObject(rect)
  selectedObject.value = rect
  refreshInspectorFromObject()
  ensurePhotoSlotLabels()
}

function normalizeColor(value: any, fallback = '#000000') {
  if (typeof value !== 'string') return fallback
  if (/^#[0-9a-f]{6}$/i.test(value)) return value
  if (/^#[0-9a-f]{3}$/i.test(value)) {
    return `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`
  }
  const rgb = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i)
  if (!rgb) return fallback
  return `#${[rgb[1], rgb[2], rgb[3]].map(part => Number(part).toString(16).padStart(2, '0')).join('')}`
}

function selectedAny() {
  return selectedObject.value as any
}

function objectBox(obj = selectedAny()) {
  if (!obj) return { left: 0, top: 0, width: 0, height: 0 }
  const box = obj.getBoundingRect()
  return {
    left: Math.round(box.left),
    top: Math.round(box.top),
    width: Math.round(box.width),
    height: Math.round(box.height),
  }
}

function refreshInspectorFromObject() {
  const obj = selectedAny()
  if (!obj) return
  const box = objectBox(obj)
  inspector.x = box.left
  inspector.y = box.top
  inspector.width = box.width
  inspector.height = box.height
  inspector.angle = Math.round(Number(obj.angle || 0))
  inspector.opacity = Math.round(Number(obj.opacity ?? 1) * 100)
  inspector.fill = normalizeColor(obj.fill, inspector.fill)
  inspector.stroke = normalizeColor(obj.stroke, inspector.stroke)
  inspector.strokeWidth = Math.round(Number(obj.strokeWidth || 0))

  if (obj._templateRole === 'text') {
    inspector.text = obj.text || ''
    inspector.fontSize = Math.round(Number(obj.fontSize || 60))
    inspector.fontFamily = obj.fontFamily || 'sans-serif'
    inspector.bold = String(obj.fontWeight || '').toLowerCase() === 'bold' || Number(obj.fontWeight) >= 600
    inspector.italic = obj.fontStyle === 'italic'
    inspector.underline = !!obj.underline
    inspector.textAlign = obj.textAlign || 'left'
    inspector.fill = normalizeColor(obj.fill, '#111827')
    inspector.shadowEnabled = !!obj.shadow
    if (obj.shadow) {
      inspector.shadowColor = normalizeColor(obj.shadow.color, '#000000')
      inspector.shadowBlur = Math.round(Number(obj.shadow.blur || 0))
      inspector.shadowOffsetX = Math.round(Number(obj.shadow.offsetX || 0))
      inspector.shadowOffsetY = Math.round(Number(obj.shadow.offsetY || 0))
    }
  }
}

function setSelectedObjectBox(left: number, top: number, width: number, height: number) {
  const obj = selectedAny()
  if (!obj) return
  const current = objectBox(obj)
  const safeWidth = Math.max(1, width)
  const safeHeight = Math.max(1, height)
  const scaleX = (Number(obj.scaleX || 1) * safeWidth) / Math.max(1, current.width)
  const scaleY = (Number(obj.scaleY || 1) * safeHeight) / Math.max(1, current.height)
  obj.set({ scaleX, scaleY })
  obj.setPositionByOrigin(new Point(left + safeWidth / 2, top + safeHeight / 2), 'center', 'center')
  obj.setCoords()
  syncSlotFromObject({ target: obj })
}

function applyObjectBox() {
  const canvas = fabricCanvas.value
  if (!canvas || !selectedObject.value) return
  setSelectedObjectBox(inspector.x, inspector.y, inspector.width, inspector.height)
  refreshInspectorFromObject()
  canvas.renderAll()
}

function applyPaintToObject(obj: any, props: Record<string, any>) {
  obj.set(props)
  const children = obj._objects || []
  children.forEach((child: any) => child.set(props))
}

function applyObjectVisualProps() {
  const canvas = fabricCanvas.value
  const obj = selectedAny()
  if (!canvas || !obj) return
  obj.set({
    angle: inspector.angle,
    opacity: Math.max(0, Math.min(100, Number(inspector.opacity || 0))) / 100,
  })
  if (obj._isSvg) {
    applyPaintToObject(obj, {
      fill: inspector.fill,
      stroke: inspector.stroke,
      strokeWidth: Number(inspector.strokeWidth || 0),
    })
  }
  obj.setCoords()
  refreshInspectorFromObject()
  canvas.renderAll()
  refreshLayerList()
}

function applyTextProps() {
  const canvas = fabricCanvas.value
  const obj = selectedAny()
  if (!canvas || !obj || obj._templateRole !== 'text') return
  obj.set({
    text: inspector.text,
    fontSize: Number(inspector.fontSize || 60),
    fontFamily: inspector.fontFamily,
    fill: inspector.fill,
    fontWeight: inspector.bold ? 'bold' : 'normal',
    fontStyle: inspector.italic ? 'italic' : 'normal',
    underline: inspector.underline,
    textAlign: inspector.textAlign,
    shadow: inspector.shadowEnabled
      ? new Shadow({
          color: inspector.shadowColor,
          blur: Number(inspector.shadowBlur || 0),
          offsetX: Number(inspector.shadowOffsetX || 0),
          offsetY: Number(inspector.shadowOffsetY || 0),
        })
      : null,
  })
  obj.setCoords()
  refreshInspectorFromObject()
  canvas.renderAll()
  refreshLayerList()
}

function objectMargin(side: SlotMarginSide) {
  const obj = selectedAny()
  if (!obj) return 0
  const box = objectBox(obj)
  if (side === 'left') return Math.max(0, box.left)
  if (side === 'right') return Math.max(0, Math.round(editingTemplate.width - box.left - box.width))
  if (side === 'top') return Math.max(0, box.top)
  return Math.max(0, Math.round(editingTemplate.height - box.top - box.height))
}

function setObjectMargin(side: SlotMarginSide, rawValue: number | string | null) {
  const canvas = fabricCanvas.value
  const obj = selectedAny()
  if (!canvas || !obj) return
  const value = Math.max(0, Math.round(Number(rawValue) || 0))
  const minSize = 1
  const box = objectBox(obj)
  const right = objectMargin('right')
  const bottom = objectMargin('bottom')
  let left = box.left
  let top = box.top
  let width = box.width
  let height = box.height

  if (side === 'left') {
    left = Math.min(value, editingTemplate.width - minSize - right)
    width = Math.max(minSize, editingTemplate.width - left - right)
  } else if (side === 'right') {
    const nextRight = Math.min(value, editingTemplate.width - minSize - left)
    width = Math.max(minSize, editingTemplate.width - left - nextRight)
  } else if (side === 'top') {
    top = Math.min(value, editingTemplate.height - minSize - bottom)
    height = Math.max(minSize, editingTemplate.height - top - bottom)
  } else {
    const nextBottom = Math.min(value, editingTemplate.height - minSize - top)
    height = Math.max(minSize, editingTemplate.height - top - nextBottom)
  }

  setSelectedObjectBox(left, top, width, height)
  refreshInspectorFromObject()
  canvas.renderAll()
}

function setObjectMarginLeft(value: number | string | null) {
  setObjectMargin('left', value)
}

function setObjectMarginRight(value: number | string | null) {
  setObjectMargin('right', value)
}

function setObjectMarginTop(value: number | string | null) {
  setObjectMargin('top', value)
}

function setObjectMarginBottom(value: number | string | null) {
  setObjectMargin('bottom', value)
}

function selectSlot(value: string | number) {
  const id = String(value)
  selectedSlotId.value = id
  const canvas = fabricCanvas.value
  if (!canvas) return
  const obj = canvas.getObjects().find((item: any) => item._slotId === id)
  if (obj) {
    canvas.setActiveObject(obj)
    selectedObject.value = obj
    selectedLocked.value = !!(obj as any).lockMovementX
    refreshInspectorFromObject()
    canvas.renderAll()
  }
}

function alignSelected(mode: 'horizontal' | 'vertical' | 'center') {
  const canvas = fabricCanvas.value
  const obj = selectedObject.value as any
  if (!canvas || !obj) return

  if (mode === 'horizontal' || mode === 'center') {
    obj.setPositionByOrigin(new Point(editingTemplate.width / 2, obj.getCenterPoint().y), 'center', 'center')
  }
  if (mode === 'vertical' || mode === 'center') {
    obj.setPositionByOrigin(new Point(obj.getCenterPoint().x, editingTemplate.height / 2), 'center', 'center')
  }
  obj.setCoords()
  canvas.setActiveObject(obj)
  syncSlotFromObject({ target: obj })
  refreshInspectorFromObject()
  canvas.renderAll()
}

function isSvgUrl(url: string) {
  return /\.svg(?:$|[?#])/i.test(url)
}

async function loadCanvasAsset(url: string, role: 'background' | 'frame' | 'sticker' | 'upload') {
  if (!isSvgUrl(url)) {
    const img = await FabricImage.fromURL(url, { crossOrigin: 'anonymous' })
    return { object: img as any, isSvg: false }
  }

  const parsed = await loadSVGFromURL(url, undefined, { crossOrigin: 'anonymous' })
  const objects = parsed.objects.filter(Boolean) as FabricObject[]
  const svgObject = util.groupSVGElements(objects, parsed.options) as any
  svgObject._isSvg = true
  svgObject._templateRole = role
  return { object: svgObject, isSvg: true }
}

async function addImageToCanvas(url: string, role: 'background' | 'frame' | 'sticker' | 'upload') {
  const canvas = fabricCanvas.value
  if (!canvas) return
  const { object: img, isSvg } = await loadCanvasAsset(url, role)
  const w = editingTemplate.width
  const h = editingTemplate.height

  if (role === 'background') {
    canvas.getObjects().filter((obj: any) => obj._templateRole === 'background').forEach(obj => canvas.remove(obj))
    img.set({
      left: 0,
      top: 0,
      originX: 'left',
      originY: 'top',
      scaleX: w / (img.width || 1),
      scaleY: h / (img.height || 1),
      lockMovementX: true,
      lockMovementY: true,
      lockScalingX: true,
      lockScalingY: true,
      lockRotation: true,
      hasControls: false,
      hasBorders: false,
      hoverCursor: 'not-allowed',
    })
    ;(img as any)._templateRole = 'background'
    ;(img as any)._isSvg = isSvg
    applyObjectLockState(img, true)
    canvas.add(img)
    canvas.sendObjectToBack(img)
    selectedObject.value = null
  } else {
    const maxW = role === 'frame' ? w : w * 0.35
    const maxH = role === 'frame' ? h : h * 0.35
    const scale = Math.min(maxW / (img.width || 1), maxH / (img.height || 1), 1)
    img.set({
      left: w / 2,
      top: h / 2,
      originX: 'center',
      originY: 'center',
      scaleX: scale,
      scaleY: scale,
      hasControls: true,
      hasBorders: true,
    })
    ;(img as any)._templateRole = role
    ;(img as any)._isSvg = isSvg
    canvas.add(img)
    canvas.setActiveObject(img)
    selectedObject.value = img
  }
  refreshInspectorFromObject()
  canvas.renderAll()
  refreshLayerList()
}

function addText() {
  const canvas = fabricCanvas.value
  if (!canvas) return
  const text = new IText('双击编辑文字', {
    left: editingTemplate.width / 2,
    top: editingTemplate.height / 2,
    originX: 'center',
    originY: 'center',
    fontSize: 60,
    fill: '#111827',
    fontFamily: 'sans-serif',
  }) as any
  text._templateRole = 'text'
  canvas.add(text)
  canvas.setActiveObject(text)
  selectedObject.value = text
  refreshInspectorFromObject()
  canvas.renderAll()
  refreshLayerList()
}

async function openMaterialPicker(type: 'background' | 'frame' | 'sticker') {
  materialType.value = type
  activeMaterialCategory.value = '全部'
  materialModalOpen.value = true
  materialsLoading.value = true
  try {
    materials.value = await fetchAllMaterials(type)
  } catch {
    message.error('加载素材失败')
  } finally {
    materialsLoading.value = false
  }
}

async function fetchAllMaterials(type: 'background' | 'frame' | 'sticker') {
  const pageSize = 200
  let page = 1
  let total = Number.POSITIVE_INFINITY
  const items: DecorationMaterialItem[] = []

  while (items.length < total) {
    const res = await materialApi.listDecorationMaterials(type, true, page, pageSize) as any
    const data = res?.data || {}
    const list = data.items || []
    items.push(...list)
    total = Number(data.total ?? items.length)
    if (!list.length || list.length < pageSize) break
    page += 1
  }

  return items
}

async function selectMaterial(item: DecorationMaterialItem) {
  await addImageToCanvas(item.storage_url, materialType.value)
  materialModalOpen.value = false
}

async function uploadToCanvas(file: File) {
  try {
    const uploadRes = await materialApi.uploadDecorationMaterial(file) as any
    const url = uploadRes?.data?.storage_url || uploadRes?.data?.url
    if (!url) throw new Error('upload url missing')
    await addImageToCanvas(url, materialType.value)
    await materialApi.createDecorationMaterial({
      type: materialType.value,
      name: file.name.replace(/\.[^.]+$/, ''),
      storage_url: url,
      thumbnail_url: url,
      category: '模版编辑上传',
      is_active: true,
      sort_order: 0,
    })
    message.success('素材已添加')
    materialModalOpen.value = false
  } catch {
    message.error('上传素材失败')
  }
  return false
}

function bringForward() {
  const canvas = fabricCanvas.value
  if (!canvas || !selectedObject.value) return
  canvas.bringObjectForward(selectedObject.value)
  canvas.renderAll()
  refreshLayerList()
}

function sendBackward() {
  const canvas = fabricCanvas.value
  if (!canvas || !selectedObject.value) return
  canvas.sendObjectBackwards(selectedObject.value)
  canvas.renderAll()
  refreshLayerList()
}

function bringToFront() {
  const canvas = fabricCanvas.value
  if (!canvas || !selectedObject.value) return
  canvas.bringObjectToFront(selectedObject.value)
  canvas.renderAll()
  refreshLayerList()
}

function sendToBack() {
  const canvas = fabricCanvas.value
  if (!canvas || !selectedObject.value) return
  canvas.sendObjectToBack(selectedObject.value)
  canvas.renderAll()
  refreshLayerList()
}

function toggleLock() {
  const canvas = fabricCanvas.value
  const obj = selectedObject.value as any
  if (!canvas || !obj) return
  const locked = !obj.lockMovementX
  applyObjectLockState(obj, locked)
  obj.setCoords()
  if (locked) {
    canvas.discardActiveObject()
    selectedObject.value = obj
    selectedLocked.value = true
  } else {
    canvas.setActiveObject(obj)
    selectedLocked.value = false
  }
  canvas.requestRenderAll()
  refreshLayerList()
}

function deleteSelected() {
  const canvas = fabricCanvas.value
  if (!canvas || !selectedObject.value) return
  const obj = selectedObject.value as any
  if (obj._templateRole === 'photo-slot' && obj._slotId) {
    editingTemplate.photoSlots = editingTemplate.photoSlots.filter(slot => slot.id !== obj._slotId)
  }
  canvas.remove(selectedObject.value)
  selectedObject.value = null
  selectedLocked.value = false
  selectedSlotId.value = editingTemplate.photoSlots[0]?.id || ''
  ensurePhotoSlotLabels()
  canvas.renderAll()
}

function snapshotCanvasJson() {
  const canvas = fabricCanvas.value
  if (!canvas) return null
  return (canvas as any).toJSON(['_templateRole', '_slotId', '_isSvg', '_lockedAspectRatio', '_locked'])
}

function templateFromSize(size: TemplateSize): PrintTemplateItem {
  return {
    id: `template-${Date.now()}`,
    name: `${size.label} ${createForm.photoCount}张`,
    width: size.width,
    height: size.height,
    paperWidthMm: size.paperWidthMm,
    paperHeightMm: size.paperHeightMm,
    dmPaperSize: '0',
    paperLabel: size.label,
    photoCount: createForm.photoCount,
    sizeKey: size.key,
    photoSlots: generateSlots(createForm.photoCount, size.width, size.height),
  }
}

function applyTemplate(item: PrintTemplateItem) {
  Object.assign(editingTemplate, JSON.parse(JSON.stringify(item)))
  selectedSlotId.value = editingTemplate.photoSlots[0]?.id || ''
}

function serializeTemplateToBase(item: PrintTemplateItem) {
  baseConfig.templateName = item.name
  baseConfig.printConfigMode = 'activity'
  baseConfig.paperKey = item.sizeKey
  baseConfig.dmPaperSize = item.dmPaperSize || '0'
  baseConfig.paperWidthMm = item.paperWidthMm
  baseConfig.paperHeightMm = item.paperHeightMm
  baseConfig.canvasWidth = item.width
  baseConfig.canvasHeight = item.height
  baseConfig.photoSlots = item.photoSlots
  baseConfig.activeTemplateId = item.id
  baseConfig.templates = templates.value
  const first = item.photoSlots[0]
  if (first) baseConfig.photoMargin = Math.max(0, Math.round(Math.min(first.x, first.y)))
}

function clearBaseTemplateConfig() {
  baseConfig.templateName = ''
  baseConfig.paperKey = ''
  baseConfig.dmPaperSize = ''
  baseConfig.canvasWidth = 0
  baseConfig.canvasHeight = 0
  baseConfig.paperWidthMm = 0
  baseConfig.paperHeightMm = 0
  baseConfig.photoSlots = []
  baseConfig.activeTemplateId = ''
  baseConfig.templates = []
  delete baseConfig.canvasJson
}

async function loadTemplates() {
  loading.value = true
  try {
    const res = await request.get(`/settings/${settingKey.value}`)
    const parsed = res.data?.value ? JSON.parse(res.data.value) : null
    if (!parsed) {
      templates.value = []
      activeTemplateId.value = ''
      return
    }
    Object.assign(baseConfig, parsed)
    if (Array.isArray(parsed.templates)) {
      const loaded = parsed.templates
      templates.value = loaded
      activeTemplateId.value = loaded.length ? (parsed.activeTemplateId || loaded[0].id) : ''
      return
    }

    const size = sizeOptions.find(item => item.key === 'square-5')!
    const fallback = templateFromSize(size)
    fallback.id = 'default'
    fallback.name = parsed.templateName || '默认模版'
    fallback.width = Number(parsed.canvasWidth || size.width)
    fallback.height = Number(parsed.canvasHeight || size.height)
    templates.value = [fallback]
    activeTemplateId.value = fallback.id
  } catch {
    templates.value = []
    activeTemplateId.value = ''
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  createModalOpen.value = true
}

async function createTemplate() {
  const size = sizeOptions.find(item => item.key === createForm.sizeKey) || sizeOptions[2]
  const next = templateFromSize(size)
  templates.value.unshift(next)
  activeTemplateId.value = next.id
  applyTemplate(next)
  mode.value = 'editor'
  createModalOpen.value = false
  await initEditorCanvas()
}

async function editTemplate(item: PrintTemplateItem) {
  applyTemplate(item)
  mode.value = 'editor'
  await initEditorCanvas()
}

async function persistTemplates() {
  const active = templates.value.find(item => item.id === activeTemplateId.value) || templates.value[0]
  if (active) {
    serializeTemplateToBase(active)
  } else {
    clearBaseTemplateConfig()
  }
  await request.put(`/settings/${settingKey.value}`, {
    value: JSON.stringify({ ...baseConfig, templates: templates.value, activeTemplateId: activeTemplateId.value }),
  })
}

async function saveEditingTemplate() {
  if (!editingTemplate.name.trim()) {
    message.warning('请输入模版名称')
    return
  }
  saving.value = true
  try {
    const index = templates.value.findIndex(item => item.id === editingTemplate.id)
    const snapshot = JSON.parse(JSON.stringify(editingTemplate)) as PrintTemplateItem
    snapshot.canvasJson = snapshotCanvasJson()
    if (index >= 0) templates.value.splice(index, 1, snapshot)
    else templates.value.unshift(snapshot)
    activeTemplateId.value = snapshot.id
    await persistTemplates()
    message.success('模版已保存')
    disposeCanvas()
    mode.value = 'list'
  } catch {
    message.error('保存模版失败')
  } finally {
    saving.value = false
  }
}

async function setActiveTemplate(item: PrintTemplateItem) {
  activeTemplateId.value = item.id
  try {
    await persistTemplates()
    message.success('已设为当前模版')
  } catch {
    message.error('保存当前模版失败')
  }
}

async function deleteTemplate(id: string) {
  templates.value = templates.value.filter(item => item.id !== id)
  if (activeTemplateId.value === id) activeTemplateId.value = templates.value[0]?.id || ''
  try {
    await persistTemplates()
    message.success('模版已删除')
  } catch {
    message.error('删除模版失败')
  }
}

function backToList() {
  disposeCanvas()
  mode.value = 'list'
}

watch(stageScale, () => {
  if (mode.value === 'editor') {
    initEditorCanvas()
  }
})

onMounted(loadTemplates)
onBeforeUnmount(disposeCanvas)
</script>

<style scoped>
.template-manager {
  background: #f7f8fb;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 18px;
}

.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.panel-toolbar h3 {
  margin: 0;
  font-size: 16px;
}

.panel-toolbar p {
  margin: 4px 0 0;
  color: #8c8c8c;
  font-size: 13px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 14px;
}

.template-card {
  background: #fff;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 14px;
}

.template-card.active {
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.12);
}

.template-preview {
  position: relative;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: linear-gradient(135deg, #fff, #eef6ff);
  color: #64748b;
  font-size: 12px;
}

.template-meta strong,
.template-meta span {
  display: block;
}

.template-meta strong {
  color: #1f2937;
}

.template-meta span {
  margin-top: 2px;
  color: #8c8c8c;
  font-size: 12px;
}

.template-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 12px;
}

.editor-shell {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 320px;
  min-height: 700px;
  background: #eef0f5;
  border-radius: 8px;
  overflow: hidden;
}

.editor-sidebar,
.inspector-panel {
  background: #fff;
  padding: 16px;
}

.editor-sidebar {
  border-right: 1px solid #e5e7eb;
}

.inspector-panel {
  border-left: 1px solid #e5e7eb;
}

.back-link {
  padding-left: 0;
  margin-bottom: 12px;
}

.side-section {
  margin-bottom: 18px;
}

.side-section label,
.side-title {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #1f2937;
}

.template-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.template-facts span {
  border-radius: 12px;
  background: #f1f5f9;
  color: #475569;
  padding: 3px 8px;
  font-size: 12px;
}

.material-actions,
.layer-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 10px;
}

.ratio-actions {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
  margin-top: 12px;
}

.ratio-actions button {
  min-height: 30px;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  background: #fff;
  color: #475569;
  cursor: pointer;
}

.ratio-actions button.active {
  border-color: #1677ff;
  background: #eef6ff;
  color: #1677ff;
  font-weight: 700;
}

.slot-form {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-top: 14px;
}

.property-panel {
  padding: 12px;
  border: 1px solid #eef1f5;
  border-radius: 8px;
  background: #fbfcfe;
}

.property-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.property-panel label span {
  display: block;
  margin-bottom: 4px;
  color: #6b7280;
  font-size: 12px;
}

.inline-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-top: 10px;
}

.color-field {
  width: 100%;
  height: 32px;
  padding: 2px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
}

.margin-form {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #eef1f5;
}

.side-subtitle {
  grid-column: 1 / -1;
  color: #1f2937;
  font-size: 13px;
  font-weight: 700;
}

.slot-form label span,
.margin-form label span {
  display: block;
  margin-bottom: 4px;
  color: #6b7280;
  font-size: 12px;
}

.editor-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  margin-top: 24px;
}

.layer-list-section {
  margin-top: 18px;
}

.layer-list {
  display: grid;
  gap: 6px;
  max-height: 280px;
  overflow-y: auto;
  padding-right: 2px;
}

.layer-list-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 34px;
  padding: 7px 9px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  color: #1f2937;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.16s ease, background 0.16s ease, box-shadow 0.16s ease;
}

.layer-list-item:hover {
  border-color: #93c5fd;
  background: #f8fbff;
}

.layer-list-item.active {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: inset 3px 0 0 #2563eb;
}

.layer-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 600;
}

.layer-role {
  min-width: 44px;
  padding: 2px 6px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 11px;
  line-height: 16px;
  text-align: center;
}

.layer-empty {
  padding: 12px 0 4px;
}

.editor-main {
  position: relative;
  padding: 42px;
  overflow: auto;
}

.canvas-size-label {
  position: absolute;
  top: 14px;
  right: 18px;
  color: #6b7280;
  font-size: 12px;
}

.design-stage-wrap {
  min-height: 620px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.canvas-frame {
  overflow: hidden;
  background: #fff;
  box-shadow: 0 24px 70px rgba(17, 24, 39, 0.18);
}

.create-form {
  display: grid;
  gap: 18px;
}

.create-field > label {
  display: block;
  margin-bottom: 10px;
  font-weight: 700;
}

.size-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.size-card {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fff;
  padding: 12px 8px;
  cursor: pointer;
}

.size-card.active {
  border-color: #ff4d4f;
  box-shadow: 0 0 0 2px rgba(255, 77, 79, 0.12);
}

.size-icon {
  display: block;
  width: 34px;
  height: 24px;
  margin: 0 auto 8px;
  border: 1px solid #64748b;
  border-radius: 3px;
}

.size-icon.portrait {
  width: 24px;
  height: 34px;
}

.size-card strong,
.size-card small {
  display: block;
}

.size-card strong {
  color: #1f2937;
}

.size-card small {
  margin-top: 2px;
  color: #8c8c8c;
}

.material-picker {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 12px;
  max-height: 58vh;
}

.material-modal-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.material-categories {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: auto;
  padding-right: 8px;
  border-right: 1px solid #edf0f5;
}

.material-categories button {
  min-height: 34px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  text-align: left;
}

.material-categories button.active {
  background: #eef6ff;
  color: #1677ff;
  font-weight: 700;
}

.material-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(128px, 1fr));
  gap: 12px;
  overflow: auto;
  padding-right: 4px;
}

.material-item {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fff;
  padding: 8px;
  cursor: pointer;
}

.material-item img {
  width: 100%;
  height: 120px;
  object-fit: contain;
  background: #f8fafc;
  border-radius: 6px;
}

.material-item span {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  color: #475569;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 980px) {
  .editor-shell {
    grid-template-columns: 1fr;
  }

  .editor-sidebar {
    border-right: 0;
    border-bottom: 1px solid #e5e7eb;
  }

  .inspector-panel {
    border-left: 0;
    border-top: 1px solid #e5e7eb;
  }

  .size-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .material-picker {
    grid-template-columns: 1fr;
  }

  .material-categories {
    flex-direction: row;
    border-right: 0;
    border-bottom: 1px solid #edf0f5;
    padding-right: 0;
    padding-bottom: 8px;
  }
}
</style>
