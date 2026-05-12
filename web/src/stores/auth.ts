import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/api/request'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const permissions = ref<string[]>(JSON.parse(localStorage.getItem('permissions') || '[]'))
  const roleCodes = ref<string[]>(JSON.parse(localStorage.getItem('role_codes') || '[]'))

  const isLoggedIn = () => !!token.value
  const hasPermission = (permission: string) => username.value === 'admin' || roleCodes.value.includes('super_admin') || permissions.value.includes(permission)
  const isPrintAdmin = () => roleCodes.value.includes('print_admin') && !roleCodes.value.includes('super_admin') && username.value !== 'admin'

  const login = async (user: string, password: string) => {
    const res = await request.post('/admin/login', { username: user, password: password })
    token.value = res.data.access_token
    username.value = res.data.username
    permissions.value = res.data.permissions || []
    roleCodes.value = res.data.role_codes || []
    localStorage.setItem('token', res.data.access_token)
    localStorage.setItem('username', res.data.username)
    localStorage.setItem('permissions', JSON.stringify(permissions.value))
    localStorage.setItem('role_codes', JSON.stringify(roleCodes.value))
    return res.data
  }

  const logout = () => {
    token.value = ''
    username.value = ''
    permissions.value = []
    roleCodes.value = []
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('permissions')
    localStorage.removeItem('role_codes')
    localStorage.removeItem('activity_ids')
  }

  return { token, username, permissions, roleCodes, isLoggedIn, hasPermission, isPrintAdmin, login, logout }
})
