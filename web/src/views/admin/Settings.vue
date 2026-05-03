<template>
  <div class="settings-page">
    <div class="settings-header">
      <div>
        <h2>系统设置</h2>
        <p>集中维护云存储、微信服务号和云打印参数。</p>
      </div>
    </div>

    <a-card class="settings-tabs-card" :bordered="false">
      <a-tabs class="settings-tabs" default-active-key="storage">
        <a-tab-pane key="storage" tab="云存储配置">
          <div class="tab-panel-head">
            <span class="card-title">
              <CloudServerOutlined />
              云存储配置
            </span>
            <a-tag color="blue">{{ activeProviderLabel }}</a-tag>
          </div>

          <a-tabs v-model:activeKey="activeProvider" @change="onProviderChange">
            <a-tab-pane key="aliyun" tab="阿里云 OSS">
              <a-form layout="vertical" class="settings-form">
                <a-row :gutter="16">
                  <a-col :xs="24" :md="12">
                    <a-form-item label="启用状态">
                      <a-switch v-model:checked="storageConfig.enabled" checked-children="启用" un-checked-children="停用" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Region">
                      <a-input v-model:value="storageConfig.region" placeholder="例如：oss-cn-hangzhou" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="AccessKey ID">
                      <a-input v-model:value="storageConfig.access_key_id" placeholder="请输入 AccessKey ID" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="AccessKey Secret">
                      <a-input-password v-model:value="storageConfig.access_key_secret" placeholder="请输入 AccessKey Secret" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Bucket">
                      <a-input v-model:value="storageConfig.bucket" placeholder="请输入 Bucket 名称" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Endpoint">
                      <a-input v-model:value="storageConfig.endpoint" placeholder="例如：oss-cn-hangzhou.aliyuncs.com" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="tencent" tab="腾讯云 COS">
              <a-form layout="vertical" class="settings-form">
                <a-row :gutter="16">
                  <a-col :xs="24" :md="12">
                    <a-form-item label="启用状态">
                      <a-switch v-model:checked="storageConfig.enabled" checked-children="启用" un-checked-children="停用" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Region">
                      <a-input v-model:value="storageConfig.region" placeholder="例如：ap-guangzhou" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="SecretId">
                      <a-input v-model:value="storageConfig.secret_id" placeholder="请输入 SecretId" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="SecretKey">
                      <a-input-password v-model:value="storageConfig.secret_key" placeholder="请输入 SecretKey" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Bucket">
                      <a-input v-model:value="storageConfig.bucket" placeholder="请输入 Bucket 名称" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="qiniu" tab="七牛云">
              <a-form layout="vertical" class="settings-form">
                <a-row :gutter="16">
                  <a-col :xs="24" :md="12">
                    <a-form-item label="启用状态">
                      <a-switch v-model:checked="storageConfig.enabled" checked-children="启用" un-checked-children="停用" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Bucket">
                      <a-input v-model:value="storageConfig.bucket" placeholder="请输入 Bucket 名称" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="AccessKey">
                      <a-input v-model:value="storageConfig.access_key" placeholder="请输入 AccessKey" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="SecretKey">
                      <a-input-password v-model:value="storageConfig.secret_key" placeholder="请输入 SecretKey" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="访问域名">
                      <a-input v-model:value="storageConfig.domain" placeholder="例如：https://cdn.example.com" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </a-tab-pane>
          </a-tabs>

          <div class="card-actions">
            <a-space>
              <a-button type="primary" @click="saveStorageConfig" :loading="savingStorage">
                <template #icon><SaveOutlined /></template>
                保存云存储配置
              </a-button>
              <a-button @click="testConnection" :loading="testingStorage">
                <template #icon><ExperimentOutlined /></template>
                测试连接
              </a-button>
            </a-space>
          </div>
        </a-tab-pane>

        <a-tab-pane key="wechat" tab="微信服务号配置">
          <div class="tab-panel-head">
            <span class="card-title">
              <WechatOutlined />
              微信服务号配置
            </span>
            <a-tag :color="wechatConfig.enabled ? 'green' : 'default'">
              {{ wechatConfig.enabled ? '已启用' : '未启用' }}
            </a-tag>
          </div>

          <a-alert
            class="info-alert"
            type="info"
            show-icon
            message="用于微信浏览器内获取观众 openid、头像和昵称"
            description="请在微信公众平台网页授权域名中配置当前访问域名；授权回调页使用 /p/index、/p/{活动ID} 和 /p/{节目token}。"
          />

          <a-form layout="vertical" class="settings-form">
            <a-row :gutter="16">
              <a-col :xs="24" :md="8">
                <a-form-item label="启用微信授权">
                  <a-switch v-model:checked="wechatConfig.enabled" checked-children="启用" un-checked-children="停用" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="AppID">
                  <a-input v-model:value="wechatConfig.appid" placeholder="请输入微信服务号 AppID" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="网页授权 Scope">
                  <a-select v-model:value="wechatConfig.scope" :options="wechatScopeOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="16">
                <a-form-item label="AppSecret">
                  <a-input-password v-model:value="wechatConfig.appsecret" placeholder="请输入微信服务号 AppSecret" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="State">
                  <a-input v-model:value="wechatConfig.state" placeholder="supertech" />
                </a-form-item>
              </a-col>
            </a-row>
          </a-form>

          <div class="card-actions">
            <a-button type="primary" @click="saveWechatConfig" :loading="savingWechat">
              <template #icon><SaveOutlined /></template>
              保存微信配置
            </a-button>
          </div>
        </a-tab-pane>

        <a-tab-pane key="print" tab="云打印配置">
          <div class="tab-panel-head">
            <span class="card-title">
              <PrinterOutlined />
              云打印配置
            </span>
            <a-tag color="green">蓝阔</a-tag>
          </div>

          <a-alert
            class="info-alert"
            type="info"
            show-icon
            message="按蓝阔云打印文档设计"
            description="API 域名使用 cloud.liankenet.com；每个请求需要在 Header 中携带 ApiKey；设备凭证来自云盒二维码中的 deviceId 与 deviceKey。"
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
                  <a-form-item label="API 服务器">
                    <a-input v-model:value="printConfig.apiBaseUrl" placeholder="https://cloud.liankenet.com" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="24">
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
                  <a-form-item label="deviceId（云账号）">
                    <a-input v-model:value="printConfig.deviceId" placeholder="从云盒二维码解析获得" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="deviceKey（云密码）">
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
                    <a-input v-model:value="printConfig.printerModel" placeholder="对应 printer_list 返回的 driver_name" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="targetIp（网络打印机）">
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
                  <a-form-item label="自定义纸宽 dmPaperWidth（0.1mm）">
                    <a-input-number v-model:value="printConfig.dmPaperWidth" :min="1" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col v-if="printConfig.dmPaperSize === '0'" :xs="24" :md="8">
                  <a-form-item label="自定义纸高 dmPaperLength（0.1mm）">
                    <a-input-number v-model:value="printConfig.dmPaperLength" :min="1" style="width: 100%" />
                  </a-form-item>
                </a-col>
              </a-row>
            </section>

            <section class="form-section">
              <div class="section-title">高级选项</div>
              <a-row :gutter="16">
                <a-col :xs="24" :md="8">
                  <a-form-item label="文件链接后缀 urlFileExt">
                    <a-select v-model:value="printConfig.urlFileExt" :options="fileExtOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="HTML 转换内核 htmlKernel">
                    <a-select v-model:value="printConfig.htmlKernel" :options="htmlKernelOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="自动对齐 jpAutoAlign">
                    <a-select v-model:value="printConfig.jpAutoAlign" :options="alignOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="页码范围 jpPageRange">
                    <a-input v-model:value="printConfig.jpPageRange" placeholder="例如：1,2,5-10；留空为全部" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="打印质量 dmPrintQuality">
                    <a-select v-model:value="printConfig.dmPrintQuality" :options="qualityOptions" allow-clear />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="连续错误上限 errLimitNum">
                    <a-input-number v-model:value="printConfig.errLimitNum" :min="1" :max="30" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="24">
                  <a-form-item label="打印结果回调 callbackUrl">
                    <a-input v-model:value="printConfig.callbackUrl" placeholder="必须为 https 链接，留空则轮询任务状态" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="拦截设备异常">
                    <a-switch v-model:checked="printConfig.reportDeviceStatus" checked-children="开启" un-checked-children="关闭" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="拦截打印机异常">
                    <a-switch v-model:checked="printConfig.reportPrinterStatus" checked-children="开启" un-checked-children="关闭" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="文档逆序">
                    <a-switch v-model:checked="printConfig.pdfRev" checked-children="开启" un-checked-children="关闭" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="自动旋转">
                    <a-switch v-model:checked="printConfig.jpAutoRotate" checked-children="开启" un-checked-children="关闭" />
                  </a-form-item>
                </a-col>
              </a-row>
            </section>
          </a-form>

          <div class="card-actions">
            <a-space>
              <a-button type="primary" @click="savePrintConfig" :loading="savingPrint">
                <template #icon><SaveOutlined /></template>
                保存云打印配置
              </a-button>
              <a-button href="https://documenter.getpostman.com/view/1758872/SWE83H6u?version=latest" target="_blank">
                <template #icon><LinkOutlined /></template>
                查看开发文档
              </a-button>
            </a-space>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  CloudServerOutlined,
  ExperimentOutlined,
  LinkOutlined,
  PrinterOutlined,
  SaveOutlined,
  WechatOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'

