<template>
  <div class="photo-editor">
    <!-- 椤堕儴鏍?-->
    <div class="editor-header">
      <button class="back-btn" @click="handleBack">
        <ChevronLeft :size="22" />
      </button>
      <span class="header-title">照片编辑器</span>
      <div class="header-actions">
        <button class="header-pill-btn download-pill" @click="handleDownload">
          <Download :size="15" />
          <span>下载</span>
        </button>
        <button class="header-pill-btn print-pill" :class="{ loading: printing }" @click="handlePrint">
          <Printer :size="15" />
          <span>打印</span>
        </button>
      </div>
    </div>

    <!-- 鐢诲竷鍖哄煙 -->
    <div class="canvas-container" ref="containerRef">
      <div class="canvas-wrapper" :style="canvasWrapperStyle">
        <canvas ref="canvasRef" />
      </div>

      <!-- 閫変腑瀵硅薄娴姩鎺т欢 -->
      <div v-if="selectedObject" class="obj-ctrl-bar">
        <button class="obj-ctrl-btn" @click="centerObjectH()" title="水平居中">
          <MoveHorizontal :size="16" />
        </button>
        <button class="obj-ctrl-btn" @click="centerObjectV()" title="垂直居中">
          <MoveVertical :size="16" />
        </button>
        <button class="obj-ctrl-btn" @click="centerObjectBoth()" title="中心居中">
          <Crosshair :size="16" />
        </button>
        <button class="obj-ctrl-btn" :class="{ locked: isObjLocked }" @click="handleToggleLock" :title="isObjLocked ? '解锁' : '锁定'">
          <Lock :size="16" v-if="isObjLocked" />
          <Unlock :size="16" v-else />
        </button>
        <button v-if="isMainPhoto" class="obj-ctrl-btn reset-btn" @click="resetPhotoPosition()" title="自动调整位置">
          <RotateCcw :size="16" />
        </button>
        <div v-if="isMainPhoto" class="margin-ctrl">
          <label>边距</label>
          <input type="number" class="margin-input" v-model.number="photoMarginVal" min="0" max="500" @change="onMarginChange" @input="onMarginInput" />
          <span>px</span>
        </div>
        <button v-if="isMainPhoto" class="obj-ctrl-btn" :class="{ active: isBgRemoved }" @click="handleRemoveBg" :disabled="removingBg" :title="isBgRemoved ? '恢复背景' : '去除背景'">
          <Eraser :size="16" />
        </button>
        <button v-if="isCropTarget" class="obj-ctrl-btn crop-btn" :class="{ active: cropPanelVisible }" @click="toggleCropPanel" title="裁剪">
          <Crop :size="16" />
        </button>
        <button v-if="isSvgTarget" class="obj-ctrl-btn color-btn" :class="{ active: svgColorPanelVisible }" @click="toggleSvgColorPanel" title="SVG 改色">
          <Palette :size="16" />
        </button>
        <div class="obj-ctrl-divider" />
        <button class="obj-ctrl-btn danger" @click="deleteSelected()" title="删除">
          <Trash2 :size="16" />
        </button>
      </div>

      <div v-if="cropPanelVisible && isCropTarget" class="crop-panel">
        <div class="crop-panel-head">
          <span><Crop :size="15" /> 裁剪</span>
          <div class="crop-actions">
            <button type="button" @click="resetCrop">
              <RotateCcw :size="14" />
              <span>重置</span>
            </button>
            <button type="button" class="primary" @click="finishCrop">
              <Check :size="14" />
              <span>完成</span>
            </button>
          </div>
        </div>
        <div class="crop-grid">
          <label v-for="field in cropFields" :key="field.key" class="crop-field">
            <span>{{ field.label }} {{ cropState[field.key] }}%</span>
            <input
              v-model.number="cropState[field.key]"
              type="range"
              min="0"
              max="80"
              step="1"
              @input="onCropInput(field.key)"
            />
          </label>
        </div>
      </div>

      <div v-if="svgColorPanelVisible && isSvgTarget" class="svg-color-panel">
        <div class="svg-color-head">
          <span><Palette :size="15" /> SVG 颜色</span>
          <input v-model="svgColor" type="color" @input="onSvgColorInput" />
        </div>
        <div class="svg-color-swatches">
          <button
            v-for="color in svgColorSwatches"
            :key="color"
            type="button"
            :class="{ active: svgColor.toLowerCase() === color.toLowerCase() }"
            :style="{ backgroundColor: color }"
            @click="setSvgColor(color)"
          />
        </div>
      </div>
    </div>

    <!-- 搴曢儴宸ュ叿鏍?-->
    <CanvasToolbar
      :has-selection="!!selectedObject"
      @add-background="showMaterialPanel('background')"
      @add-frame="showMaterialPanel('frame')"
      @add-sticker="showMaterialPanel('sticker')"
      @add-text="showTextPanel"
      @layer-forward="handleLayerForward"
      @layer-backward="handleLayerBackward"
      @edit-selected="handleEditSelected"
      @upload-image="triggerUploadImage"
      @unlock-all="handleUnlockAll"
    />

    <input
      ref="uploadInputRef"
      class="upload-input"
      type="file"
      accept="image/*"
      @change="handleUploadImage"
    />

    <!-- 绱犳潗閫夋嫨闈㈡澘 -->
    <MaterialPanel
      :visible="materialPanelVisible"
      :material-type="materialPanelType"
      @select="handleMaterialSelect"
      @close="materialPanelVisible = false"
    />

    <!-- 鏂囧瓧缂栬緫闈㈡澘 -->
    <TextEditorPanel
      :visible="textPanelVisible"
      :initial-text="editingText"
      :initial-style="editingTextStyle"
      @confirm="handleTextConfirm"
      @preview="handleTextPreview"
      @close="handleTextPanelClose"
    />

    <!-- 鎵撳嵃纭寮圭獥 -->
    <a-modal
      v-model:open="printModalVisible"
      title="确认打印"
      :confirm-loading="printing"
      ok-text="确认打印"
      cancel-text="取消"
      @ok="confirmPrint"
    >
      <div class="print-confirm-content">
        <p v-if="quotaInfo">
          <span v-if="quotaInfo.remaining > 0" style="color: #52c41a">
            您还有 {{ quotaInfo.remaining }} 次免费打印额度
          </span>
          <span v-else style="color: #ff4d4f">
            免费额度已用完，本次打印将使用付费通道
          </span>
        </p>
        <p>是否确认打印当前作品？</p>
      </div>
    </a-modal>

    <!-- 鍏ㄥ眬鍔犺浇 -->
    <a-modal v-model:open="loadingModal" :footer="null" centered :mask-closable="false">
      <div class="loading-content">
        <a-spin size="large" />
        <p>{{ loadingText }}</p>
      </div>
    </a-modal>

    <!-- 鍘熷浘棰勮寮圭獥锛堝井淇′腑闀挎寜淇濆瓨锛?-->
    <a-modal v-model:open="downloadPreviewVisible" title="保存原图" :footer="null" centered>
      <div class="download-preview">
        <img :src="downloadPreviewUrl" alt="原图" class="download-preview-img" />
        <p class="download-tip">长按原图即可保存到手机相册</p>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { ChevronLeft, Download, Printer, MoveHorizontal, MoveVertical, Crosshair, Lock, Unlock, RotateCcw, Trash2, Eraser, Crop, Check, Palette } from 'lucide-vue-next'
