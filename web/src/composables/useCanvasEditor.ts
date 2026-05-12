/**
 * useCanvasEditor - fabric.js 画布编辑器核心 composable
 * 支持：初始化、图层操作、触屏双指缩放、导出JSON/图片、素材添加
 */
import { ref, shallowRef, onUnmounted } from 'vue'
import { Canvas, FabricImage, IText, Textbox, FabricText, Point, loadSVGFromURL, util, type FabricObject, type ImageFormat } from 'fabric'

// 解析 fabric 中的文字类（兼容不同导出结构）
function _resolveTextClass(): any {
  const candidates = [IText, Textbox, FabricText]
  for (const cls of candidates) {
    if (typeof cls === 'function') return cls
  }
  return null
}

export interface CanvasConfig {
  width: number
  height: number
  backgroundColor?: string
}

export interface TextStyle {
  text: string
  fontFamily: string
  fontSize: number
  fill: string
  fontWeight?: string
  fontStyle?: string
}

export interface PhotoInitConfig {
  initX: number  // 0~100 百分比
  initY: number  // 0~100 百分比
  initScale: number // 10~200 百分比
  margin?: number   // 照片与画布左、上、右边缘的像素距离
}

export interface ImageCropState {
  left: number
  right: number
  top: number
  bottom: number
}

