<template>
  <div class="role-management">
    <div class="role-toolbar">
      <div>
        <h3>角色管理</h3>
        <p>配置后台角色与权限范围，系统默认角色会在服务启动时自动生成。</p>
      </div>
      <a-button type="primary" @click="openCreate">
        <template #icon><PlusOutlined /></template>
        创建角色
      </a-button>
    </div>

    <a-table
      row-key="id"
      :loading="loading"
      :data-source="roles"
      :pagination="false"
      bordered
    >
      <a-table-column title="角色名称" data-index="name" :width="180" />
      <a-table-column title="角色编码" data-index="code" :width="180" />
      <a-table-column title="权限">
        <template #default="{ record }">
          <a-space wrap>
            <a-tag v-for="permission in record.permissions" :key="permission" color="blue">
              {{ permissionLabel(permission) }}
            </a-tag>
          </a-space>
        </template>
      </a-table-column>
      <a-table-column title="说明" data-index="description" />
      <a-table-column title="类型" :width="110">
        <template #default="{ record }">
          <a-tag :color="record.is_system ? 'green' : 'default'">
            {{ record.is_system ? '系统默认' : '自定义' }}
          </a-tag>
        </template>
      </a-table-column>
      <a-table-column title="操作" :width="150">
        <template #default="{ record }">
          <a-space>
            <a-button type="link" size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除这个角色？" @confirm="deleteRole(record)">
              <a-button type="link" size="small" danger :disabled="record.is_system">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </a-table-column>
    </a-table>

    <a-modal
      v-model:open="modalOpen"
      :title="editingRole ? '编辑角色' : '创建角色'"
      ok-text="保存"
      cancel-text="取消"
      :confirm-loading="saving"
      @ok="saveRole"
    >
      <a-form layout="vertical">
        <a-form-item label="角色名称" required>
          <a-input v-model:value="form.name" :disabled="editingRole?.is_system" placeholder="例如：运营管理员" />
        </a-form-item>
        <a-form-item label="角色编码" required>
          <a-input v-model:value="form.code" :disabled="editingRole?.is_system" placeholder="例如：operator_admin" />
        </a-form-item>
        <a-form-item label="说明">
          <a-textarea v-model:value="form.description" :rows="2" placeholder="描述这个角色适合谁使用" />
        </a-form-item>
        <a-form-item label="权限" required>
          <a-checkbox-group v-model:value="form.permissions" class="permission-grid">
            <a-checkbox v-for="item in permissions" :key="item.key" :value="item.key">
              {{ item.label }}
            </a-checkbox>
          </a-checkbox-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { adminApi, type AdminPermission, type AdminRole } from '@/api/admin'

const loading = ref(false)
const saving = ref(false)
const modalOpen = ref(false)
const roles = ref<AdminRole[]>([])
const permissions = ref<AdminPermission[]>([])
const editingRole = ref<AdminRole | null>(null)

const form = reactive({
  name: '',
  code: '',
  description: '',
  permissions: [] as string[],
})

function permissionLabel(key: string) {
  return permissions.value.find(item => item.key === key)?.label || key
}

function resetForm(role?: AdminRole) {
  editingRole.value = role || null
  form.name = role?.name || ''
  form.code = role?.code || ''
  form.description = role?.description || ''
  form.permissions = [...(role?.permissions || [])]
}

function openCreate() {
  resetForm()
  modalOpen.value = true
}

function openEdit(role: AdminRole) {
  resetForm(role)
  modalOpen.value = true
}

async function loadData() {
  loading.value = true
  try {
    const [roleRes, permissionRes] = await Promise.all([
      adminApi.listRoles(),
      adminApi.listPermissions(),
    ])
    roles.value = roleRes.data
    permissions.value = permissionRes.data
  } finally {
    loading.value = false
  }
}

async function saveRole() {
  if (!form.name.trim() || !form.code.trim()) {
    message.warning('请填写角色名称和编码')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      code: form.code.trim(),
      description: form.description.trim(),
      permissions: form.permissions,
    }
    if (editingRole.value) {
      await adminApi.updateRole(editingRole.value.id, payload)
    } else {
      await adminApi.createRole(payload)
    }
    message.success('角色已保存')
    modalOpen.value = false
    await loadData()
  } finally {
    saving.value = false
  }
}

async function deleteRole(role: AdminRole) {
  await adminApi.deleteRole(role.id)
  message.success('角色已删除')
  await loadData()
}

onMounted(loadData)
</script>

<style scoped>
.role-management {
  min-width: 0;
}

.role-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.role-toolbar h3 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 17px;
}

.role-toolbar p {
  margin: 0;
  color: #6b7280;
}

.permission-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
}
</style>