import { FabricImage, FabricObject, Rect } from 'fabric'
import CanvasToolbar from '@/components/CanvasToolbar.vue'
import MaterialPanel, { type MaterialItem } from './MaterialPanel.vue'
import TextEditorPanel, { type TextStyle } from './TextEditorPanel.vue'
import { useCanvasEditor, type ImageCropState } from '@/composables/useCanvasEditor'
import { publicApi, publicApi2 } from '@/api/admin'
import type { CanvasPrintResponse, WechatPayParams, WechatProfile } from '@/api/admin'

declare global {
  interface Window {
    WeixinJSBridge?: {
      invoke: (
        name: string,
        params: WechatPayParams,
        callback: (res: { err_msg?: string }) => void
      ) => void
    }
  }
}

FabricObject.customProperties = ['_templateRole', '_slotId', '_isSvg', '_lockedAspectRatio', '_locked']

type EditorPhotoItem = { id: number; url: string }
type PrintPhotoSlot = { id: string; x: number; y: number; width: number; height: number }

// Props
const props = defineProps<{
  photoUrl: string
  photoId: number
  photos?: EditorPhotoItem[]
  programToken: string
  activityId: number
  wechatProfile?: WechatProfile | null
  canvasWidth?: number
  canvasHeight?: number
  photoInitX?: number
  photoInitY?: number
  photoInitScale?: number
  photoMargin?: number
  templateName?: string
  paperSize?: string | null
  photoSlots?: PrintPhotoSlot[]
  templateCanvasJson?: any
}>()

const emit = defineEmits<{
  back: []
}>()

// Canvas refs
const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)
const uploadInputRef = ref<HTMLInputElement | null>(null)

// 鐢诲竷閫昏緫灏哄锛堝唴閮ㄧ粯鍒跺垎杈ㄧ巼锛?
const logicalWidth = props.canvasWidth || 800
const logicalHeight = props.canvasHeight || 600

// 鐓х墖鍒濆浣嶇疆锛堢櫨鍒嗘瘮 0~100锛?
const photoInitX = props.photoInitX ?? 50
const photoInitY = props.photoInitY ?? 50
const photoInitScale = props.photoInitScale ?? 100
const photoMargin = props.photoMargin ?? 20

// 鐢诲竷鏄剧ず缂╂斁姣旓紙閫傞厤灞忓箷锛?
const displayScale = ref(1)

// 璁＄畻鐢诲竷鍦ㄥ睆骞曚腑鐨勬樉绀哄昂瀵?
const canvasWrapperStyle = computed(() => {
  const w = Math.round(logicalWidth * displayScale.value)
  const h = Math.round(logicalHeight * displayScale.value)
  return {
    width: `${w}px`,
    height: `${h}px`,
  }
})