export function useCanvasEditor() {
  const fabricCanvas = shallowRef<Canvas | null>(null)
  const isReady = ref(false)
  const selectedObject = shallowRef<FabricObject | null>(null)

  // 逻辑尺寸（打印模板配置的画布尺寸，如 1500×1500）
  let _logicalWidth = 0
  let _logicalHeight = 0
  // 显示缩放比（画布逻辑尺寸 → 屏幕显示尺寸的比例）
  let _displayScale = 1

  // 触屏双指缩放状态
  let _pinchStartDist = 0
  let _pinchStartScaleX = 1
  let _pinchStartScaleY = 1

  // 触摸双击检测状态
  let _lastTapTime = 0
  let _lastTapTarget: any = null

  // 双击对象回调
  let _dblClickCallback: ((obj: any) => void) | null = null

  function _applyObjectLockState(obj: any, locked = !!obj?._locked || !!obj?.lockMovementX) {
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
      editable: !locked && obj.type !== 'i-text' && obj.type !== 'textbox',
      hoverCursor: locked ? 'default' : 'move',
    })
    obj._locked = locked
  }

  // 初始化 fabric 画布
  // displayScale: 画布逻辑尺寸到屏幕显示尺寸的缩放比（如手机上 1500px → 359px 则为 ~0.239）
  function initCanvas(canvasElement: HTMLCanvasElement, config: CanvasConfig, displayScale: number = 1) {
    _logicalWidth = config.width
    _logicalHeight = config.height
    _displayScale = displayScale

    const displayW = Math.round(config.width * displayScale)
    const displayH = Math.round(config.height * displayScale)

    fabricCanvas.value = new Canvas(canvasElement, {
      width: displayW,
      height: displayH,
      backgroundColor: config.backgroundColor || '#ffffff',
      selection: true,
      preserveObjectStacking: true,
    })

    const canvas = fabricCanvas.value

    // 使用 setZoom 让 Fabric.js 视口缩放，坐标系仍为逻辑尺寸（1500×1500）
    if (displayScale !== 1) {
      canvas.setZoom(displayScale)
    }

    // 监听选中事件
    canvas.on('selection:created', (e: any) => {
      selectedObject.value = e.selected?.[0] || null
      if (e.selected?.[0]) _setCornerControlsOnly(e.selected[0])
    })
    canvas.on('selection:updated', (e: any) => {
      selectedObject.value = e.selected?.[0] || null
      if (e.selected?.[0]) _setCornerControlsOnly(e.selected[0])
    })
    canvas.on('selection:cleared', () => {
      selectedObject.value = null
    })

    // 触屏双指缩放支持（缩放选中对象）
    _setupPinchToZoom(canvas)

    // 鼠标双击对象事件
    canvas.on('mouse:dblclick', (e: any) => {
      if (e.target && _dblClickCallback) {
        _dblClickCallback(e.target)
      }
    })

    // 触摸双击检测（移动端 object:dblclick 不触发）
    _setupTouchDoubleTap(canvas)

    isReady.value = true
    return canvas
  }

  // 触屏双指缩放：选中对象时，双指可以缩放该对象
  function _setupPinchToZoom(canvas: Canvas) {
    const upperCanvas = canvas.upperCanvasEl
    if (!upperCanvas) return

    upperCanvas.addEventListener('touchstart', (e: TouchEvent) => {
      if (e.touches.length === 2) {
        const activeObj = canvas.getActiveObject()
        if (activeObj && !(activeObj as any)._locked) {
          e.preventDefault()
          _pinchStartDist = _getTouchDistance(e.touches)
          _pinchStartScaleX = activeObj.scaleX || 1
          _pinchStartScaleY = activeObj.scaleY || 1
        }
      }
    }, { passive: false })

    upperCanvas.addEventListener('touchmove', (e: TouchEvent) => {
      if (e.touches.length === 2 && _pinchStartDist > 0) {
        const activeObj = canvas.getActiveObject()
        if (activeObj) {
          // 锁定对象不允许缩放
          if ((activeObj as any)._locked) {
            e.preventDefault()
            return
          }
          e.preventDefault()
          const currentDist = _getTouchDistance(e.touches)
          const scaleFactor = currentDist / _pinchStartDist
          const newScaleX = Math.max(0.05, Math.min(5, _pinchStartScaleX * scaleFactor))
          const newScaleY = Math.max(0.05, Math.min(5, _pinchStartScaleY * scaleFactor))

          activeObj.set({ scaleX: newScaleX, scaleY: newScaleY })
          activeObj.setCoords()
          canvas.renderAll()
        }
      }
    }, { passive: false })

    upperCanvas.addEventListener('touchend', (e: TouchEvent) => {
      if (_pinchStartDist > 0 && e.touches.length < 2) {
        _pinchStartDist = 0
        const activeObj = canvas.getActiveObject()
        if (activeObj) {
          canvas.fire('object:modified', { target: activeObj })
        }
      }
    })
  }

  function _getTouchDistance(touches: TouchList): number {
    const dx = touches[0].clientX - touches[1].clientX
    const dy = touches[0].clientY - touches[1].clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  // 触摸双击检测（移动端 Fabric.js 不触发 object:dblclick）
  function _setupTouchDoubleTap(canvas: Canvas) {
    const upperCanvas = canvas.upperCanvasEl
    if (!upperCanvas) return

    upperCanvas.addEventListener('touchend', (e: TouchEvent) => {
      if (e.touches.length > 0) return // 还有手指在屏幕上，不是 tap
      const now = Date.now()
      const tapTarget = canvas.getActiveObject()

      if (tapTarget && _lastTapTarget === tapTarget && (now - _lastTapTime) < 400) {
        // 双击检测成功
        e.preventDefault()
        if (_dblClickCallback) {
          _dblClickCallback(tapTarget)
        }
        // 退出 IText 内联编辑模式（如果进入了的话）
        if (tapTarget.type === 'i-text' || tapTarget.type === 'textbox') {
          canvas.discardActiveObject()
          canvas.setActiveObject(tapTarget)
          ;(tapTarget as any).exitEditing()
          canvas.renderAll()
        }
        _lastTapTime = 0
        _lastTapTarget = null
      } else {
        _lastTapTime = now
        _lastTapTarget = tapTarget
      }
    }, { passive: false })
  }

  // 只保留四角控制点，隐藏四边中点控制点
  function _setCornerControlsOnly(obj: any) {
    obj.setControlsVisibility({
      ml: false, // 左中
      mt: false, // 上中
      mr: false, // 右中
      mb: false, // 下中
    })
  }

  function _isSvgSource(imageUrl: string): boolean {
    const cleanUrl = imageUrl.split('?')[0].split('#')[0].toLowerCase()
    return cleanUrl.endsWith('.svg') || imageUrl.startsWith('data:image/svg+xml')
  }

  async function _loadVisualObject(imageUrl: string): Promise<any> {
    if (_isSvgSource(imageUrl)) {
      try {
        const svg = await loadSVGFromURL(imageUrl)
        const objects = (svg.objects || []).filter(Boolean) as any[]
        if (objects.length) {
          return util.groupSVGElements(objects, svg.options || {})
        }
      } catch (e) {
        console.warn('[useCanvasEditor] SVG vector parsing failed, fallback to image element:', e)
      }
    }
    return FabricImage.fromURL(imageUrl, { crossOrigin: 'anonymous' })
  }

  function _markSvgObject(obj: any, imageUrl: string) {
    if (!_isSvgSource(imageUrl)) return
    obj._isSvgMaterial = true
    obj._svgSourceUrl = imageUrl
    obj._svgColor = obj._svgColor || '#111827'
  }

  function _rememberImageSourceSize(obj: any) {
    if (!obj) return
    obj._sourceWidth = obj._sourceWidth || obj.width || 1
    obj._sourceHeight = obj._sourceHeight || obj.height || 1
    obj._cropState = obj._cropState || { left: 0, right: 0, top: 0, bottom: 0 }
  }

  function _walkObjects(obj: any, visitor: (item: any) => void) {
    visitor(obj)
    const children = typeof obj.getObjects === 'function' ? obj.getObjects() : obj._objects
    if (Array.isArray(children)) {
      children.forEach(child => _walkObjects(child, visitor))
    }
  }

  function _colorVectorSvg(obj: any, color: string) {
    _walkObjects(obj, item => {
      const currentFill = item.fill
      const currentStroke = item.stroke
      if (currentFill !== 'none' && currentFill !== null) {
        item.set('fill', color)
      }
      if (currentStroke && currentStroke !== 'none') {
        item.set('stroke', color)
      }
    })
    obj._svgColor = color
  }

  function _recolorSvgText(svgText: string, color: string): string {
    const cleaned = svgText.replace(/<!DOCTYPE[\s\S]*?>/i, '')
    const style = `<style>path,polygon,circle,rect,ellipse{fill:${color} !important;}line,polyline{stroke:${color} !important;}[stroke]:not([stroke="none"]){stroke:${color} !important;}</style>`
    if (cleaned.includes('<style')) {
      return cleaned.replace(/<style[\s\S]*?<\/style>/i, style)
    }
    return cleaned.replace(/<svg\b([^>]*)>/i, `<svg$1>${style}`)
  }

  // 添加图片到画布
  // fillMode: 'contain' = 按最长边完全展示（默认，适合主照片），'fit' = 缩小适配画布50%（适合装饰）
  // photoInit: 照片初始位置/缩放配置（仅主照片有效）
  function addImage(
    imageUrl: string,
    options?: any,
    fillMode: 'contain' | 'fit' = 'contain',
    photoInit?: Partial<PhotoInitConfig>
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!fabricCanvas.value) return reject(new Error('Canvas not initialized'))

      _loadVisualObject(imageUrl)
        .then((img: any) => {
          if (!img) {
            return reject(new Error('Failed to load image'))
          }
          const cvs = fabricCanvas.value!
          // 使用逻辑尺寸计算定位，而非画布像素尺寸（因 setZoom 缩放了视口）
          const canvasWidth = _logicalWidth || cvs.getWidth()
          const canvasHeight = _logicalHeight || cvs.getHeight()

          let scale = 1
          let left: number, top: number

          if (fillMode === 'contain' && photoInit) {
            // 使用打印模板配置的边距：照片左、上、右边缘与画布保持 margin 像素
            const margin = photoInit.margin ?? 20
            // 可用区域 = 画布宽 - 左边距 - 右边距，高 - 上边距
            const availW = canvasWidth - margin * 2
            const availH = canvasHeight - margin
            scale = Math.min(availW / (img.width || 1), availH / (img.height || 1))

            // 照片定位：左边缘 = margin，上边缘 = margin，水平方向在可用区域内居中
            const imgW = (img.width || 1) * scale
            const imgH = (img.height || 1) * scale
            left = margin + imgW / 2
            top = margin + imgH / 2
          } else if (fillMode === 'contain') {
            // 按最长边完全展示：照片的长边刚好等于画布对应边
            const scaleX = canvasWidth / (img.width || 1)
            const scaleY = canvasHeight / (img.height || 1)
            scale = Math.min(scaleX, scaleY)
            left = canvasWidth / 2
            top = canvasHeight / 2
          } else {
            // fit模式：缩小适配画布50%（适合装饰素材）
            if ((img.width || 0) > canvasWidth || (img.height || 0) > canvasHeight) {
              scale = Math.min(canvasWidth / (img.width || 1), canvasHeight / (img.height || 1)) * 0.5
            } else {
              scale = 0.5
            }
            left = canvasWidth / 2
            top = canvasHeight / 2
          }

          img.set({
            left,
            top,
            originX: 'center',
            originY: 'center',
            scaleX: scale,
            scaleY: scale,
            ...options,
          })
          _markSvgObject(img, imageUrl)
          _rememberImageSourceSize(img)

          // 标记主照片，用于"恢复初始位置"
          if (fillMode === 'contain' && photoInit) {
            ;(img as any)._isMainPhoto = true
            ;(img as any)._isEditablePhoto = true
            ;(img as any)._photoInit = { ...photoInit, margin: photoInit.margin ?? 20 }
          }
          if (options?._isEditablePhoto) {
            ;(img as any)._isEditablePhoto = true
          }

          cvs.add(img)
          _setCornerControlsOnly(img)
          cvs.setActiveObject(img)
          cvs.renderAll()
          resolve(img)
        })
        .catch(reject)
    })
  }

  // 添加背景图片
  function addBackground(imageUrl: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!fabricCanvas.value) return reject(new Error('Canvas not initialized'))
      const cvs = fabricCanvas.value!
      const lw = _logicalWidth || cvs.getWidth()
      const lh = _logicalHeight || cvs.getHeight()

      _loadVisualObject(imageUrl)
        .then((img: any) => {
          if (!img) {
            return reject(new Error('Failed to load background image'))
          }
          img.set({
            scaleX: lw / (img.width || 1),
            scaleY: lh / (img.height || 1),
            originX: 'left',
            originY: 'top',
            left: 0,
            top: 0,
            lockMovementX: true,
            lockMovementY: true,
            lockScalingX: true,
            lockScalingY: true,
            lockRotation: true,
            hasControls: false,
            hasBorders: false,
            hoverCursor: 'not-allowed',
          })
          _markSvgObject(img, imageUrl)
          ;(img as any)._isBackgroundMaterial = true
          _applyObjectLockState(img, true)
          cvs.add(img)
          cvs.sendObjectToBack(img)
          cvs.renderAll()
          resolve()
        })
        .catch(reject)
    })
  }

  // 添加文字 - 使用 IText（可交互编辑文字）
  function addText(text: string = '点击编辑文字', style?: Partial<TextStyle>): any | null {
    if (!fabricCanvas.value) return null

    try {
      const cvs = fabricCanvas.value
      const canvasWidth = _logicalWidth || cvs.getWidth()
      const canvasHeight = _logicalHeight || cvs.getHeight()

      // fabric v5 导出结构：fabric.fabric.IText
      const TextClass = _resolveTextClass()

      if (!TextClass) {
        console.error('[useCanvasEditor] No IText/Textbox class found in fabric')
        return null
      }

      const textObj = new TextClass(text, {
        left: canvasWidth / 2,
        top: canvasHeight / 2,
        originX: 'center',
        originY: 'center',
        fontFamily: style?.fontFamily || 'sans-serif',
        fontSize: style?.fontSize || 48,
        fill: style?.fill || '#333333',
        fontWeight: style?.fontWeight || 'normal',
        fontStyle: style?.fontStyle === 'italic' ? 'italic' : 'normal',
        editable: false, // 禁用内联编辑，双击打开自定义面板
        hasControls: true,
        hasBorders: true,
      })

      cvs.add(textObj)
      _setCornerControlsOnly(textObj)
      cvs.setActiveObject(textObj)
      // 确保文字在最上层
      cvs.bringObjectToFront(textObj)
      cvs.renderAll()
      return textObj
    } catch (e) {
      console.error('[useCanvasEditor] addText error:', e)
      return null
    }
  }

  // 删除选中对象
  function deleteSelected() {
    if (!fabricCanvas.value) return
    const active = fabricCanvas.value.getActiveObjects()
    if (active.length) {
      fabricCanvas.value.discardActiveObject()
      active.forEach((obj) => fabricCanvas.value!.remove(obj))
      fabricCanvas.value.renderAll()
    }
    selectedObject.value = null
  }

  // 复制选中对象
  function cloneSelected() {
    if (!fabricCanvas.value) return
    const active = fabricCanvas.value.getActiveObject()
    if (!active) return
    active.clone().then((cloned: any) => {
      cloned.set({ left: (active.left || 0) + 20, top: (active.top || 0) + 20 })
      fabricCanvas.value!.add(cloned)
      _setCornerControlsOnly(cloned)
      fabricCanvas.value!.setActiveObject(cloned)
      fabricCanvas.value!.renderAll()
    })
  }

  // 导出画布 JSON
  function exportJSON(): string | null {
    if (!fabricCanvas.value) return null
    return JSON.stringify((fabricCanvas.value as any).toJSON(['_locked']))
  }

  // 导出画布为图片（临时重置 zoom 以输出逻辑分辨率）
  function exportImage(options?: { format?: string; quality?: number; multiplier?: number }): string | null {
    if (!fabricCanvas.value) return null
    const canvas = fabricCanvas.value
    const format = (options?.format || 'png') as ImageFormat

    // 如果显示缩放为1，直接导出
    if (_displayScale === 1) {
      return canvas.toDataURL({
        format,
        quality: options?.quality || 1,
        multiplier: options?.multiplier || 2,
      })
    }

    // 临时重置到逻辑尺寸导出全分辨率
    canvas.setZoom(1)
    canvas.setDimensions({ width: _logicalWidth, height: _logicalHeight })
    canvas.renderAll()

    const dataUrl = canvas.toDataURL({
      format,
      quality: options?.quality || 1,
      multiplier: options?.multiplier || 2,
    })

    // 恢复显示缩放
    canvas.setZoom(_displayScale)
    canvas.setDimensions({ width: Math.round(_logicalWidth * _displayScale), height: Math.round(_logicalHeight * _displayScale) })
    canvas.renderAll()

    return dataUrl
  }

  // 从 JSON 加载画布
  function loadFromJSON(json: string | object) {
    return new Promise<void>((resolve, reject) => {
      if (!fabricCanvas.value) return reject(new Error('Canvas not initialized'))
      try {
        const jsonObj = typeof json === 'string' ? json : JSON.stringify(json)
        fabricCanvas.value.loadFromJSON(jsonObj).then(() => {
          fabricCanvas.value!.getObjects().forEach((obj: any) => {
            _applyObjectLockState(obj, !!obj._locked || !!obj.lockMovementX)
          })
          fabricCanvas.value!.renderAll()
          resolve()
        }).catch(reject)
      } catch (e) {
        reject(e)
      }
    })
  }

  // 清空画布
  function clearCanvas() {
    if (!fabricCanvas.value) return
    fabricCanvas.value.clear()
    fabricCanvas.value.backgroundColor = '#ffffff'
    fabricCanvas.value.renderAll()
  }

  // 更新选中对象样式
  function updateSelectedStyle(style: Record<string, any>) {
    if (!fabricCanvas.value || !selectedObject.value) return
    selectedObject.value.set(style)
    fabricCanvas.value.renderAll()
  }

  // 缩放画布视口
  function zoomCanvas(delta: number) {
    if (!fabricCanvas.value) return
    const zoom = fabricCanvas.value.getZoom()
    const newZoom = Math.max(0.1, Math.min(5, zoom * (1 + delta * 0.1)))
    const center = fabricCanvas.value.getVpCenter()
    fabricCanvas.value.zoomToPoint(new Point(center.x, center.y), newZoom)
  }

  // 重置画布缩放（恢复到显示缩放比，而非1:1）
  function resetZoom() {
    if (!fabricCanvas.value) return
    fabricCanvas.value.setViewportTransform([_displayScale, 0, 0, _displayScale, 0, 0])
    fabricCanvas.value.renderAll()
  }

  // 更新画布视口（窗口尺寸变化时调用）
  function updateViewport(displayScale: number) {
    if (!fabricCanvas.value) return
    _displayScale = displayScale
    const displayW = Math.round(_logicalWidth * displayScale)
    const displayH = Math.round(_logicalHeight * displayScale)
    fabricCanvas.value.setZoom(displayScale)
    fabricCanvas.value.setDimensions({ width: displayW, height: displayH })
    fabricCanvas.value.renderAll()
  }

  // 获取选中对象类型
  function getSelectedType(): string | null {
    if (!selectedObject.value) return null
    return selectedObject.value.type || null
  }

  // 注册双击对象回调
  function onObjectDoubleClick(callback: (obj: any) => void) {
    _dblClickCallback = callback
  }

  // 水平居中选中对象（保持 Y 不变，让照片垂直中线与画布垂直中线重合）
  function centerObjectH() {
    if (!fabricCanvas.value || !selectedObject.value) return
    const cvs = fabricCanvas.value
    const obj = selectedObject.value as any
    const canvasW = _logicalWidth || cvs.getWidth()
    // 用 originX='center' + left=画布中心，无论对象当前 origin 是什么都正确居中
    obj.set({
      left: canvasW / 2,
      originX: 'center',
    })
    obj.setCoords()
    cvs.renderAll()
    cvs.fire('object:modified', { target: obj })
  }

  // 垂直居中选中对象（保持 X 不变，让照片水平中线与画布水平中线重合）
  function centerObjectV() {
    if (!fabricCanvas.value || !selectedObject.value) return
    const cvs = fabricCanvas.value
    const obj = selectedObject.value as any
    const canvasH = _logicalHeight || cvs.getHeight()
    obj.set({
      top: canvasH / 2,
      originY: 'center',
    })
    obj.setCoords()
    cvs.renderAll()
    cvs.fire('object:modified', { target: obj })
  }

  // 中心点居中选中对象
  function centerObjectBoth() {
    if (!fabricCanvas.value || !selectedObject.value) return
    const cvs = fabricCanvas.value
    const obj = selectedObject.value as any
    obj.set({
      left: (_logicalWidth || cvs.getWidth()) / 2,
      top: (_logicalHeight || cvs.getHeight()) / 2,
      originX: 'center',
      originY: 'center',
    })
    obj.setCoords()
    cvs.renderAll()
    cvs.fire('object:modified', { target: obj })
  }

  // 锁定/解锁选中对象
  function toggleLockObject(): boolean {
    if (!fabricCanvas.value || !selectedObject.value) return false
    const cvs = fabricCanvas.value
    const obj = selectedObject.value as any
    const locked = !(obj as any)._locked
    _applyObjectLockState(obj, locked)
    obj.setCoords()
    if (locked) {
      cvs.discardActiveObject()
      selectedObject.value = obj
    } else {
      cvs.setActiveObject(obj)
    }
    cvs.requestRenderAll()
    return locked
  }

  function unlockAllObjects(): number {
    if (!fabricCanvas.value) return 0
    const cvs = fabricCanvas.value
    let changed = 0
    cvs.getObjects().forEach((obj: any) => {
      if (obj._locked || obj.lockMovementX || obj.lockMovementY || obj.lockScalingX || obj.lockScalingY || obj.lockRotation) {
        _applyObjectLockState(obj, false)
        obj.setCoords()
        changed += 1
      }
    })
    if (selectedObject.value) {
      cvs.setActiveObject(selectedObject.value)
    }
    cvs.requestRenderAll()
    return changed
  }

  function bringSelectedForward() {
    if (!fabricCanvas.value || !selectedObject.value) return false
    const cvs = fabricCanvas.value
    const obj = selectedObject.value
    const moved = cvs.bringObjectForward(obj)
    if (moved) {
      obj.setCoords()
      cvs.setActiveObject(obj)
      cvs.renderAll()
      cvs.fire('object:modified', { target: obj })
    }
    return moved
  }

  function sendSelectedBackward() {
    if (!fabricCanvas.value || !selectedObject.value) return false
    const cvs = fabricCanvas.value
    const obj = selectedObject.value
    const moved = cvs.sendObjectBackwards(obj)
    if (moved) {
      obj.setCoords()
      cvs.setActiveObject(obj)
      cvs.renderAll()
      cvs.fire('object:modified', { target: obj })
    }
    return moved
  }

  // 获取选中对象是否锁定
  function isSelectedLocked(): boolean {
    if (!selectedObject.value) return false
    return !!(selectedObject.value as any).lockMovementX
  }

  // 判断选中对象是否为主照片
  function isSelectedMainPhoto(): boolean {
    if (!selectedObject.value) return false
    return !!(selectedObject.value as any)._isMainPhoto
  }

  function isSelectedCropTarget(): boolean {
    if (!selectedObject.value) return false
    const obj = selectedObject.value as any
    return obj.type === 'image' && !!obj._isEditablePhoto
  }

  function isSelectedSvgTarget(): boolean {
    if (!selectedObject.value) return false
    return !!(selectedObject.value as any)._isSvgMaterial
  }

  function getSelectedSvgColor(): string {
    const obj = selectedObject.value as any
    return obj?._svgColor || '#111827'
  }

  async function applySelectedSvgColor(color: string) {
    if (!fabricCanvas.value || !selectedObject.value || !isSelectedSvgTarget()) return
    const obj = selectedObject.value as any
    const cvs = fabricCanvas.value

    if (obj.type !== 'image') {
      _colorVectorSvg(obj, color)
      obj.setCoords()
      cvs.renderAll()
      cvs.fire('object:modified', { target: obj })
      return
    }

    const sourceUrl = obj._svgSourceUrl
    if (!sourceUrl) return
    try {
      let svgText = obj._svgOriginalText
      if (!svgText) {
        if (sourceUrl.startsWith('data:image/svg+xml')) {
          const commaIndex = sourceUrl.indexOf(',')
          const payload = commaIndex >= 0 ? sourceUrl.slice(commaIndex + 1) : ''
          svgText = sourceUrl.includes(';base64,') ? atob(payload) : decodeURIComponent(payload)
        } else {
          const res = await fetch(sourceUrl)
          svgText = await res.text()
        }
        obj._svgOriginalText = svgText
      }
      const recolored = _recolorSvgText(svgText, color)
      const dataUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(recolored)}`
      await new Promise<void>((resolve, reject) => {
        obj.setSrc(dataUrl, () => {
          obj._svgColor = color
          obj._svgSourceUrl = dataUrl
          obj.setCoords()
          cvs.renderAll()
          cvs.fire('object:modified', { target: obj })
          resolve()
        }, { crossOrigin: 'anonymous' } as any)
        setTimeout(() => {
          if (obj._svgColor === color) resolve()
        }, 0)
      })
    } catch (e) {
      console.error('[useCanvasEditor] applySelectedSvgColor failed:', e)
      throw e
    }
  }

  function getSelectedCropState(): ImageCropState {
    const obj = selectedObject.value as any
    return {
      left: Number(obj?._cropState?.left || 0),
      right: Number(obj?._cropState?.right || 0),
      top: Number(obj?._cropState?.top || 0),
      bottom: Number(obj?._cropState?.bottom || 0),
    }
  }

  function applySelectedImageCrop(state: ImageCropState) {
    if (!fabricCanvas.value || !selectedObject.value || !isSelectedCropTarget()) return
    const obj = selectedObject.value as any
    _rememberImageSourceSize(obj)

    const sourceW = Number(obj._sourceWidth || obj.width || 1)
    const sourceH = Number(obj._sourceHeight || obj.height || 1)
    const cropLeft = Math.round(sourceW * Math.max(0, Math.min(80, state.left)) / 100)
    const cropRight = Math.round(sourceW * Math.max(0, Math.min(80, state.right)) / 100)
    const cropTop = Math.round(sourceH * Math.max(0, Math.min(80, state.top)) / 100)
    const cropBottom = Math.round(sourceH * Math.max(0, Math.min(80, state.bottom)) / 100)
    const visibleW = Math.max(1, sourceW - cropLeft - cropRight)
    const visibleH = Math.max(1, sourceH - cropTop - cropBottom)

    obj.set({
      cropX: cropLeft,
      cropY: cropTop,
      width: visibleW,
      height: visibleH,
      originX: 'center',
      originY: 'center',
    })
    obj._cropState = { ...state }
    obj.setCoords()
    fabricCanvas.value.renderAll()
    fabricCanvas.value.fire('object:modified', { target: obj })
  }

  function resetSelectedImageCrop() {
    if (!fabricCanvas.value || !selectedObject.value || !isSelectedCropTarget()) return
    const obj = selectedObject.value as any
    _rememberImageSourceSize(obj)
    obj.set({
      cropX: 0,
      cropY: 0,
      width: obj._sourceWidth || obj.width,
      height: obj._sourceHeight || obj.height,
      originX: 'center',
      originY: 'center',
    })
    obj._cropState = { left: 0, right: 0, top: 0, bottom: 0 }
    obj.setCoords()
    fabricCanvas.value.renderAll()
    fabricCanvas.value.fire('object:modified', { target: obj })
  }

  // 恢复主照片初始位置（左、上、右边缘保持 margin 像素）
  function resetPhotoPosition() {
    if (!fabricCanvas.value || !selectedObject.value) return
    const cvs = fabricCanvas.value
    const obj = selectedObject.value as any
    const photoInit = obj._photoInit as PhotoInitConfig | undefined
    if (!photoInit) return

    const margin = photoInit.margin ?? 20
    const canvasWidth = _logicalWidth || cvs.getWidth()
    const canvasHeight = _logicalHeight || cvs.getHeight()
    const availW = canvasWidth - margin * 2
    const availH = canvasHeight - margin
    const scale = Math.min(availW / (obj.width || 1), availH / (obj.height || 1))
    const imgW = (obj.width || 1) * scale
    const imgH = (obj.height || 1) * scale

    obj.set({
      scaleX: scale,
      scaleY: scale,
      left: margin + imgW / 2,
      top: margin + imgH / 2,
      originX: 'center',
      originY: 'center',
    })
    obj.setCoords()
    cvs.renderAll()
    cvs.fire('object:modified', { target: obj })
  }

  // 用指定边距重新调整主照片位置
  function resetPhotoPositionWithMargin(margin: number) {
    if (!fabricCanvas.value || !selectedObject.value) return
    const cvs = fabricCanvas.value
    const obj = selectedObject.value as any
    if (!obj._isMainPhoto) return

    // 更新存储的 margin 值
    if (obj._photoInit) {
      obj._photoInit.margin = margin
    }

    const canvasWidth = _logicalWidth || cvs.getWidth()
    const canvasHeight = _logicalHeight || cvs.getHeight()
    const availW = canvasWidth - margin * 2
    const availH = canvasHeight - margin
    const scale = Math.min(availW / (obj.width || 1), availH / (obj.height || 1))
    const imgW = (obj.width || 1) * scale
    const imgH = (obj.height || 1) * scale

    obj.set({
      scaleX: scale,
      scaleY: scale,
      left: margin + imgW / 2,
      top: margin + imgH / 2,
      originX: 'center',
      originY: 'center',
    })
    obj.setCoords()
    cvs.renderAll()
    cvs.fire('object:modified', { target: obj })
  }

  // 销毁画布
  function dispose() {
    if (fabricCanvas.value) {
      fabricCanvas.value.dispose()
      fabricCanvas.value = null
      isReady.value = false
    }
  }

  onUnmounted(() => {
    dispose()
  })

  return {
    fabricCanvas,
    isReady,
    selectedObject,
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
    dispose,
  }
}
