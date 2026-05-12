<template>
  <div v-if="!authorized" class="wechat-auth-gate">
    <div class="auth-card">
      <div class="auth-icon">
        <svg viewBox="0 0 24 24" width="64" height="64" fill="#07C160">
          <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 0 1 .598.082l1.584.926a.272.272 0 0 0 .14.047c.134 0 .24-.11.24-.245 0-.06-.022-.12-.038-.173l-.327-1.233a.582.582 0 0 1-.023-.156.49.49 0 0 1 .201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-6.656-6.088V8.87l-.406-.012zm-2.53 2.66c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.97-.982zm4.844 0c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.969-.982z"/>
        </svg>
      </div>
      <h2>微信授权</h2>
      <p>为确保您能正常访问照片并使用下载/打印功能，请先完成微信授权</p>
      <a-button type="primary" size="large" block :loading="loading" @click="doAuth">
        微信一键授权
      </a-button>
      <p v-if="error" class="error-tip">{{ error }}</p>
      <p class="tip">授权后您的微信昵称和头像将用于识别身份，不会泄露其他信息</p>
    </div>
  </div>

  <div v-else class="auth-success">
    <slot :profile="profile" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { publicApi } from '@/api/admin'
import type { WechatProfile } from '@/api/admin'

const props = defineProps<{
  activityId: number
  redirectPath?: string
}>()

const emit = defineEmits<{
  authorized: [profile: WechatProfile]
}>()

const authorized = ref(false)
const loading = ref(false)
const error = ref('')
const profile = ref<WechatProfile | null>(null)
const activeWechatAppid = ref('')

const legacyProfileKey = 'wechat_profile'
const profileKey = () => `wechat_profile:${activeWechatAppid.value || 'unknown'}:${props.activityId}`

async function loadWechatConfig() {
  const wechatConfig = (await publicApi.getWechatConfig() as any)?.data
  if (!wechatConfig?.enabled) {
    error.value = '寰俊鎺堟潈鏈厤缃紝璇疯仈绯绘椿鍔ㄤ富鍔炴柟'
    return null
  }
  activeWechatAppid.value = wechatConfig.appid || ''
  return wechatConfig
}

async function checkExistingAuth() {
  const saved = activeWechatAppid.value ? localStorage.getItem(profileKey()) : null
  if (saved) {
    try {
      const data = JSON.parse(saved) as WechatProfile
      if (data.openid && (!data.appid || data.appid === activeWechatAppid.value)) {
        profile.value = data
        authorized.value = true
        emit('authorized', data)
        return true
      }
    } catch {}
  }
  localStorage.removeItem(legacyProfileKey)
  return false
}

async function doAuth() {
  loading.value = true
  error.value = ''

  try {
    const wechatConfig = (await publicApi.getWechatConfig() as any)?.data
    if (!wechatConfig?.enabled) {
      error.value = '微信授权未配置，请联系活动主办方'
      return
    }

    // 获取 OAuth URL - 微信回调直接到前端页面
    const baseUrl = window.location.origin
    const redirectPath = props.redirectPath || (window.location.pathname + window.location.search)
    const redirectUri = baseUrl + redirectPath

    const oauthRes = (await publicApi.getWechatOAuthUrl(redirectUri) as any)?.data
    window.location.href = oauthRes?.url || ''
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '获取授权地址失败，请重试'
  } finally {
    loading.value = false
  }
}

async function handleCallback() {
  const params = new URLSearchParams(window.location.search)
  const code = params.get('code')

  if (code) {
    loading.value = true
    try {
      const res = await publicApi.resolveWechatProfile(code, props.activityId)
      const data = (res as any)?.data || res
      data.appid = data.appid || activeWechatAppid.value
      profile.value = data
      authorized.value = true
      if (activeWechatAppid.value) {
        localStorage.setItem(profileKey(), JSON.stringify(data))
      }
      localStorage.removeItem(legacyProfileKey)
      emit('authorized', data)

      // 移除 URL 中的 code 参数
      const cleanUrl = window.location.origin + (props.redirectPath || window.location.pathname)
      window.history.replaceState({}, '', cleanUrl)
    } catch (e: any) {
      error.value = e?.response?.data?.detail || '授权失败，请重试'
    } finally {
      loading.value = false
    }
  }
}

onMounted(async () => {
  await loadWechatConfig()
  // 先检查已有授权
  const hasAuth = await checkExistingAuth()
  if (!hasAuth) {
    // 检查 URL 中是否有 code（微信回调）
    await handleCallback()
  }
})
</script>

<style scoped>
.wechat-auth-gate {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #07C160 0%, #04a849 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.auth-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px 32px;
  margin: 16px;
  max-width: 380px;
  width: 100%;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.auth-icon {
  margin-bottom: 16px;
}

h2 {
  font-size: 22px;
  font-weight: 600;
  color: #333;
  margin: 0 0 12px;
}

p {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 24px;
}

.error-tip {
  color: #ff4d4f !important;
  font-size: 13px !important;
  margin-top: -12px !important;
  margin-bottom: 12px !important;
}

.tip {
  color: #999 !important;
  font-size: 12px !important;
  margin-top: 16px !important;
}

.auth-success {
  width: 100%;
  height: 100%;
}
</style>
