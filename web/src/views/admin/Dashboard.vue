<template>
  <a-layout class="admin-layout">
    <a-layout-sider
      v-model:collapsed="collapsed"
      collapsible
      theme="dark"
      :width="220"
      class="admin-sider"
    >
      <div class="admin-sider-logo">
        <h2 v-if="!collapsed">SuperTech PM</h2>
        <h2 v-else>ST</h2>
      </div>

      <div class="sider-menu-shell">
        <a-menu
          class="sider-menu-main"
          theme="dark"
          mode="inline"
          :selected-keys="selectedKeys"
          @click="handleMenuClick"
        >
          <a-menu-item v-if="auth.hasPermission('activity.manage')" key="/admin">
            <template #icon><AppstoreOutlined /></template>
            <span>活动管理</span>
          </a-menu-item>
          <a-menu-item v-if="auth.hasPermission('sync.manage')" key="/admin/wotu-sync">
            <template #icon><CloudSyncOutlined /></template>
            <span>同步记录</span>
          </a-menu-item>
          <a-menu-item v-if="auth.hasPermission('photo.manage') && !isPrintAdmin" key="/admin/photo-manager">
            <template #icon><PictureOutlined /></template>
            <span>照片管理</span>
          </a-menu-item>
          <a-menu-item v-if="auth.hasPermission('music.manage')" key="/admin/music-library">
            <template #icon><CustomerServiceOutlined /></template>
            <span>热门曲库</span>
          </a-menu-item>
          <a-menu-item v-if="auth.hasPermission('material.manage')" key="/admin/decoration-manager">
            <template #icon><BgColorsOutlined /></template>
            <span>素材管理</span>
          </a-menu-item>
          <a-menu-item v-if="auth.hasPermission('print.manage')" key="/admin/print-settings">
            <template #icon><PrinterOutlined /></template>
            <span>云印设置</span>
          </a-menu-item>
          <a-menu-item v-if="auth.hasPermission('print.manage')" key="/admin/print-orders">
            <template #icon><OrderedListOutlined /></template>
            <span>打印订单</span>
          </a-menu-item>
          <a-menu-item v-if="auth.hasPermission('user.manage')" key="/admin/users">
            <template #icon><TeamOutlined /></template>
            <span>用户管理</span>
          </a-menu-item>
        </a-menu>

        <a-menu
          class="sider-menu-bottom"
          theme="dark"
          mode="inline"
          :selected-keys="selectedKeys"
          @click="handleMenuClick"
        >
          <a-menu-item v-if="auth.hasPermission('system.manage') || auth.hasPermission('role.manage')" key="/admin/settings">
            <template #icon><SettingOutlined /></template>
            <span>系统设置</span>
          </a-menu-item>
        </a-menu>
      </div>
    </a-layout-sider>

    <a-layout>
      <a-layout-header class="admin-header">
        <div class="header-left">
          <MenuFoldOutlined v-if="!collapsed" class="trigger" @click="collapsed = true" />
          <MenuUnfoldOutlined v-else class="trigger" @click="collapsed = false" />
          <span class="page-title">素材管理系统</span>
          <a-button
            v-if="showDeliveryButton"
            size="small"
            class="delivery-button"
            @click="openDeliveryQr"
          >
            <template #icon><QrcodeOutlined /></template>
            素材交付
          </a-button>
        </div>

        <div class="header-right">
          <a-dropdown placement="bottomRight">
            <a class="user-info" @click.prevent>
              <UserOutlined />
              <span>{{ auth.username || 'admin' }}</span>
            </a>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="router.push('/admin/change-password')">
                  <LockOutlined />
                  <span>修改密码</span>
                </a-menu-item>
                <a-menu-item @click="handleLogout">
                  <LogoutOutlined />
                  <span>退出登录</span>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <a-layout-content class="admin-content">
        <router-view />
      </a-layout-content>
    </a-layout>

    <a-modal
      v-model:open="showDeliveryModal"
      title="素材交付二维码"
      :footer="null"
      width="420px"
    >
      <a-spin :spinning="deliveryLoading">
        <div class="delivery-qr-panel">
          <a-qrcode v-if="deliveryUrl" :value="deliveryUrl" :size="220" />
          <a-empty v-else description="暂未生成交付链接" />
          <div class="delivery-url">{{ deliveryUrl || '请先在系统设置中配置域名' }}</div>
          <a-space>
            <a-button :disabled="!deliveryUrl" @click="copyDeliveryUrl">
              <template #icon><CopyOutlined /></template>
              复制链接
            </a-button>
            <a-button type="primary" :disabled="!deliveryUrl" @click="openDeliveryUrl">
              <template #icon><LinkOutlined /></template>
              打开页面
            </a-button>
          </a-space>
        </div>
      </a-spin>
    </a-modal>
  </a-layout>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AppstoreOutlined,
  CloudSyncOutlined,
  CustomerServiceOutlined,
  LockOutlined,
  LogoutOutlined,
  LinkOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  OrderedListOutlined,
  PictureOutlined,
  QrcodeOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
  BgColorsOutlined,
  CopyOutlined,
  PrinterOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const collapsed = ref(false)
