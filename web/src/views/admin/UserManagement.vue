<template>
  <div class="user-management">
    <div class="page-header">
      <div>
        <h2>用户管理</h2>
        <p>管理自注册后台账号和微信用户的角色、活动授权与禁用状态。</p>
      </div>
      <a-input-search
        v-model:value="keyword"
        class="search-box"
        :placeholder="searchPlaceholder"
        allow-clear
        enter-button
        @search="loadUsers(1)"
      />
    </div>

    <a-tabs v-model:active-key="activeSource" class="user-tabs" @change="handleTabChange">
      <a-tab-pane key="self" tab="自注册用户" />
      <a-tab-pane key="wechat" tab="微信用户" />
    </a-tabs>

    <a-table
      row-key="id"
      :loading="loading"
      :data-source="users"
      :pagination="pagination"
      @change="handleTableChange"
      bordered
    >
      <a-table-column v-if="activeSource === 'self'" title="账号" :width="280">
        <template #default="{ record }">
          <div class="user-cell">
            <a-avatar :size="42">{{ avatarText(record) }}</a-avatar>
            <div class="user-meta">
              <strong>{{ record.nickname || record.username || '自注册用户' }}</strong>
              <span>{{ record.username }}</span>
            </div>
          </div>
        </template>
      </a-table-column>

      <a-table-column v-if="activeSource === 'wechat'" title="微信用户" :width="300">
        <template #default="{ record }">
          <div class="user-cell">
            <a-avatar :src="record.avatar_url || undefined" :size="42">
              {{ avatarText(record) }}
            </a-avatar>
            <div class="user-meta">
              <strong>{{ record.nickname || '微信用户' }}</strong>
              <span>{{ record.openid }}</span>
            </div>
          </div>
        </template>
      </a-table-column>

      <a-table-column title="来源" :width="110">
        <template #default="{ record }">
          <a-tag :color="record.source === 'self' ? 'purple' : 'green'">
            {{ record.source === 'self' ? '自注册' : '微信' }}
          </a-tag>
        </template>
      </a-table-column>

      <a-table-column title="角色" :width="230">
        <template #default="{ record }">
          <a-space wrap>
            <a-tag v-for="item in roleTags(record)" :key="item" color="blue">{{ item }}</a-tag>
            <span v-if="roleTags(record).length === 0" class="muted">未设置</span>
          </a-space>
        </template>
      </a-table-column>

      <a-table-column title="活动权限">
        <template #default="{ record }">
          <a-space wrap>
            <a-tag v-for="item in activityTags(record)" :key="item" color="green">{{ item }}</a-tag>
            <span v-if="activityTags(record).length === 0" class="muted">无指定活动</span>
          </a-space>
        </template>
      </a-table-column>

      <a-table-column title="状态" :width="120">
        <template #default="{ record }">
          <a-switch
            :checked="record.is_blacklisted"
            checked-children="禁用"
            un-checked-children="正常"
            @change="(checked: boolean) => toggleBlacklist(record, checked)"
          />
        </template>
      </a-table-column>

      <a-table-column :title="activeSource === 'self' ? '注册时间' : '最近访问'" :width="170">
        <template #default="{ record }">
          {{ formatTime(activeSource === 'self' ? record.created_at : record.last_seen_at) }}
        </template>
      </a-table-column>

      <a-table-column title="操作" :width="170">
        <template #default="{ record }">
          <a-space>
            <a-button type="link" size="small" @click="openRoleModal(record)">设置角色</a-button>
            <a-popconfirm title="确定删除这个用户？" @confirm="deleteUser(record)">
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </a-table-column>
    </a-table>

    <a-modal
      v-model:open="roleModalOpen"
      title="设置用户角色"
      ok-text="保存"
      cancel-text="取消"
      :confirm-loading="savingRoles"
      @ok="saveUserRoles"
    >
      <a-form layout="vertical">
        <a-form-item label="角色">
          <a-checkbox-group v-model:value="roleForm.roleIds" class="role-grid">
            <a-checkbox v-for="role in roles" :key="role.id" :value="role.id">
              {{ role.name }}
            </a-checkbox>
          </a-checkbox-group>
        </a-form-item>
        <a-form-item v-if="needsActivityScope" label="授权活动">
          <a-select
            v-model:value="roleForm.activityIds"
            mode="multiple"
            placeholder="选择活动管理员可管理的活动"
            :options="activityOptions"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { adminApi, type Activity, type AdminRole, type AdminUser } from '@/api/admin'

