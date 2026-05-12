<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <h1>SuperTech</h1>
          <p>少儿舞蹈展演素材管理系统</p>
        </div>

        <a-form :model="formState" layout="vertical" class="login-form" @finish="handleLogin">
          <a-form-item name="username" :rules="[{ required: true, message: '请输入用户名' }]">
            <a-input v-model:value="formState.username" size="large" placeholder="用户名" allow-clear>
              <template #prefix><UserOutlined /></template>
            </a-input>
          </a-form-item>
          <a-form-item name="password" :rules="[{ required: true, message: '请输入密码' }]">
            <a-input-password v-model:value="formState.password" size="large" placeholder="密码" @pressEnter="handleLogin">
              <template #prefix><LockOutlined /></template>
            </a-input-password>
          </a-form-item>
          <a-form-item>
            <a-button type="primary" html-type="submit" size="large" block :loading="loading" class="login-btn">
              登录
            </a-button>
          </a-form-item>
        </a-form>

        <div class="register-entry">
          <span>还没有后台账号？</span>
          <a-button type="link" size="small" @click="registerOpen = true">立即注册</a-button>
        </div>
      </div>
    </div>

    <a-modal
      v-model:open="registerOpen"
      title="注册后台账号"
      ok-text="提交注册"
      cancel-text="取消"
      :confirm-loading="registering"
      @ok="handleRegister"
    >
      <a-form ref="registerFormRef" :model="registerForm" layout="vertical">
        <a-form-item
          name="username"
          label="用户名"
          :rules="[
            { required: true, message: '请输入用户名' },
            { min: 3, max: 40, message: '用户名长度为 3-40 个字符' },
            { pattern: /^[A-Za-z0-9_][A-Za-z0-9_.-]*$/, message: '只能使用字母、数字、下划线、点和短横线' },
          ]"
        >
          <a-input v-model:value="registerForm.username" placeholder="例如 teacher_01" allow-clear />
        </a-form-item>
        <a-form-item name="nickname" label="显示名称">
          <a-input v-model:value="registerForm.nickname" placeholder="用于用户管理中识别账号" allow-clear />
        </a-form-item>
        <a-form-item
          name="password"
          label="密码"
          :rules="[
            { required: true, message: '请输入密码' },
            { min: 6, max: 72, message: '密码长度为 6-72 个字符' },
          ]"
        >
          <a-input-password v-model:value="registerForm.password" placeholder="至少 6 位" />
        </a-form-item>
        <a-form-item
          name="confirmPassword"
          label="确认密码"
          :rules="[
            { required: true, message: '请再次输入密码' },
            { validator: validateConfirmPassword },
          ]"
        >
          <a-input-password v-model:value="registerForm.confirmPassword" placeholder="再次输入密码" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormInstance } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const registering = ref(false)
const registerOpen = ref(false)
const registerFormRef = ref<FormInstance>()

const formState = reactive({
  username: '',
  password: '',
})

const registerForm = reactive({
  username: '',
  nickname: '',
  password: '',
  confirmPassword: '',
})

const validateConfirmPassword = async (_rule: unknown, value: string) => {
  if (value && value !== registerForm.password) {
    return Promise.reject(new Error('两次输入的密码不一致'))
  }
  return Promise.resolve()
}

const handleLogin = async () => {
  loading.value = true
  try {
    await auth.login(formState.username, formState.password)
    message.success('登录成功')
    router.push('/admin')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  await registerFormRef.value?.validate()
  registering.value = true
  try {
    await adminApi.register({
      username: registerForm.username.trim(),
      nickname: registerForm.nickname.trim() || registerForm.username.trim(),
      password: registerForm.password,
    })
    formState.username = registerForm.username.trim()
    formState.password = ''
    registerOpen.value = false
    Object.assign(registerForm, { username: '', nickname: '', password: '', confirmPassword: '' })
    message.success('注册成功，请等待管理员分配权限后登录')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '注册失败')
  } finally {
    registering.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #001529 0%, #003a8c 50%, #0050b3 100%);
}

.login-container {
  width: 100%;
  max-width: 400px;
  padding: 20px;
}

.login-card {
  background: #fff;
  border-radius: 12px;
  padding: 40px 32px 28px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 8px;
  background: linear-gradient(135deg, #1890ff, #096dd9);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.login-header p {
  color: #8c8c8c;
  font-size: 14px;
  margin: 0;
}

.login-btn {
  height: 44px;
  font-size: 16px;
  border-radius: 8px;
}

.register-entry {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: #6b7280;
  font-size: 13px;
}
</style>
