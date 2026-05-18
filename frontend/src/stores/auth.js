import { defineStore } from 'pinia'
import { login as loginApi, register as registerApi, getMe } from '@/api'
import router from '@/router'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: null
  }),
  getters: {
    isLoggedIn: (state) => !!state.token
  },
  actions: {
    async login(credentials) {
      const res = await loginApi(credentials)
      const token = res?.data?.token || res?.token
      if (!token) throw new Error('登录失败：未获取到令牌')
      this.token = token
      localStorage.setItem('token', token)
      await this.fetchUser()
    },
    async register(data) {
      await registerApi(data)
    },
    async fetchUser() {
      try {
        const res = await getMe()
        this.user = res?.data || res
      } catch {
        // ignore fetch failure
      }
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      router.push('/login')
    }
  }
})