type UserSource = 'self' | 'wechat'

const loading = ref(false)
const savingRoles = ref(false)
const keyword = ref('')
const activeSource = ref<UserSource>('self')
const users = ref<AdminUser[]>([])
const roles = ref<AdminRole[]>([])
const activities = ref<Activity[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const selectedUser = ref<AdminUser | null>(null)
const roleModalOpen = ref(false)

const roleForm = reactive({
  roleIds: [] as number[],
  activityIds: [] as number[],
})

const pagination = computed(() => ({
  current: currentPage.value,
  pageSize: pageSize.value,
  total: total.value,
  showSizeChanger: true,
}))

const searchPlaceholder = computed(() => (
  activeSource.value === 'self'
    ? '搜索显示名称 / 用户名 / 手机号'
    : '搜索昵称 / openid / 手机号'
))

const activityOptions = computed(() => activities.value.map(item => ({ label: item.name, value: item.id })))

const needsActivityScope = computed(() => roleForm.roleIds.some(roleId => {
  const role = roles.value.find(item => item.id === roleId)
  return requiresActivityScope(role)
}))

function requiresActivityScope(role?: AdminRole) {
  return !!role && role.code !== 'print_admin' && role.permissions.includes('activity.manage')
}

function avatarText(user: AdminUser) {
  return (user.nickname || user.username || user.openid || '用').slice(0, 1)
}

function roleTags(user: AdminUser) {
  return [...new Set(user.assignments.map(item => item.role_name))]
}

function activityTags(user: AdminUser) {
  return [...new Set(user.assignments.map(item => item.activity_name).filter(Boolean))] as string[]
}

function formatTime(value?: string | null) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-'
}

async function loadUsers(page = currentPage.value) {
  loading.value = true
  try {
    currentPage.value = page
    const res = await adminApi.listUsers(keyword.value || undefined, currentPage.value, pageSize.value, activeSource.value)
    users.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  const [roleRes, activityRes] = await Promise.all([
    adminApi.listRoles(),
    adminApi.listActivities(),
  ])
  roles.value = roleRes.data
  activities.value = activityRes.data
}

function handleTabChange(key: string | number) {
  activeSource.value = key as UserSource
  keyword.value = ''
  void loadUsers(1)
}

function handleTableChange(pager: any) {
  pageSize.value = pager.pageSize
  void loadUsers(pager.current)
}

async function toggleBlacklist(user: AdminUser, checked: boolean) {
  const oldValue = user.is_blacklisted
  user.is_blacklisted = checked
  try {
    await adminApi.updateUserBlacklist(user.id, checked)
    message.success(checked ? '用户已禁用' : '用户已恢复')
  } catch {
    user.is_blacklisted = oldValue
  }
}

function openRoleModal(user: AdminUser) {
  selectedUser.value = user
  roleForm.roleIds = [...new Set(user.assignments.map(item => item.role_id))]
  roleForm.activityIds = [...new Set(user.assignments.map(item => item.activity_id).filter(Boolean))] as number[]
  roleModalOpen.value = true
}

async function saveUserRoles() {
  if (!selectedUser.value) return
  if (needsActivityScope.value && roleForm.activityIds.length === 0) {
    message.warning('请至少选择一个授权活动')
    return
  }
  savingRoles.value = true
  try {
    const assignments = roleForm.roleIds.map(roleId => {
      const role = roles.value.find(item => item.id === roleId)
      return {
        role_id: roleId,
        activity_ids: requiresActivityScope(role) ? roleForm.activityIds : [],
      }
    })
    await adminApi.updateUserRoles(selectedUser.value.id, assignments)
    message.success('用户角色已更新')
    roleModalOpen.value = false
    await loadUsers()
  } finally {
    savingRoles.value = false
  }
}

async function deleteUser(user: AdminUser) {
  await adminApi.deleteUser(user.id)
  message.success('用户已删除')
  await loadUsers()
}

onMounted(async () => {
  await Promise.all([loadMeta(), loadUsers(1)])
})
</script>

<style scoped>
.user-management {
  min-width: 0;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
}

.page-header h2 {
  margin: 0 0 4px;
  font-size: 20px;
}

.page-header p {
  margin: 0;
  color: #6b7280;
}

.search-box {
  width: 320px;
}

.user-tabs {
  margin-bottom: 14px;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.user-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.user-meta strong {
  color: #111827;
}

.user-meta span {
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #8c96a8;
  font-size: 12px;
}

.muted {
  color: #9ca3af;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
}
</style>