type SettingValue = string | number | boolean | null
type StorageConfig = Record<string, SettingValue>

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
  urlFileExt: string
  callbackUrl: string
  reportDeviceStatus: boolean
  reportPrinterStatus: boolean
  errLimitNum: number
  pdfRev: boolean
  jpAutoRotate: boolean
}

interface WechatOfficialConfig {
  enabled: boolean
  appid: string
  appsecret: string
  scope: 'snsapi_userinfo' | 'snsapi_base'
  state: string
}

const activeProvider = ref('aliyun')
const savingStorage = ref(false)
const testingStorage = ref(false)
const savingPrint = ref(false)
const savingWechat = ref(false)

const storageProviderLabels: Record<string, string> = {
  aliyun: '阿里云 OSS',
  tencent: '腾讯云 COS',
  qiniu: '七牛云',
}

const defaultStorageConfigs: Record<string, StorageConfig> = {
  aliyun: {
    enabled: false,
    access_key_id: '',
    access_key_secret: '',
    bucket: '',
    endpoint: '',
    region: 'oss-cn-hangzhou',
  },
  tencent: {
    enabled: false,
    secret_id: '',
    secret_key: '',
    bucket: '',
    region: 'ap-guangzhou',
  },
  qiniu: {
    enabled: false,
    access_key: '',
    secret_key: '',
    bucket: '',
    domain: '',
  },
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
  urlFileExt: '.pdf',
  callbackUrl: '',
  reportDeviceStatus: true,
  reportPrinterStatus: true,
  errLimitNum: 30,
  pdfRev: false,
  jpAutoRotate: false,
}

