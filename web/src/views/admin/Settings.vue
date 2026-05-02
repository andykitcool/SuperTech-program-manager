<template>
  <div>
    <h2 style="margin-bottom: 24px">系统设置</h2>
    <a-card title="云存储配置" style="margin-bottom: 16px">
      <a-tabs v-model:activeKey="activeProvider" @change="onProviderChange">
        <a-tab-pane key="aliyun" tab="阿里云 OSS">
          <a-form layout="vertical" style="max-width: 500px">
            <a-form-item label="启用状态">
              <a-switch
                v-model:checked="storageConfig.enabled"
                checked-children="启用"
                un-checked-children="停用"
              />
            </a-form-item>
            <a-form-item label="AccessKey ID">
              <a-input v-model:value="storageConfig.access_key_id" placeholder="请输入AccessKey ID" />
            </a-form-item>
            <a-form-item label="AccessKey Secret">
              <a-input-password v-model:value="storageConfig.access_key_secret" placeholder="请输入AccessKey Secret" />
            </a-form-item>
            <a-form-item label="Bucket">
              <a-input v-model:value="storageConfig.bucket" placeholder="请输入Bucket名称" />
            </a-form-item>
            <a-form-item label="Endpoint">
              <a-input v-model:value="storageConfig.endpoint" placeholder="例如：oss-cn-hangzhou.aliyuncs.com" />
            </a-form-item>
            <a-form-item label="Region">
              <a-input v-model:value="storageConfig.region" placeholder="例如：oss-cn-hangzhou" />
            </a-form-item>
          </a-form>
        </a-tab-pane>
        <a-tab-pane key="tencent" tab="腾讯云 COS">
          <a-form layout="vertical" style="max-width: 500px">
            <a-form-item label="启用状态">
              <a-switch
                v-model:checked="storageConfig.enabled"
                checked-children="启用"
                un-checked-children="停用"
              />
            </a-form-item>
            <a-form-item label="SecretId">
              <a-input v-model:value="storageConfig.secret_id" placeholder="请输入SecretId" />
            </a-form-item>
            <a-form-item label="SecretKey">
              <a-input-password v-model:value="storageConfig.secret_key" placeholder="请输入SecretKey" />
            </a-form-item>
            <a-form-item label="Bucket">
              <a-input v-model:value="storageConfig.bucket" placeholder="请输入Bucket名称" />
            </a-form-item>
            <a-form-item label="Region">
              <a-input v-model:value="storageConfig.region" placeholder="例如：ap-guangzhou" />
            </a-form-item>
          </a-form>
        </a-tab-pane>
        <a-tab-pane key="qiniu" tab="七牛云">
          <a-form layout="vertical" style="max-width: 500px">
            <a-form-item label="启用状态">
              <a-switch
                v-model:checked="storageConfig.enabled"
                checked-children="启用"
                un-checked-children="停用"
              />
            </a-form-item>
            <a-form-item label="AccessKey">
              <a-input v-model:value="storageConfig.access_key" placeholder="请输入AccessKey" />
            </a-form-item>
            <a-form-item label="SecretKey">
              <a-input-password v-model:value="storageConfig.secret_key" placeholder="请输入SecretKey" />
            </a-form-item>
            <a-form-item label="Bucket">
              <a-input v-model:value="storageConfig.bucket" placeholder="请输入Bucket名称" />
            </a-form-item>
            <a-form-item label="域名">
              <a-input v-model:value="storageConfig.domain" placeholder="例如：https://cdn.example.com" />
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>
      <a-divider />
      <a-space>
        <a-button type="primary" @click="saveConfig" :loading="saving">保存配置</a-button>
        <a-button @click="testConnection" :loading="testing">测试连接</a-button>
      </a-space>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'

const activeProvider = ref('aliyun')
const saving = ref(false)
const testing = ref(false)

type StorageConfig = Record<string, string | boolean>

const defaultConfigs: Record<string, StorageConfig> = {
  aliyun: { enabled: false, access_key_id: '', access_key_secret: '', bucket: '', endpoint: '', region: 'oss-cn-hangzhou' },
  tencent: { enabled: false, secret_id: '', secret_key: '', bucket: '', region: 'ap-guangzhou' },
  qiniu: { enabled: false, access_key: '', secret_key: '', bucket: '', domain: '' },
}

const storageConfig = reactive<StorageConfig>({ ...defaultConfigs.aliyun })

const onProviderChange = () => {
  loadConfig(activeProvider.value)
}

const loadConfig = async (provider: string) => {
  try {
    const res = await request.get(`/settings/${provider}_config`)
    if (res.data?.value) {
      const parsed = JSON.parse(res.data.value)
      const enabled = parsed.enabled ?? Boolean(parsed.bucket)
      Object.assign(storageConfig, defaultConfigs[provider], parsed, { enabled })
    } else {
      Object.assign(storageConfig, defaultConfigs[provider])
    }
  } catch {
    Object.assign(storageConfig, defaultConfigs[provider])
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await request.put(`/settings/${activeProvider.value}_config`, {
      value: JSON.stringify({ ...storageConfig }),
    })
    message.success('配置保存成功')
  } catch {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

const testConnection = async () => {
  testing.value = true
  try {
    const res = await request.post('/settings/storage/test', { provider: activeProvider.value })
    if (res.data.success) {
      message.success('连接测试成功')
    } else {
      message.error(`连接失败：${res.data.message}`)
    }
  } catch (e: any) {
    message.error('连接测试失败')
  } finally {
    testing.value = false
  }
}

const providers = ['aliyun', 'tencent', 'qiniu']

const detectProvider = async (): Promise<string> => {
  for (const p of providers) {
    try {
      const res = await request.get(`/settings/${p}_config`)
      if (res.data?.value) {
        const parsed = JSON.parse(res.data.value)
        const enabled = parsed.enabled ?? Boolean(parsed.bucket)
        if (enabled && parsed.bucket) return p
      }
    } catch { /* ignore */ }
  }
  return 'aliyun'
}

onMounted(async () => {
  const detected = await detectProvider()
  activeProvider.value = detected
  loadConfig(detected)
})
</script>