// 閫変腑瀵硅薄鐘舵€?
const isObjLocked = computed(() => isSelectedLocked())
const isMainPhoto = computed(() => isSelectedMainPhoto())
const isCropTarget = computed(() => isSelectedCropTarget())
const isSvgTarget = computed(() => isSelectedSvgTarget())

// 鏍规嵁灞忓箷灏哄璁＄畻鐢诲竷缂╂斁姣旓紝浣挎渶闀胯竟瀹屽叏鏄剧ず
function calcDisplayScale() {
  const headerH = 48
  const toolbarH = 68
  const padding = 8
  const availW = window.innerWidth - padding * 2
  const availH = window.innerHeight - headerH - toolbarH - padding * 2

  const scaleX = availW / logicalWidth
  const scaleY = availH / logicalHeight

  // 鍙栬緝灏忓€硷紝纭繚鏈€闀胯竟瀹屽叏鍙
  displayScale.value = Math.min(scaleX, scaleY, 1)
}

// Editor state
const printing = ref(false)
const loadingModal = ref(false)
const loadingText = ref('')

// Material panel
const materialPanelVisible = ref(false)
const materialPanelType = ref<'background' | 'frame' | 'sticker'>('background')

// Text panel
const textPanelVisible = ref(false)
const editingText = ref('点击编辑文字')
const editingTextStyle = ref<Partial<TextStyle>>({})
const editingObject = ref<any>(null)

// 鐓х墖杈硅窛
const photoMarginVal = ref(photoMargin)

// 鎶犲浘鐘舵€?
const removingBg = ref(false)
const isBgRemoved = ref(false)
let originalImageDataUrl: string | null = null  // 淇濆瓨鍘熷鍥剧墖 dataUrl

// Print modal
const printModalVisible = ref(false)
const quotaInfo = ref<{ free_quota: number; used_count: number; remaining: number; price: number; pay_enabled: boolean } | null>(null)

// Canvas editor
const {
  initCanvas,
  addImage,
  addBackground,
  addText,
  deleteSelected,
  cloneSelected,
  exportJSON,
  exportImage,
  loadFromJSON,
  clearCanvas,
  updateSelectedStyle,
  zoomCanvas,
  resetZoom,
  updateViewport,
  getSelectedType,
  selectedObject,
  fabricCanvas,
  dispose,
  onObjectDoubleClick,
  centerObjectH,
  centerObjectV,
  centerObjectBoth,
  toggleLockObject,
  unlockAllObjects,
  bringSelectedForward,
  sendSelectedBackward,
  isSelectedLocked,
  isSelectedMainPhoto,
  isSelectedCropTarget,
  isSelectedSvgTarget,
  getSelectedSvgColor,
  applySelectedSvgColor,
  getSelectedCropState,
  applySelectedImageCrop,
  resetSelectedImageCrop,
  resetPhotoPosition,
  resetPhotoPositionWithMargin,
} = useCanvasEditor()