const defaultWechatConfig: WechatOfficialConfig = {
  enabled: false,
  appid: '',
  appsecret: '',
  scope: 'snsapi_userinfo',
  state: 'supertech',
}

const storageConfig = reactive<StorageConfig>({ ...defaultStorageConfigs.aliyun })
const printConfig = reactive<LankuoPrintConfig>({ ...defaultPrintConfig })
const wechatConfig = reactive<WechatOfficialConfig>({ ...defaultWechatConfig })

const activeProviderLabel = computed(() => storageProviderLabels[activeProvider.value] || activeProvider.value)

const devicePortOptions: OptionItem[] = [
  { label: 'USB1 / 网络打印机默认', value: '1' },
  { label: 'USB2', value: '2' },
  { label: 'USB3', value: '3' },
  { label: 'USB4', value: '4' },
]

const printerTypeOptions: OptionItem[] = [
  { label: '打印机', value: '1' },
]

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
  { label: 'fit 自适应', value: 'fit' },
  { label: 'fitw 宽度优先', value: 'fitw' },
  { label: 'fith 高度优先', value: 'fith' },
  { label: 'fill 拉伸全图', value: 'fill' },
  { label: 'cover 自动裁剪铺满', value: 'cover' },
  { label: 'none 不缩放', value: 'none' },
]

const alignOptions: OptionItem[] = [
  { label: '左上 z1', value: 'z1' },
  { label: '中上 z2', value: 'z2' },
  { label: '右上 z3', value: 'z3' },
  { label: '左中 z4', value: 'z4' },
  { label: '居中 z5', value: 'z5' },
  { label: '右中 z6', value: 'z6' },
  { label: '左下 z7', value: 'z7' },
  { label: '中下 z8', value: 'z8' },
  { label: '右下 z9', value: 'z9' },
]

const fileExtOptions: OptionItem[] = [
  { label: '.pdf', value: '.pdf' },
  { label: '.jpg', value: '.jpg' },
  { label: '.jpeg', value: '.jpeg' },
  { label: '.png', value: '.png' },
  { label: '.html', value: '.html' },
  { label: '.docx', value: '.docx' },
  { label: '.xlsx', value: '.xlsx' },
]

const htmlKernelOptions: OptionItem[] = [
  { label: 'chrometopdf（推荐）', value: 'chrometopdf' },
  { label: 'wkhtmltopdf', value: 'wkhtmltopdf' },
  { label: 'wkhtml', value: 'wkhtml' },
]

const qualityOptions: OptionItem[] = [
  { label: '-1 最低质量', value: '-1' },
  { label: '-2 较低质量', value: '-2' },
  { label: '-3 较高质量', value: '-3' },
  { label: '-4 最高质量', value: '-4' },
]

const wechatScopeOptions: OptionItem[] = [
  { label: 'snsapi_userinfo（获取头像和昵称）', value: 'snsapi_userinfo' },
  { label: 'snsapi_base（只获取 openid）', value: 'snsapi_base' },
]

