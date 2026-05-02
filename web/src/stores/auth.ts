import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/api/request'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')

  const isLoggedIn = () => !!token.value

  const login = async (user: string, password: string) => {
    const res = await request.post('/admin/login', { username: user, password: password })
    token.value = res.data.access_token
    username.value = res.data.username
    localStorage.setItem('token', res.data.access_token)
    localStorage.setItem('username', res.data.username)
    return res.data
  }

  const logout = () => {
    token.value = ''
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
  }

  return { token, username, isLoggedIn, login, logout }
})