type CropKey = keyof ImageCropState
const cropPanelVisible = ref(false)
const cropState = ref<ImageCropState>({ left: 0, right: 0, top: 0, bottom: 0 })
const cropFields: Array<{ key: CropKey; label: string }> = [
  { key: 'left', label: 'Left' },
  { key: 'right', label: 'Right' },
  { key: 'top', label: 'Top' },
  { key: 'bottom', label: 'Bottom' },
]
const svgColorPanelVisible = ref(false)
const svgColor = ref('#111827')
const svgColorSwatches = ['#111827', '#ffffff', '#ef4444', '#f97316', '#f59e0b', '#22c55e', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899']

function editorPhotos(): EditorPhotoItem[] {
  const list = Array.isArray(props.photos) ? props.photos.filter(item => item.url) : []
  if (list.length) return list
  return props.photoUrl ? [{ id: props.photoId, url: props.photoUrl }] : []
}

function sortSlots(slots: PrintPhotoSlot[]) {
  return [...slots].sort((a, b) => {
    const aNum = Number(String(a.id || '').match(/\d+$/)?.[0] || 0)
    const bNum = Number(String(b.id || '').match(/\d+$/)?.[0] || 0)
    return aNum - bNum
  })
}

function collectTemplateSlotsFromCanvas(): PrintPhotoSlot[] {
  const canvas = fabricCanvas.value
  if (!canvas) return []
  return canvas.getObjects()
    .filter((obj: any) => isSlotGuideObject(obj))
    .map((obj: any, index) => ({
      id: obj._slotId || `photo-${index + 1}`,
      x: Math.round(Number(obj.left || 0)),
      y: Math.round(Number(obj.top || 0)),
      width: Math.round(Number(obj.width || 0) * Number(obj.scaleX || 1)),
      height: Math.round(Number(obj.height || 0) * Number(obj.scaleY || 1)),
    }))
}

function templateSlotIndexes() {
  const indexes: Record<string, number> = {}
  const canvas = fabricCanvas.value
  if (!canvas) return indexes
  canvas.getObjects().forEach((obj: any, index) => {
    if (obj._templateRole === 'photo-slot' && obj._slotId) {
      indexes[obj._slotId] = index
      return
    }
    const matched = matchObjectToSlot(obj)
    if (matched) {
      indexes[matched.id] = index
    }
  })
  return indexes
}

function removeTemplateSlotGuides() {
  const canvas = fabricCanvas.value
  if (!canvas) return
  canvas.getObjects()
    .filter((obj: any) => isSlotGuideObject(obj) || isSlotLabelObject(obj))
    .forEach(obj => canvas.remove(obj))
  canvas.discardActiveObject()
}

function normalizeTemplateAssetUrl(src: string) {
  if (!src) return src
  try {
    const url = new URL(src, window.location.origin)
    if (['localhost', '127.0.0.1', '0.0.0.0'].includes(url.hostname)) {
      return `${window.location.origin}${url.pathname}${url.search}${url.hash}`
    }
    return url.href
  } catch {
    return src
  }
}

function withTemplateImageOptions(source: any): any {
  const cloned = JSON.parse(JSON.stringify(source))
  const visit = (item: any) => {
    if (!item || typeof item !== 'object') return
    if (String(item.type || '').toLowerCase() === 'image' && item.src) {
      item.src = normalizeTemplateAssetUrl(item.src)
      item.crossOrigin = item.crossOrigin || 'anonymous'
    }
    const children = item.objects || item._objects
    if (Array.isArray(children)) children.forEach(visit)
  }
  if (Array.isArray(cloned.objects)) cloned.objects.forEach(visit)
  return cloned
}

function objectBox(obj: any) {
  return {
    left: Number(obj.left || 0),
    top: Number(obj.top || 0),
    width: Number(obj.width || 0) * Number(obj.scaleX || 1),
    height: Number(obj.height || 0) * Number(obj.scaleY || 1),
  }
}

function matchObjectToSlot(obj: any) {
  const slots = Array.isArray(props.photoSlots) ? props.photoSlots : []
  if (!slots.length || !obj) return null
  const box = objectBox(obj)
  const tolerance = Math.max(8, Math.min(logicalWidth, logicalHeight) * 0.015)
  return slots.find(slot =>
    Math.abs(box.left - slot.x) <= tolerance &&
    Math.abs(box.top - slot.y) <= tolerance &&
    Math.abs(box.width - slot.width) <= tolerance &&
    Math.abs(box.height - slot.height) <= tolerance
  ) || null
}

function isSlotGuideObject(obj: any) {
  if (!obj) return false
  if (obj._templateRole === 'photo-slot') return true
  if (String(obj.type || '').toLowerCase() !== 'rect') return false
  return !!matchObjectToSlot(obj)
}

function isSlotLabelObject(obj: any) {
  if (!obj) return false
  if (obj._templateRole === 'photo-label') return true
  const type = String(obj.type || '').toLowerCase()
  if (!type.includes('text')) return false
  const fill = String(obj.fill || '').toLowerCase()
  const text = String(obj.text || '')
  if (fill !== '#ff6b35' && !/照片|\?\?/.test(text)) return false
  const box = objectBox(obj)
  const slots = Array.isArray(props.photoSlots) ? props.photoSlots : []
  return slots.some(slot =>
    box.left >= slot.x - 20 &&
    box.top >= slot.y - 20 &&
    box.left <= slot.x + Math.max(160, slot.width * 0.35) &&
    box.top <= slot.y + Math.max(120, slot.height * 0.35)
  )
}

function restoreTemplateOverlays() {
  const canvas = fabricCanvas.value
  if (!canvas) return
  canvas.getObjects()
    .filter((obj: any) => ['frame', 'sticker', 'upload', 'text', 'svg'].includes(obj._templateRole))
    .forEach(obj => canvas.bringObjectToFront(obj))
}

async function addPhotoToSlot(photo: EditorPhotoItem, slot: PrintPhotoSlot, index: number, layerIndex?: number) {
  const canvas = fabricCanvas.value
  if (!canvas || !photo.url || !slot.width || !slot.height) return null
  const img = await FabricImage.fromURL(photo.url, { crossOrigin: 'anonymous' })
  const scale = Math.max(slot.width / (img.width || 1), slot.height / (img.height || 1))
  const clipPath = new Rect({
    left: slot.x,
    top: slot.y,
    width: slot.width,
    height: slot.height,
    originX: 'left',
    originY: 'top',
    absolutePositioned: true,
  } as any)
  img.set({
    left: slot.x + slot.width / 2,
    top: slot.y + slot.height / 2,
    originX: 'center',
    originY: 'center',
    scaleX: scale,
    scaleY: scale,
    clipPath,
    selectable: true,
    hasControls: true,
    hasBorders: true,
  })
  ;(img as any)._isEditablePhoto = true
  ;(img as any)._templateSlotId = slot.id
  ;(img as any)._slotPhotoIndex = index
  canvas.add(img)
  if (layerIndex !== undefined) {
    canvas.moveObjectTo(img, Math.min(layerIndex, canvas.getObjects().length - 1))
  }
  img.setCoords()
  return img
}

async function applyTemplatePhotos() {
  const photos = editorPhotos()
  if (!photos.length) return false

  if (props.templateCanvasJson) {
    await loadFromJSON(withTemplateImageOptions(props.templateCanvasJson))
  }

  const slots = sortSlots(
    Array.isArray(props.photoSlots) && props.photoSlots.length
      ? props.photoSlots
      : collectTemplateSlotsFromCanvas()
  )

  if (!slots.length) {
    await addImage(photos[0].url, {
      selectable: true,
      hasControls: true,
      hasBorders: true,
    }, 'contain', { initX: photoInitX, initY: photoInitY, initScale: photoInitScale, margin: photoMargin })
    return true
  }

  const slotIndexes = templateSlotIndexes()
  removeTemplateSlotGuides()
  const inserted: any[] = []
  for (const [index, photo] of photos.slice(0, slots.length).entries()) {
    const insertedPhoto = await addPhotoToSlot(photo, slots[index], index, slotIndexes[slots[index].id])
    if (insertedPhoto) inserted.push(insertedPhoto)
  }
  if (inserted[0] && fabricCanvas.value) {
    fabricCanvas.value.setActiveObject(inserted[0])
  }
  restoreTemplateOverlays()
  fabricCanvas.value?.renderAll()
  return true
}

async function init() {
  loadingText.value = '正在加载编辑器...'
  loadingModal.value = true

  // 鍏堣绠楃敾甯冩樉绀虹缉鏀?
  calcDisplayScale()

  if (canvasRef.value) {
    // 浣跨敤閫昏緫灏哄鍒濆鍖栫敾甯冿紝浼犲叆 displayScale 璁?setZoom 澶勭悊缂╂斁
    initCanvas(canvasRef.value, { width: logicalWidth, height: logicalHeight, backgroundColor: '#ffffff' }, displayScale.value)

    // 娉ㄥ唽鍙屽嚮瀵硅薄鍥炶皟 - 鍙屽嚮鏂囧瓧寮瑰嚭缂栬緫闈㈡澘
    onObjectDoubleClick((obj: any) => {
      const type = obj?.type
      if (type === 'i-text' || type === 'text' || type === 'textbox') {
        editingObject.value = obj
        editingText.value = obj.text || ''
        editingTextStyle.value = {
          fontFamily: obj.fontFamily,
          fontSize: obj.fontSize,
          fill: obj.fill,
          fontWeight: obj.fontWeight,
          fontStyle: obj.fontStyle,
        }
        textPanelVisible.value = true
      }
    })

    try {
      // 涓荤収鐗囦娇鐢?contain 妯″紡锛屾寜鎵撳嵃妯℃澘閰嶇疆鐨勫垵濮嬩綅缃拰缂╂斁
      await applyTemplatePhotos()
    } catch (e) {
      console.error('load print template failed:', e)
      message.error('照片加载失败')
    }
  }

  loadingModal.value = false
}

function handleBack() { emit('back') }

function showMaterialPanel(type: 'background' | 'frame' | 'sticker') {
  materialPanelType.value = type
  materialPanelVisible.value = true
}

function showTextPanel() {
  // 鐐瑰嚮"鏂囧瓧"鎸夐挳鐩存帴鍦ㄧ敾甯冧笂娣诲姞榛樿鏂囧瓧
  const textObj = addText('点击编辑文字', {
    fontFamily: 'sans-serif',
    fontSize: 48,
    fill: '#333333',
  })
  if (textObj) {
    message.info('双击文字可编辑内容和样式')
  } else {
    message.error('添加文字失败')
  }
}

function handleMaterialSelect(item: MaterialItem) {
  const url = item.storage_url

  if (item.type === 'background') {
    addBackground(url)
  } else {
    // 瑁呴グ/鐩告浣跨敤 fit 妯″紡
    addImage(url, { hasControls: true, hasBorders: true }, 'fit')
  }
  materialPanelVisible.value = false
  message.success(`已添加${item.type === 'frame' ? '相框' : '装饰'}`)
}

function handleTextConfirm(style: TextStyle) {
  textPanelVisible.value = false
  if (editingObject.value) {
    editingObject.value.set({ text: style.text, fontFamily: style.fontFamily, fontSize: style.fontSize, fill: style.fill, fontWeight: style.fontWeight, fontStyle: style.fontStyle })
    if (fabricCanvas.value) fabricCanvas.value.renderAll()
  } else {
    addText(style.text, style)
  }
}

function handleTextPreview(style: TextStyle) {
  if (editingObject.value) {
    editingObject.value.set({ text: style.text, fontFamily: style.fontFamily, fontSize: style.fontSize, fill: style.fill, fontWeight: style.fontWeight, fontStyle: style.fontStyle })
    if (fabricCanvas.value) fabricCanvas.value.renderAll()
  }
}

function handleTextPanelClose() {
  textPanelVisible.value = false
  editingObject.value = null
}

function handleDelete() { deleteSelected() }
function handleToggleLock() {
  const locked = toggleLockObject()
  message.info(locked ? '已锁定对象' : '已解锁对象')
}

function handleUnlockAll() {
  const count = unlockAllObjects()
  message.success(count > 0 ? `已解锁 ${count} 个图层元素` : '当前没有锁定的图层元素')
}

function onMarginChange() {
  const val = Math.max(0, Math.min(500, photoMarginVal.value || 0))
  photoMarginVal.value = val
  resetPhotoPositionWithMargin(val)
}

function onMarginInput() {
  // 瀹炴椂棰勮杈硅窛鍙樺寲
  const val = Math.max(0, Math.min(500, photoMarginVal.value || 0))
  resetPhotoPositionWithMargin(val)
}

// 鎶犲浘/鎭㈠鑳屾櫙
let removedBgDataUrlCache: string | null = null  // 缂撳瓨鎶犲浘缁撴灉锛岄伩鍏嶉噸澶嶈姹?

async function handleRemoveBg() {
  if (removingBg.value) return

  const obj = selectedObject.value as any
  if (!obj || !obj._isMainPhoto) return

  const cvs = fabricCanvas.value
  if (!cvs) return

  // 濡傛灉宸茬粡鎶犺繃鍥撅紝鎭㈠鍘熷浘
  if (isBgRemoved.value) {
    if (originalImageDataUrl) {
      obj.setSrc(originalImageDataUrl, () => {
        cvs.renderAll()
        isBgRemoved.value = false
        message.success('已恢复原图')
      })
    }
    return
  }

  // 寮€濮嬫姞鍥?
  removingBg.value = true
  try {
    // 淇濆瓨鍘熷鍥剧墖 dataUrl锛堜粠鍏冪礌鑾峰彇锛?
    const imgEl = obj.getElement() as HTMLImageElement
    if (!imgEl) {
      message.error('无法获取图片')
      return
    }
    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = imgEl.naturalWidth || imgEl.width
    tempCanvas.height = imgEl.naturalHeight || imgEl.height
    const tempCtx = tempCanvas.getContext('2d')!
    tempCtx.drawImage(imgEl, 0, 0)
    originalImageDataUrl = tempCanvas.toDataURL('image/png')

    // 璋冪敤鏈嶅姟绔?API 鎶犻櫎鑳屾櫙
    let resultDataUrl: string

    if (removedBgDataUrlCache) {
      // 鏈夌紦瀛橈紝鐩存帴浣跨敤
      resultDataUrl = removedBgDataUrlCache
    } else {
      // 鐢ㄥ師濮嬬収鐗?URL 璋冪敤鏈嶅姟绔姞鍥?API
      loadingText.value = '正在抠图，请稍候...'
      loadingModal.value = true

      const resp = await fetch('/api/public/image/remove-bg', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_url: props.photoUrl }),
      })

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}))
        throw new Error(errData.detail || `请求失败 (${resp.status})`)
      }

      const blob = await resp.blob()
      resultDataUrl = await blobToDataUrl(blob)
      removedBgDataUrlCache = resultDataUrl
    }

    // 鏇挎崲 fabric 鍥剧墖婧?
    obj.setSrc(resultDataUrl, () => {
      cvs.renderAll()
      isBgRemoved.value = true
      message.success('已去除背景')
    })
  } catch (e: any) {
    console.error('抠图失败:', e)
    message.error(e.message || '抠图失败，请重试')
  } finally {
    removingBg.value = false
    loadingModal.value = false
  }
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