const isPrintAdmin = computed(() => auth.isPrintAdmin())
const showDeliveryModal = ref(false)
const deliveryLoading = ref(false)
const deliveryUrl = ref('')
const showDeliveryButton = computed(() => route.name === 'ProgramList' && Boolean(route.params.id))

const selectedKeys = computed(() => {
  if (route.path === '/admin/change-password') return []
  return [route.path]
})

const handleMenuClick = ({ key }: { key: string }) => {
  router.push(key)
}

const handleLogout = () => {
  auth.logout()
  router.push('/admin/login')
}

const fallbackBaseUrl = () => window.location.origin.replace(/\/+$/, '')

const normalizeBaseUrl = (value?: string | null) => {
  const text = String(value || '').trim().replace(/\/+$/, '')
  return text || fallbackBaseUrl()
}

const resolvePublicBaseUrl = async () => {
  try {
    const res = await request.get('/settings/network')
    return normalizeBaseUrl(res.data?.base_url)
  } catch {
    return fallbackBaseUrl()
  }
}

const openDeliveryQr = async () => {
  showDeliveryModal.value = true
  deliveryLoading.value = true
  try {
    const baseUrl = await resolvePublicBaseUrl()
    deliveryUrl.value = `${baseUrl}/p/${route.params.id}`
  } catch {
    message.error('生成交付二维码失败')
  } finally {
    deliveryLoading.value = false
  }
}

const copyDeliveryUrl = async () => {
  if (!deliveryUrl.value) return
  try {
    await navigator.clipboard.writeText(deliveryUrl.value)
    message.success('交付链接已复制')
  } catch {
    message.warning('复制失败，请手动复制链接')
  }
}

const openDeliveryUrl = () => {
  if (!deliveryUrl.value) return
  window.open(deliveryUrl.value, '_blank', 'noopener')
}

watch(() => route.path, (path) => {
  if (path.startsWith('/admin') && path !== '/admin/login' && !auth.isLoggedIn()) {
    router.push('/admin/login')
  }
})
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
}

.admin-sider :deep(.ant-layout-sider-children) {
  display: flex;
  flex-direction: column;
}

.admin-sider-logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.admin-sider-logo h2 {
  margin: 0;
  color: #fff;
  font-size: 18px;
  font-weight: 700;
}

.sider-menu-shell {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.sider-menu-main {
  flex: 1;
}

.sider-menu-bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.admin-header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
}

.trigger {
  font-size: 18px;
  cursor: pointer;
  transition: color 0.3s;
  color: rgba(0, 0, 0, 0.65);
}

.trigger:hover {
  color: #1890ff;
}

.page-title {
  font-size: 16px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
}

.delivery-button {
  margin-left: 2px;
}

.user-info {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: rgba(0, 0, 0, 0.65);
  cursor: pointer;
  transition: color 0.3s;
}

.user-info:hover {
  color: #1890ff;
}

.admin-content {
  margin: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  min-height: 280px;
}

.delivery-qr-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 8px 0 4px;
}

.delivery-url {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f6f8fb;
  color: #4b5565;
  font-size: 13px;
  line-height: 1.5;
  text-align: center;
  word-break: break-all;
}
</style>