function resetReactive<T extends Record<string, any>>(target: T, value: T) {
  Object.keys(target).forEach(key => {
    delete target[key]
  })
  Object.assign(target, value)
}

async function loadSettingJSON<T>(key: string, fallback: T): Promise<T> {
  try {
    const res = await request.get(`/settings/${key}`)
    if (!res.data?.value) return fallback
    return { ...fallback, ...JSON.parse(res.data.value) }
  } catch {
    return fallback
  }
}

const onProviderChange = () => {
  loadStorageConfig(activeProvider.value)
}

const loadStorageConfig = async (provider: string) => {
  const fallback = defaultStorageConfigs[provider]
  const parsed = await loadSettingJSON<StorageConfig>(`${provider}_config`, fallback)
  const enabled = parsed.enabled ?? Boolean(parsed.bucket)
  resetReactive(storageConfig, { ...fallback, ...parsed, enabled })
}

const loadPrintConfig = async () => {
  const parsed = await loadSettingJSON<LankuoPrintConfig>('lankuo_print_config', defaultPrintConfig)
  resetReactive(printConfig, {
    ...defaultPrintConfig,
    ...parsed,
    provider: 'lankuo',
    providerName: '蓝阔（链科云打印 v3）',
    reportDeviceStatus: parsed.reportDeviceStatus ?? true,
    reportPrinterStatus: parsed.reportPrinterStatus ?? true,
  })
}

const loadWechatConfig = async () => {
  const parsed = await loadSettingJSON<WechatOfficialConfig>('wechat_official_account_config', defaultWechatConfig)
  resetReactive(wechatConfig, {
    ...defaultWechatConfig,
    ...parsed,
    scope: parsed.scope || 'snsapi_userinfo',
  })
}

const saveStorageConfig = async () => {
  savingStorage.value = true
  try {
    await request.put(`/settings/${activeProvider.value}_config`, {
      value: JSON.stringify({ ...storageConfig }),
    })
    message.success('云存储配置已保存')
  } catch {
    message.error('保存云存储配置失败')
  } finally {
    savingStorage.value = false
  }
}

const savePrintConfig = async () => {
  savingPrint.value = true
  try {
    await request.put('/settings/lankuo_print_config', {
      value: JSON.stringify({ ...printConfig }),
    })
    message.success('云打印配置已保存')
  } catch {
    message.error('保存云打印配置失败')
  } finally {
    savingPrint.value = false
  }
}

const saveWechatConfig = async () => {
  savingWechat.value = true
  try {
    await request.put('/settings/wechat_official_account_config', {
      value: JSON.stringify({ ...wechatConfig }),
    })
    message.success('微信服务号配置已保存')
  } catch {
    message.error('保存微信服务号配置失败')
  } finally {
    savingWechat.value = false
  }
}

const testConnection = async () => {
  testingStorage.value = true
  try {
    const res = await request.post('/settings/storage/test', { provider: activeProvider.value })
    if (res.data.success) {
      message.success('连接测试成功')
    } else {
      message.error(`连接失败：${res.data.message}`)
    }
  } catch {
    message.error('连接测试失败')
  } finally {
    testingStorage.value = false
  }
}

const providers = ['aliyun', 'tencent', 'qiniu']

const detectProvider = async (): Promise<string> => {
  for (const provider of providers) {
    try {
      const res = await request.get(`/settings/${provider}_config`)
      if (res.data?.value) {
        const parsed = JSON.parse(res.data.value)
        const enabled = parsed.enabled ?? Boolean(parsed.bucket)
        if (enabled && parsed.bucket) return provider
      }
    } catch {
      // keep scanning
    }
  }
  return 'aliyun'
}

onMounted(async () => {
  const detected = await detectProvider()
  activeProvider.value = detected
  await Promise.all([
    loadStorageConfig(detected),
    loadPrintConfig(),
    loadWechatConfig(),
  ])
})
</script>

<style scoped>
.settings-page {
  max-width: 1180px;
}

.settings-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 20px;
}

.settings-header h2 {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 650;
  color: #202124;
}

.settings-header p {
  margin: 0;
  color: #6b7280;
}

.settings-tabs-card {
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(24, 32, 54, 0.08);
}

.settings-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 22px;
}

.tab-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid #eef1f5;
}

.card-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #111827;
  font-size: 16px;
  font-weight: 650;
}

.settings-form {
  max-width: 980px;
}

.card-actions {
  margin-top: 4px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.info-alert {
  margin-bottom: 18px;
}

.form-section {
  margin-bottom: 22px;
}

.section-title {
  margin-bottom: 12px;
  color: #111827;
  font-size: 15px;
  font-weight: 650;
}
</style>