function syncCropState() {
  cropState.value = getSelectedCropState()
}

function toggleCropPanel() {
  if (!isCropTarget.value) return
  if (!cropPanelVisible.value) syncCropState()
  svgColorPanelVisible.value = false
  cropPanelVisible.value = !cropPanelVisible.value
}

function onCropInput(key: CropKey) {
  const state = cropState.value
  const pair: Record<CropKey, CropKey> = { left: 'right', right: 'left', top: 'bottom', bottom: 'top' }
  const other = pair[key]
  const maxTotal = 90
  state[key] = Math.max(0, Math.min(80, Number(state[key] || 0)))
  if (state[key] + state[other] > maxTotal) {
    state[other] = Math.max(0, maxTotal - state[key])
  }
  applySelectedImageCrop({ ...state })
}

function resetCrop() {
  resetSelectedImageCrop()
  syncCropState()
}

function finishCrop() {
  cropPanelVisible.value = false
}

function syncSvgColor() {
  svgColor.value = getSelectedSvgColor()
}

function toggleSvgColorPanel() {
  if (!isSvgTarget.value) return
  if (!svgColorPanelVisible.value) syncSvgColor()
  cropPanelVisible.value = false
  svgColorPanelVisible.value = !svgColorPanelVisible.value
}

async function setSvgColor(color: string) {
  svgColor.value = color
  try {
    await applySelectedSvgColor(color)
  } catch {
    message.error('SVG 改色失败')
  }
}

