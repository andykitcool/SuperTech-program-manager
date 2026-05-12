<template>
  <div class="canvas-toolbar">
    <div class="toolbar-row toolbar-main">
      <button class="mat-btn" @click="$emit('addBackground')">
        <div class="mat-icon"><Image :size="18" /></div>
        <span>背景</span>
      </button>
      <button class="mat-btn" @click="$emit('addFrame')">
        <div class="mat-icon"><Square :size="18" /></div>
        <span>相框</span>
      </button>
      <button class="mat-btn" @click="$emit('addSticker')">
        <div class="mat-icon"><Sparkles :size="18" /></div>
        <span>装饰</span>
      </button>
      <button class="mat-btn" @click="$emit('addText')">
        <div class="mat-icon"><Type :size="18" /></div>
        <span>文字</span>
      </button>
      <button class="mat-btn" :class="{ active: hasSelection }" :disabled="!hasSelection" @click="$emit('editSelected')">
        <div class="mat-icon"><Settings2 :size="18" /></div>
        <span>编辑</span>
      </button>
      <button class="mat-btn upload-btn" @click="$emit('uploadImage')">
        <div class="mat-icon"><Upload :size="18" /></div>
        <span>上传</span>
      </button>
      <button class="mat-btn unlock-all-btn" title="一键解锁所有图层元素" @click="$emit('unlockAll')">
        <div class="mat-icon"><Unlock :size="18" /></div>
        <span>全解锁</span>
      </button>
      <div class="toolbar-spacer" />
      <div class="layer-group">
        <button class="layer-btn" :disabled="!hasSelection" title="下移图层" @click="$emit('layerBackward')">
          <Layers :size="13" />
          <ChevronDown :size="15" />
        </button>
        <button class="layer-btn" :disabled="!hasSelection" title="上移图层" @click="$emit('layerForward')">
          <Layers :size="13" />
          <ChevronUp :size="15" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Image, Square, Sparkles, Type,
  ChevronDown, ChevronUp, Layers,
  Settings2, Upload, Unlock,
} from 'lucide-vue-next'

defineProps<{
  hasSelection: boolean
}>()

defineEmits<{
  addBackground: []
  addFrame: []
  addSticker: []
  addText: []
  layerForward: []
  layerBackward: []
  editSelected: []
  uploadImage: []
  unlockAll: []
}>()
</script>

<style scoped>
.canvas-toolbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(30, 30, 46, 0.95);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  z-index: 100;
  padding: 6px 6px calc(6px + env(safe-area-inset-bottom, 0px));
}

.toolbar-row {
  display: flex;
  align-items: center;
  gap: 2px;
}

.toolbar-spacer {
  flex: 1;
}

.toolbar-divider-v {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.12);
  margin: 0 4px;
}

.mat-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: 4px 5px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.65);
  font-size: 9px;
  transition: all 0.15s ease;
  -webkit-tap-highlight-color: transparent;
}

.mat-btn .mat-icon {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  transition: all 0.15s ease;
}

.mat-btn .mat-icon.danger {
  color: rgba(255, 100, 100, 0.7);
}

.mat-btn:active .mat-icon,
.mat-btn:hover .mat-icon {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

.mat-btn.active .mat-icon {
  background: rgba(99, 102, 241, 0.25);
  color: #818cf8;
}

.unlock-all-btn .mat-icon {
  color: #facc15;
}

.mat-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.mat-btn:disabled .mat-icon.danger {
  color: rgba(255, 100, 100, 0.3);
}

.layer-group {
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 3px;
}

.layer-btn {
  width: 34px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1px;
  border: none;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.76);
  transition: all 0.15s ease;
  -webkit-tap-highlight-color: transparent;
}

.layer-btn:active,
.layer-btn:hover {
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
}

.layer-btn:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}
</style>
