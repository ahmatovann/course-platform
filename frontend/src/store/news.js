import { defineStore } from 'pinia'
import client from '../api/client'

export const useNewsStore = defineStore('news', {
  state: () => ({
    items: [],
  }),
  actions: {
    async fetchNews(params = {}) {
      const { data } = await client.get('/news/', { params })
      this.items = data
      return data
    },
    async createNews(payload) {
      const { data } = await client.post('/news/create/', payload)
      await this.fetchNews()
      return data
    },
    async updateNews(id, payload) {
      const { data } = await client.patch(`/news/${id}/`, payload)
      await this.fetchNews()
      return data
    },
    async deleteNews(id) {
      await client.delete(`/news/${id}/`)
      await this.fetchNews()
    },
  },
})