function onSvgColorInput() {
  void setSvgColor(svgColor.value)
}

function triggerUploadImage() {
  uploadInputRef.value?.click()
}

async function handleUploadImage(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''

  if (!file) return
  if (!file.type.startsWith('image/')) {
    message.warning('请选择图片文件')
    return
  }
  if (file.size > 15 * 1024 * 1024) {
    message.warning('图片不能超过 15MB')
    return
  }

  loadingText.value = '正在添加图片...'
  loadingModal.value = true
  try {
    const dataUrl = await blobToDataUrl(file)
    await addImage(dataUrl, { hasControls: true, hasBorders: true, _isEditablePhoto: true }, 'fit')
    message.success('图片已添加到画布')
  } catch (e) {
    message.error('上传图片失败，请重试')
  } finally {
    loadingModal.value = false
  }
}

function handleLayerForward() {
  if (!bringSelectedForward()) message.info('已经在最上层')
}

function handleLayerBackward() {
  if (!sendSelectedBackward()) message.info('已经在最下层')
}

function handleEditSelected() {
  const type = getSelectedType()
  const obj = selectedObject.value as any
  if (type === 'i-text' || type === 'text' || type === 'textbox') {
    editingObject.value = selectedObject.value
    editingText.value = obj?.text || ''
    editingTextStyle.value = {
      fontFamily: obj?.fontFamily,
      fontSize: obj?.fontSize,
      fill: obj?.fill,
      fontWeight: obj?.fontWeight,
      fontStyle: obj?.fontStyle,
    }
    textPanelVisible.value = true
  } else if (type === 'image') {
    message.info('双指缩放可调整图片大小')
  } else {
    message.info('该对象不支持编辑')
  }
}

