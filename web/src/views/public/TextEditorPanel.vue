<template>
  <transition name="slide-up">
    <div v-if="visible" class="text-editor-panel">
      <div class="panel-header">
        <span class="panel-title">文字编辑</span>
        <button class="close-btn" @click="$emit('close')">
          <X :size="20" />
        </button>
      </div>

      <div class="panel-body">
        <div class="form-item">
          <label>文字内容</label>
          <a-textarea
            v-model:value="localText"
            :rows="2"
            :maxlength="200"
            show-count
            placeholder="输入文字..."
            @change="onTextChange"
          />
        </div>

        <div class="form-item">
          <label>字体</label>
          <div class="font-list">
            <button
              v-for="font in fonts"
              :key="font.family"
              :class="['font-btn', { active: localFont === font.family }]"
              :style="{ fontFamily: font.family }"
              @click="selectFont(font)"
            >
              {{ font.name }}
            </button>
          </div>
        </div>

        <div class="form-item">
          <label>字号: {{ localFontSize }}</label>
          <a-slider v-model:value="localFontSize" :min="12" :max="120" @change="onStyleChange" />
        </div>

        <div class="form-item">
          <label>颜色</label>
          <div class="color-row">
            <button
              v-for="color in presetColors"
              :key="color"
              :class="['color-btn', { active: localColor === color }]"
              :style="{ background: color }"
              @click="selectColor(color)"
            />
            <input
              v-model="localColor"
              type="color"
              class="color-picker"
              @change="onStyleChange"
            />
          </div>
        </div>

        <div class="form-item">
          <label>样式</label>
          <div class="style-btns">
            <button
              :class="['style-btn', { active: localBold }]"
              @click="toggleBold"
            >
              <Bold :size="16" /> 加粗
            </button>
            <button
              :class="['style-btn', { active: localItalic }]"
              @click="toggleItalic"
            >
              <Italic :size="16" /> 斜体
            </button>
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <a-button @click="$emit('close')">取消</a-button>
        <a-button type="primary" @click="confirmText">确定</a-button>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { X, Bold, Italic } from 'lucide-vue-next'

export interface TextStyle {
  text: string
  fontFamily: string
  fontSize: number
  fill: string
  fontWeight?: string
  fontStyle?: string
}

const props = defineProps<{
  visible: boolean
  initialText?: string
  initialStyle?: Partial<TextStyle>
}>()

const emit = defineEmits<{
  confirm: [style: TextStyle]
  preview: [style: TextStyle]
  close: []
}>()

const localText = ref(props.initialText || '点击编辑文字')
const localFont = ref(props.initialStyle?.fontFamily || 'sans-serif')
const localFontSize = ref(props.initialStyle?.fontSize || 48)
const localColor = ref(props.initialStyle?.fill || '#333333')
const localBold = ref(props.initialStyle?.fontWeight === 'bold')
const localItalic = ref(props.initialStyle?.fontStyle === 'italic')

const fonts = [
  { name: '默认黑体', family: 'sans-serif' },
  { name: '思源黑体', family: 'Noto Sans SC' },
  { name: '思源宋体', family: 'Noto Serif SC' },
  { name: '站酷快乐体', family: 'ZCOOL QingKe HuangYou' },
  { name: '站酷小薇体', family: 'ZCOOL XiaoWei' },
]

const presetColors = ['#333333', '#ffffff', '#ff4d4f', '#fa8c16', '#fadb14', '#52c41a', '#1890ff', '#722ed1']

function selectFont(font: { name: string; family: string }) {
  localFont.value = font.family
  onStyleChange()
}

function selectColor(color: string) {
  localColor.value = color
  onStyleChange()
}

function toggleBold() {
  localBold.value = !localBold.value
  onStyleChange()
}

function toggleItalic() {
  localItalic.value = !localItalic.value
  onStyleChange()
}

function onTextChange() {
  emitPreview()
}

function onStyleChange() {
  emitPreview()
}

function emitPreview() {
  emit('preview', {
    text: localText.value,
    fontFamily: localFont.value,
    fontSize: localFontSize.value,
    fill: localColor.value,
    fontWeight: localBold.value ? 'bold' : 'normal',
    fontStyle: localItalic.value ? 'italic' : 'normal',
  })
}

function confirmText() {
  emit('confirm', {
    text: localText.value,
    fontFamily: localFont.value,
    fontSize: localFontSize.value,
    fill: localColor.value,
    fontWeight: localBold.value ? 'bold' : 'normal',
    fontStyle: localItalic.value ? 'italic' : 'normal',
  })
}

watch(() => props.visible, (visible) => {
  if (visible) {
    localText.value = props.initialText || '点击编辑文字'
    localFont.value = props.initialStyle?.fontFamily || 'sans-serif'
    localFontSize.value = props.initialStyle?.fontSize || 48
    localColor.value = props.initialStyle?.fill || '#333333'
    localBold.value = props.initialStyle?.fontWeight === 'bold'
    localItalic.value = props.initialStyle?.fontStyle === 'italic'
  }
})
</script>

<style scoped>
.text-editor-panel {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 120;
  max-height: 72vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px 16px 0 0;
  box-shadow: 0 -10px 32px rgba(15, 23, 42, 0.18);
}

.panel-header,
.panel-footer {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.panel-footer {
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid #f0f0f0;
  border-bottom: 0;
}

.panel-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.close-btn {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 50%;
  background: #f3f4f6;
  color: #374151;
  display: flex;
  align-items: center;
  justify-content: center;
}

.panel-body {
  flex: 1;
  overflow: auto;
  padding: 14px 16px 18px;
}

.form-item {
  margin-bottom: 14px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  color: #374151;
  font-size: 13px;
  font-weight: 700;
}

.font-list {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.font-btn,
.style-btn {
  flex: 0 0 auto;
  min-height: 34px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #374151;
  padding: 0 12px;
}

.font-btn.active,
.style-btn.active {
  border-color: #1677ff;
  background: #eef6ff;
  color: #1677ff;
  font-weight: 700;
}

.color-row,
.style-btns {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.color-btn,
.color-picker {
  width: 32px;
  height: 32px;
  border: 2px solid #fff;
  border-radius: 50%;
  box-shadow: 0 0 0 1px #d1d5db;
  padding: 0;
}

.color-btn.active {
  box-shadow: 0 0 0 2px #1677ff;
}

.style-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
