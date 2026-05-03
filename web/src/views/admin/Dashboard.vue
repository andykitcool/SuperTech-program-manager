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
          <a-menu-item key="/admin">
            <template #icon><AppstoreOutlined /></template>
            <span>活动管理</span>
          </a-menu-item>
          <a-menu-item key="/admin/wotu-sync">
            <template #icon><CloudSyncOutlined /></template>
            <span>同步记录</span>
          </a-menu-item>
          <a-menu-item key="/admin/photo-manager">
            <template #icon><PictureOutlined /></template>
            <span>照片管理</span>
          </a-menu-item>
        </a-menu>

        <a-menu
          class="sider-menu-bottom"
          theme="dark"
          mode="inline"
          :selected-keys="selectedKeys"
          @click="handleMenuClick"
        >
          <a-menu-item key="/admin/settings">
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
  </a-layout>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AppstoreOutlined,
  CloudSyncOutlined,
  LockOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PictureOutlined,
  SettingOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const collapsed = ref(false)

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
</style>