// 涓嬭浇棰勮
const downloadPreviewVisible = ref(false)
const downloadPreviewUrl = ref('')

// 涓嬭浇鍘熷浘
async function handleDownload() {
  try {
    if (!props.photoUrl) {
      message.error('原图地址不存在')
      return
    }

    downloadPreviewUrl.value = props.photoUrl
    downloadPreviewVisible.value = true

    // 璁板綍涓嬭浇
    if (props.wechatProfile?.openid) {
      publicApi2.createDownloadRecord(props.photoId, props.wechatProfile.openid, props.wechatProfile.nickname ?? undefined).catch(() => {})
    }
  } catch (e: any) {
    message.error('下载失败，请重试')
  }
}

// Print
async function handlePrint() {
  printModalVisible.value = true
  if (props.wechatProfile?.openid) {
    try {
      quotaInfo.value = (await publicApi2.checkPrintQuota(props.activityId, props.wechatProfile.openid) as any)?.data
    } catch { quotaInfo.value = null }
  }
}

function waitForWeixinBridge() {
  return new Promise<void>((resolve, reject) => {
    if (window.WeixinJSBridge) {
      resolve()
      return
    }
    const timer = window.setTimeout(() => {
      document.removeEventListener('WeixinJSBridgeReady', onReady)
      reject(new Error('请在微信内打开页面后再支付'))
    }, 5000)
    function onReady() {
      window.clearTimeout(timer)
      resolve()
    }
    document.addEventListener('WeixinJSBridgeReady', onReady, { once: true })
  })
}

async function requestWechatPay(params: WechatPayParams) {
  await waitForWeixinBridge()
  return new Promise<void>((resolve, reject) => {
    window.WeixinJSBridge!.invoke('getBrandWCPayRequest', params, (res) => {
      const result = String(res.err_msg || '')
      if (result.endsWith(':ok')) {
        resolve()
      } else if (result.endsWith(':cancel')) {
        reject(new Error('支付已取消'))
      } else {
        reject(new Error(result || '微信支付失败'))
      }
    })
  })
}

async function confirmPrint() {
  printing.value = true
  try {
    const canvasImage = exportImage()
    const canvasJson = exportJSON()
    const res = await publicApi2.canvasPrint(
      props.programToken, props.photoId, {
        copies: 1,
        openid: props.wechatProfile?.openid ?? undefined,
        nickname: props.wechatProfile?.nickname ?? undefined,
        canvas_json: canvasJson ?? undefined,
        canvas_image: canvasImage ?? undefined,
        canvas_width: logicalWidth,
        canvas_height: logicalHeight,
        paper_size: props.paperSize || undefined,
        template_name: props.templateName || '照片编辑器模板',
      }
    ) as any
    const resData = (res?.data || res) as CanvasPrintResponse
    printModalVisible.value = false
    if (resData.payment_status === 'free') {
      message.success('打印任务已提交，免费打印')
    } else if (resData.payment_status === 'pending') {
      if (!resData.pay_params) {
        message.error('支付参数缺失，请联系现场工作人员')
        return
      }
      await requestWechatPay(resData.pay_params)
      message.success('支付成功，打印任务已提交')
    } else {
      message.info('打印任务已提交')
    }
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '打印失败，请重试')
  } finally {
    printing.value = false
  }
}

// 绐楀彛灏哄鍙樺寲鏃堕噸鏂拌绠?
function handleResize() {
  calcDisplayScale()
  updateViewport(displayScale.value)
}

onMounted(() => {
  init()
  window.addEventListener('resize', handleResize)
})
watch(selectedObject, () => {
  if (!isCropTarget.value) {
    cropPanelVisible.value = false
    cropState.value = { left: 0, right: 0, top: 0, bottom: 0 }
  } else {
    syncCropState()
  }
  if (!isSvgTarget.value) {
    svgColorPanelVisible.value = false
    svgColor.value = '#111827'
  } else {
    syncSvgColor()
  }
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  dispose()
})
</script>

<style scoped>
.photo-editor {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
  z-index: 200;
}

.editor-header {
  height: 48px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  padding: 0 8px;
  flex-shrink: 0;
  z-index: 10;
}

.back-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  display: flex;
  color: #333;
}

