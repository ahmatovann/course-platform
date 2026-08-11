import { defineStore } from 'pinia'
import client from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    accessToken: localStorage.getItem('access_token') || null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.accessToken,
    isAdmin: (state) => state.user?.role === 'admin',
    initials: (state) => {
      const name = `${state.user?.first_name || ''} ${state.user?.last_name || ''}`.trim()
      return name.split(' ').filter(Boolean).map((w) => w[0]).join('').toUpperCase() || '??'
    },
  },
  actions: {
    persist(data) {
      this.accessToken = data.access
      this.user = data.user
      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
      localStorage.setItem('user', JSON.stringify(data.user))
    },
    async login(email, password) {
      const { data } = await client.post('/auth/login/', { email, password })
      this.persist(data)
      return data
    },
    async fetchProfile() {
      const { data } = await client.get('/profile/')
      this.user = data
      localStorage.setItem('user', JSON.stringify(data))
      return data
    },
    async updateProfile(payload) {
      const { data } = await client.patch('/profile/', payload)
      this.user = data
      localStorage.setItem('user', JSON.stringify(data))
      return data
    },
    async changePassword(newPassword, confirmPassword) {
      await client.post('/profile/change-password/', {
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
    },
    async requestPasswordReset(email) {
      const { data } = await client.post('/auth/password-reset/', { email })
      return data
    },
    async confirmPasswordReset({ uid, token, newPassword, confirmPassword }) {
      const { data } = await client.post('/auth/password-reset/confirm/', {
        uid, token, new_password: newPassword, confirm_password: confirmPassword,
      })
      return data
    },
    logout() {
      this.user = null
      this.accessToken = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    },
  },
})
