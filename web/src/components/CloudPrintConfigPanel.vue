<template>
  <div class="cloud-print-panel">
    <div class="cloud-layout">
      <div class="cloud-form">
        <a-alert
          class="info-alert"
          type="info"
          show-icon
          message="蓝阔云打印配置"
          description="配置设备凭证、默认纸张和高级打印参数。活动打印纸张由所选打印模版决定。"
        />

        <a-form layout="vertical" class="settings-form">
          <section class="form-section">
            <div class="section-title">服务凭证</div>
            <a-row :gutter="16">
              <a-col :xs="24" :md="8">
                <a-form-item label="启用云打印">
                  <a-switch v-model:checked="printConfig.enabled" checked-children="启用" un-checked-children="停用" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="服务商">
                  <a-input v-model:value="printConfig.providerName" disabled />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="API 服务">
                  <a-input v-model:value="printConfig.apiBaseUrl" placeholder="https://cloud.liankenet.com" />
                </a-form-item>
              </a-col>
              <a-col :xs="24">
                <a-form-item label="ApiKey">
                  <a-input-password v-model:value="printConfig.ApiKey" placeholder="开放平台申请的开发者 ApiKey" />
                </a-form-item>
              </a-col>
            </a-row>
          </section>

          <section class="form-section">
            <div class="section-title">设备与打印机</div>
            <a-row :gutter="16">
              <a-col :xs="24" :md="8">
                <a-form-item label="deviceId">
                  <a-input v-model:value="printConfig.deviceId" placeholder="从云盒二维码解析获得" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="deviceKey">
                  <a-input-password v-model:value="printConfig.deviceKey" placeholder="从云盒二维码解析获得" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="devicePort">
                  <a-select v-model:value="printConfig.devicePort" :options="devicePortOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="printerType">
                  <a-select v-model:value="printConfig.printerType" :options="printerTypeOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="printerModel">
                  <a-input v-model:value="printConfig.printerModel" placeholder="printer_list 返回的 driver_name" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="targetIp">
                  <a-input v-model:value="printConfig.targetIp" placeholder="局域网打印机 IP，可选" />
                </a-form-item>
              </a-col>
            </a-row>
          </section>

          <section class="form-section">
            <div class="section-title">默认打印参数</div>
            <a-row :gutter="16">
              <a-col :xs="24" :md="8">
                <a-form-item label="纸张尺寸 dmPaperSize">
                  <a-select v-model:value="printConfig.dmPaperSize" :options="paperSizeOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="打印方向 dmOrientation">
                  <a-select v-model:value="printConfig.dmOrientation" :options="orientationOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="打印份数 dmCopies">
                  <a-input-number v-model:value="printConfig.dmCopies" :min="1" :max="999" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="打印颜色 dmColor">
                  <a-select v-model:value="printConfig.dmColor" :options="colorOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="双面打印 dmDuplex">
                  <a-select v-model:value="printConfig.dmDuplex" :options="duplexOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="缩放 jpScale">
                  <a-select v-model:value="printConfig.jpScale" :options="scaleOptions" />
                </a-form-item>
              </a-col>
              <a-col v-if="printConfig.dmPaperSize === '0'" :xs="24" :md="8">
                <a-form-item label="自定义纸宽（0.1mm）">
                  <a-input-number v-model:value="printConfig.dmPaperWidth" :min="1" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col v-if="printConfig.dmPaperSize === '0'" :xs="24" :md="8">
                <a-form-item label="自定义纸高（0.1mm）">
                  <a-input-number v-model:value="printConfig.dmPaperLength" :min="1" style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>
          </section>

          <section class="form-section">
            <div class="section-title">高级选项</div>
            <a-row :gutter="16">
              <a-col :xs="24" :md="8">
                <a-form-item label="HTML 转换内核">
                  <a-select v-model:value="printConfig.htmlKernel" :options="htmlKernelOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="自动对齐 jpAutoAlign">
                  <a-select v-model:value="printConfig.jpAutoAlign" :options="alignOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="打印质量 dmPrintQuality">
                  <a-select v-model:value="printConfig.dmPrintQuality" :options="qualityOptions" allow-clear />
                </a-form-item>
              </a-col>
              <a-col v-if="effectiveMediaTypeOptions.length" :xs="24" :md="8">
                <a-form-item label="介质类型 dmMediaType">
                  <a-select v-model:value="printConfig.dmMediaType" :options="effectiveMediaTypeOptions" allow-clear />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="连续错误上限">
                  <a-input-number v-model:value="printConfig.errLimitNum" :min="1" :max="30" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="16">
                <a-form-item label="打印结果回调 callbackUrl">
                  <a-input v-model:value="printConfig.callbackUrl" placeholder="必须为 https 链接，留空则轮询任务状态" />
                </a-form-item>
              </a-col>
              <a-col :xs="12" :md="6">
                <a-form-item label="拦截设备异常">
                  <a-switch v-model:checked="printConfig.reportDeviceStatus" />
                </a-form-item>
              </a-col>
              <a-col :xs="12" :md="6">
                <a-form-item label="拦截打印机异常">
                  <a-switch v-model:checked="printConfig.reportPrinterStatus" />
                </a-form-item>
              </a-col>
              <a-col :xs="12" :md="6">
                <a-form-item label="文档逆序">
                  <a-switch v-model:checked="printConfig.pdfRev" />
                </a-form-item>
              </a-col>
              <a-col :xs="12" :md="6">
                <a-form-item label="自动旋转">
                  <a-switch v-model:checked="printConfig.jpAutoRotate" />
                </a-form-item>
              </a-col>
            </a-row>
          </section>
        </a-form>

        <div class="card-actions">
          <a-space>
            <a-button type="primary" :loading="saving" @click="savePrintConfig">
              <template #icon><SaveOutlined /></template>
              保存云打印配置
            </a-button>
            <a-button href="https://documenter.getpostman.com/view/1758872/SWE83H6u?version=latest" target="_blank">
              <template #icon><LinkOutlined /></template>
              查看开发文档
            </a-button>
          </a-space>
        </div>
      </div>

      <aside class="printer-inspector">
        <div class="printer-inspector-head">
          <div>
            <span class="inspector-title">
              <PrinterOutlined />
              打印机状态
            </span>
            <div class="inspector-subtitle">
              在线 {{ printerInfo.online_printers.length }} / 总计 {{ printerInfo.printers.length }}
            </div>
          </div>
          <a-button size="small" :loading="loadingPrinterInfo" @click="loadPrinterInfo(true)">
            <template #icon><ReloadOutlined /></template>
          </a-button>
        </div>

        <a-spin :spinning="loadingPrinterInfo">
          <a-alert v-if="printerInfoError" class="printer-alert" type="warning" show-icon :message="printerInfoError" />
          <a-empty v-else-if="!printerInfo.printers.length" class="printer-empty" description="暂无打印机信息" />
          <div v-else>
            <div class="printer-list">
              <button
                v-for="printer in printerInfo.online_printers"
                :key="printerKey(printer)"
                type="button"
                class="printer-row"
                :class="{ active: printerKey(printer) === selectedPrinterKey }"
                @click="selectPrinter(printer)"
              >
                <span>
                  <strong>{{ printer.printer_name || printer.driver_name }}</strong>
                  <small>{{ printer.driver_name }}</small>
                </span>
                <a-tag :color="printerStatusColor(printer)">{{ printer.status_label }}</a-tag>
              </button>
            </div>

            <a-descriptions v-if="printerInfo.selected_printer" class="printer-desc" size="small" :column="1" bordered>
              <a-descriptions-item label="printerModel">{{ printerInfo.selected_model || '-' }}</a-descriptions-item>
              <a-descriptions-item label="devicePort">{{ printerInfo.selected_printer.port === 631 ? '1（网络打印机）' : printerInfo.selected_printer.port || '-' }}</a-descriptions-item>
              <a-descriptions-item label="printer_state">{{ printerInfo.selected_printer.printer_state || printerInfo.selected_printer.status_label || '-' }}</a-descriptions-item>
              <a-descriptions-item label="support_status">{{ printerInfo.selected_printer.support_status ? '支持' : '未声明' }}</a-descriptions-item>
            </a-descriptions>

            <div v-if="Object.keys(printerInfo.printer_params || {}).length" class="printer-params">
              <div class="params-head">
                <span>打印机参数</span>
                <a-tag v-if="printerInfo.params_cached" color="blue">缓存</a-tag>
                <a-tag v-else color="green">已刷新</a-tag>
              </div>
              <div class="params-grid">
                <div><span>纸张</span><strong>{{ optionCount(printerInfo.printer_params?.Capabilities?.Papers) }}</strong></div>
                <div><span>介质</span><strong>{{ mediaTypeOptions.length }}</strong></div>
                <div><span>DPI</span><strong>{{ printerDpi }}</strong></div>
                <div><span>色彩</span><strong>{{ optionCount(printerInfo.printer_params?.Capabilities?.Color) }}</strong></div>
              </div>
              <div v-if="mediaTypeOptions.length" class="media-options">
                <a-tag v-for="item in mediaTypeOptions.slice(0, 8)" :key="item.value">{{ item.label }}</a-tag>
              </div>
            </div>
          </div>
        </a-spin>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { LinkOutlined, PrinterOutlined, ReloadOutlined, SaveOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'
import { materialApi } from '@/api/admin'

interface OptionItem {
  label: string
  value: string
}

interface LankuoPrintConfig {
  enabled: boolean
  provider: 'lankuo'
  providerName: string
  apiBaseUrl: string
  ApiKey: string
  deviceId: string
  deviceKey: string
  devicePort: string
  printerType: string
  printerModel: string
  targetIp: string
  dmPaperSize: string
  dmOrientation: string
  dmCopies: number
  dmColor: string
  dmDuplex: string
  dmDefaultSource: string
  dmMediaType: string
  dmPaperLength: number
  dmPaperWidth: number
  dmPrintQuality: string
  jpScale: string
  jpAutoAlign: string
  jpPageRange: string
  htmlKernel: string
  callbackUrl: string
  reportDeviceStatus: boolean
  reportPrinterStatus: boolean
  errLimitNum: number
  pdfRev: boolean
  jpAutoRotate: boolean
}

interface PrinterItem {
  [key: string]: any
  driver_name: string
  printer_name?: string
  printer_state?: string
  port?: number | string
  ip_addr?: string
  support_status?: boolean
  is_online?: boolean
  status_label?: string
  status_level?: string
}

const defaultPrintConfig: LankuoPrintConfig = {
  enabled: false,
  provider: 'lankuo',
  providerName: '蓝阔（链科云打印 v3）',
  apiBaseUrl: 'https://cloud.liankenet.com',
  ApiKey: '',
  deviceId: '',
  deviceKey: '',
  devicePort: '1',
  printerType: '1',
  printerModel: '',
  targetIp: '',
  dmPaperSize: '9',
  dmOrientation: '1',
  dmCopies: 1,
  dmColor: '2',
  dmDuplex: '1',
  dmDefaultSource: '',
  dmMediaType: '',
  dmPaperLength: 300,
  dmPaperWidth: 200,
  dmPrintQuality: '',
  jpScale: 'fit',
  jpAutoAlign: 'z5',
  jpPageRange: '',
  htmlKernel: 'chrometopdf',
  callbackUrl: '',
  reportDeviceStatus: true,
  reportPrinterStatus: true,
  errLimitNum: 30,
  pdfRev: false,
  jpAutoRotate: false,
}

const printConfig = reactive<LankuoPrintConfig>({ ...defaultPrintConfig })
const saving = ref(false)
const loadingPrinterInfo = ref(false)
const printerInfoError = ref('')
const selectedPrinterKey = ref('')
const mediaTypeOptions = ref<OptionItem[]>([])
const printerInfo = reactive({
  configured: false,
  printers: [] as PrinterItem[],
  online_printers: [] as PrinterItem[],
  selected_printer: null as PrinterItem | null,
  selected_model: '',
  printer_params: {} as Record<string, any>,
  params_cached: false,
})

const devicePortOptions: OptionItem[] = [
  { label: 'USB1 / 网络打印机默认', value: '1' },
  { label: 'USB2', value: '2' },
  { label: 'USB3', value: '3' },
  { label: 'USB4', value: '4' },
]
const printerTypeOptions: OptionItem[] = [{ label: '打印机', value: '1' }]
const paperSizeOptions: OptionItem[] = [
  { label: 'A4（9）', value: '9' },
  { label: 'A5（11）', value: '11' },
  { label: 'A6（70）', value: '70' },
  { label: 'Letter（1）', value: '1' },
  { label: 'Legal（5）', value: '5' },
  { label: '自定义尺寸（0）', value: '0' },
]
const orientationOptions: OptionItem[] = [
  { label: '纵向（1）', value: '1' },
  { label: '横向（2）', value: '2' },
]
const colorOptions: OptionItem[] = [
  { label: '黑白（1）', value: '1' },
  { label: '彩色（2）', value: '2' },
]
const duplexOptions: OptionItem[] = [
  { label: '关闭（1）', value: '1' },
  { label: '长边翻转（2）', value: '2' },
  { label: '短边翻转（3）', value: '3' },
]
const scaleOptions: OptionItem[] = [
  { label: '适配纸张', value: 'fit' },
  { label: '原始尺寸', value: 'none' },
  { label: '填满纸张', value: 'fill' },
]
const htmlKernelOptions: OptionItem[] = [
  { label: 'Chrome 转 PDF', value: 'chrometopdf' },
  { label: '默认内核', value: 'default' },
]
const alignOptions: OptionItem[] = [
  { label: '居中（z5）', value: 'z5' },
  { label: '左上（z1）', value: 'z1' },
  { label: '右下（z9）', value: 'z9' },
]
const qualityOptions: OptionItem[] = [
  { label: '高质量', value: 'high' },
  { label: '普通', value: 'normal' },
  { label: '草稿', value: 'draft' },
]

const effectiveMediaTypeOptions = computed(() => {
  const options = [...mediaTypeOptions.value]
  const current = String(printConfig.dmMediaType || '')
  if (current && !options.some(item => item.value === current)) {
    options.unshift({ label: `当前值 ${current}`, value: current })
  }
  return options
})

const printerDpi = computed(() => {
  const ctx = printerInfo.printer_params?.DeviceContext || {}
  const devMode = printerInfo.printer_params?.DevMode || {}
  return ctx.LogPixelsX && ctx.LogPixelsY
    ? `${ctx.LogPixelsX}x${ctx.LogPixelsY}`
    : String(devMode.PrintQuality || '-')
})

function resetReactive<T extends Record<string, any>>(target: T, source: Partial<T>) {
  Object.keys(target).forEach(key => delete target[key])
  Object.assign(target, source)
}

function removeUrlFileExt(config: Record<string, any>) {
  const cleaned = { ...config }
  delete cleaned.urlFileExt
  return cleaned
}

function optionCount(value: any) {
  if (Array.isArray(value)) return value.length
  if (value && typeof value === 'object') return Object.keys(value).length
  return 0
}

function printerKey(printer: PrinterItem) {
  return `${printer.driver_name || printer.printer_name || 'printer'}-${printer.port || ''}-${printer.ip_addr || ''}`
}

function printerStatusColor(printer: PrinterItem) {
  if (printer.status_level === 'online') return 'green'
  if (printer.status_level === 'busy') return 'blue'
  if (printer.status_level === 'warning') return 'orange'
  return printer.is_online ? 'green' : 'default'
}

function applyPrinterInfo(next: any) {
  Object.assign(printerInfo, {
    configured: !!next?.configured,
    printers: next?.printers || [],
    online_printers: next?.online_printers || [],
    selected_printer: next?.selected_printer || null,
    selected_model: next?.selected_model || '',
    printer_params: next?.printer_params || {},
    params_cached: !!next?.params_cached,
  })
  selectedPrinterKey.value = next?.selected_printer ? printerKey(next.selected_printer) : ''
  mediaTypeOptions.value = next?.media_type_options || []
}

async function loadPrintConfig() {
  try {
    const settings = (await materialApi.getPrintSettings() as any)?.data || {}
    resetReactive(printConfig, {
      ...defaultPrintConfig,
      ...(settings.lankuo_print_config || {}),
      provider: 'lankuo',
      providerName: '蓝阔（链科云打印 v3）',
    })
    await loadPrinterInfo(false)
  } catch {
    message.error('加载云打印配置失败')
  }
}

async function loadPrinterInfo(refresh = false, printerModel?: string) {
  if (!printConfig.ApiKey || !printConfig.deviceId || !printConfig.deviceKey) {
    printerInfoError.value = '请先配置 ApiKey、deviceId 和 deviceKey'
    return
  }
  loadingPrinterInfo.value = true
  printerInfoError.value = ''
  try {
    const res = await request.get('/settings/lankuo/printers', {
      params: {
        refresh: refresh ? 1 : 0,
        printer_model: printerModel || printConfig.printerModel || undefined,
      },
    })
    applyPrinterInfo(res.data || {})
    const selected = res.data?.selected_printer
    if (selected?.driver_name) {
      printConfig.printerModel = selected.driver_name
      printConfig.devicePort = String(selected.port === 631 ? 1 : selected.port || printConfig.devicePort || '1')
      if (selected.ip_addr) printConfig.targetIp = selected.ip_addr
    }
    if (res.data?.message) printerInfoError.value = res.data.message
  } catch (error: any) {
    printerInfoError.value = error?.response?.data?.detail || '获取打印机信息失败'
  } finally {
    loadingPrinterInfo.value = false
  }
}

async function selectPrinter(printer: PrinterItem) {
  selectedPrinterKey.value = printerKey(printer)
  printConfig.printerModel = printer.driver_name || printConfig.printerModel
  printConfig.devicePort = String(printer.port === 631 ? 1 : printer.port || printConfig.devicePort || '1')
  if (printer.ip_addr) printConfig.targetIp = printer.ip_addr
  await loadPrinterInfo(false, printConfig.printerModel)
}

async function savePrintConfig() {
  saving.value = true
  try {
    await materialApi.updatePrintSettings({
      lankuo_print_config: removeUrlFileExt({ ...printConfig }),
    })
    message.success('云打印配置已保存')
    await loadPrinterInfo(false)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '保存云打印配置失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadPrintConfig)
</script>

<style scoped>
.cloud-print-panel {
  width: 100%;
}

.cloud-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: start;
}

.cloud-form,
.printer-inspector {
  background: #fff;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 18px;
}

.info-alert {
  margin-bottom: 16px;
}

.form-section {
  margin-bottom: 18px;
}

.section-title {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}

.printer-inspector {
  position: sticky;
  top: 16px;
}

.printer-inspector-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.inspector-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #1f2937;
}

.inspector-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: #8c8c8c;
}

.printer-alert,
.printer-empty {
  margin: 12px 0;
}

.printer-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.printer-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fafafa;
  padding: 10px;
  text-align: left;
  cursor: pointer;
}

.printer-row.active {
  border-color: #1677ff;
  background: #e6f4ff;
}

.printer-row strong,
.printer-row small {
  display: block;
}

.printer-row strong {
  color: #1f2937;
}

.printer-row small {
  color: #8c8c8c;
}

.printer-desc,
.printer-params {
  margin-top: 14px;
}

.params-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-weight: 600;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.params-grid div {
  border-radius: 8px;
  background: #f7f8fb;
  padding: 10px;
}

.params-grid span,
.params-grid strong {
  display: block;
}

.params-grid span {
  font-size: 12px;
  color: #8c8c8c;
}

.params-grid strong {
  margin-top: 3px;
  color: #1f2937;
}

.media-options {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 1100px) {
  .cloud-layout {
    grid-template-columns: 1fr;
  }

  .printer-inspector {
    position: static;
  }
}
</style>