.back-btn:hover {
  background: #f0f0f0;
}

.header-title {
  flex: 1;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.header-action-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
}

.header-pill-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
  white-space: nowrap;
}

.download-pill {
  background: rgba(0, 0, 0, 0.06);
  color: #333;
}

.download-pill:active {
  background: rgba(0, 0, 0, 0.12);
}

.print-pill {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.print-pill:active {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
}

.print-pill.loading {
  opacity: 0.7;
  pointer-events: none;
}

.canvas-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  position: relative;
}

.canvas-wrapper {
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  overflow: hidden;
}

.canvas-wrapper canvas {
  display: block;
}

/* 鈹€鈹€ 閫変腑瀵硅薄娴姩鎺т欢 鈹€鈹€ */
.obj-ctrl-bar {
  position: absolute;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 2px;
  background: rgba(30, 30, 46, 0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 4px 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  z-index: 50;
}

.obj-ctrl-btn {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 50%;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.75);
  transition: all 0.15s ease;
  -webkit-tap-highlight-color: transparent;
}

.obj-ctrl-btn:active {
  background: rgba(99, 102, 241, 0.3);
  color: #818cf8;
}

.obj-ctrl-btn.locked {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
}

.obj-ctrl-btn.reset-btn {
  color: rgba(56, 189, 248, 0.9);
}

.obj-ctrl-btn.reset-btn:active {
  background: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
}

.obj-ctrl-btn.danger {
  color: rgba(248, 113, 113, 0.85);
}

.obj-ctrl-btn.danger:active {
  background: rgba(248, 113, 113, 0.2);
  color: #f87171;
}

.obj-ctrl-btn.active {
  background: rgba(168, 85, 247, 0.25);
  color: #c084fc;
}

.obj-ctrl-btn.crop-btn.active {
  background: rgba(20, 184, 166, 0.24);
  color: #5eead4;
}

.obj-ctrl-btn.color-btn.active {
  background: rgba(236, 72, 153, 0.24);
  color: #f9a8d4;
}

.obj-ctrl-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  animation: pulse-loading 1s ease-in-out infinite;
}

@keyframes pulse-loading {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.9; }
}

.obj-ctrl-divider {
  width: 1px;
  height: 20px;
  background: rgba(255, 255, 255, 0.12);
  margin: 0 2px;
}

.margin-ctrl {
  display: flex;
  align-items: center;
  gap: 3px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  padding: 2px 8px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  white-space: nowrap;
}

.margin-ctrl label {
  color: rgba(255, 255, 255, 0.45);
  font-size: 10px;
}

.margin-input {
  width: 38px;
  height: 22px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.85);
  font-size: 12px;
  text-align: center;
  outline: none;
  -moz-appearance: textfield;
}

.margin-input::-webkit-outer-spin-button,
.margin-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.margin-input:focus {
  border-color: rgba(99, 102, 241, 0.5);
  background: rgba(99, 102, 241, 0.1);
}

.crop-panel {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 126px;
  z-index: 55;
  max-width: 520px;
  margin: 0 auto;
  padding: 12px;
  border-radius: 18px;
  background: rgba(18, 24, 38, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.38);
  color: #fff;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.crop-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.crop-panel-head > span,
.crop-actions,
.crop-actions button {
  display: flex;
  align-items: center;
}

.crop-panel-head > span {
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
}

.crop-actions {
  gap: 6px;
}

.crop-actions button {
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  border: none;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
}

.crop-actions button.primary {
  background: #14b8a6;
  color: #fff;
}

.crop-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
}

.crop-field {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.crop-field span {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.68);
}

.crop-field input {
  width: 100%;
  accent-color: #14b8a6;
}

.svg-color-panel {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 126px;
  z-index: 55;
  max-width: 420px;
  margin: 0 auto;
  padding: 12px;
  border-radius: 18px;
  background: rgba(18, 24, 38, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.38);
  color: #fff;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.svg-color-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.svg-color-head span {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
}

.svg-color-head input[type="color"] {
  width: 42px;
  height: 30px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 10px;
  overflow: hidden;
  background: transparent;
}

.svg-color-swatches {
  display: grid;
  grid-template-columns: repeat(10, minmax(0, 1fr));
  gap: 8px;
}

.svg-color-swatches button {
  width: 100%;
  aspect-ratio: 1;
  min-height: 28px;
  border: 2px solid rgba(255, 255, 255, 0.16);
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.12);
}

.svg-color-swatches button.active {
  border-color: #fff;
  box-shadow: 0 0 0 2px rgba(236, 72, 153, 0.58);
}

.print-confirm-content {
  text-align: center;
  padding: 8px 0;
}

.print-confirm-content p {
  margin: 8px 0;
  color: #666;
  font-size: 14px;
}

.loading-content {
  text-align: center;
  padding: 24px 0;
}

.loading-content p {
  margin-top: 12px;
  color: #666;
}

.download-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.download-preview-img {
  max-width: 100%;
  max-height: 60vh;
  border-radius: 8px;
  object-fit: contain;
}

.download-tip {
  color: #666;
  font-size: 14px;
  text-align: center;
}

.upload-input {
  display: none;
}
</style>
