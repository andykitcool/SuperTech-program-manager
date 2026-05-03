<template>
  <div>
    <div class="page-header">
      <h2>修改密码</h2>
    </div>

    <a-card class="password-card">
      <a-form
        ref="formRef"
        :model="form"
        layout="vertical"
        @finish="handleSubmit"
      >
        <a-form-item
          label="当前密码"
          name="oldPassword"
          :rules="[{ required: true, message: '请输入当前密码' }]"
        >
          <a-input-password
            v-model:value="form.oldPassword"
            placeholder="请输入当前密码"
            autocomplete="current-password"
          />
        </a-form-item>

        <a-form-item
          label="新密码"
          name="newPassword"
          :rules="[
            { required: true, message: '请输入新密码' },
            { min: 6, message: '新密码至少 6 位' },
          ]"
        >
          <a-input-password
            v-model:value="form.newPassword"
            placeholder="请输入新密码"
            autocomplete="new-password"
          />
        </a-form-item>

        <a-form-item
          label="确认新密码"
          name="confirmPassword"
          :rules="[
            { required: true, message: '请再次输入新密码' },
            { validator: validateConfirmPassword },
          ]"
        >
          <a-input-password
            v-model:value="form.confirmPassword"
            placeholder="请再次输入新密码"
            autocomplete="new-password"
          />
        </a-form-item>

        <a-space>
          <a-button type="primary" html-type="submit" :loading="saving">保存新密码</a-button>
          <a-button @click="resetForm">重置</a-button>
        </a-space>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { message, type FormInstance } from 'ant-design-vue'
import { adminApi } from '@/api/admin'

const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const validateConfirmPassword = async (_rule: unknown, value: string) => {
  if (value && value !== form.newPassword) {
    return Promise.reject('两次输入的新密码不一致')
  }
  return Promise.resolve()
}

const resetForm = () => {
  formRef.value?.resetFields()
}

const handleSubmit = async () => {
  saving.value = true
  try {
    await adminApi.changePassword(form.oldPassword, form.newPassword)
    message.success('密码修改成功')
    resetForm()
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.password-card {
  max-width: 520px;
}
</style>
