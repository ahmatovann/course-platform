import { defineStore } from 'pinia'
import client from '../api/client'

export const useNewsStore = defineStore('news', {
  state: () => ({
    items: [],
    favorites: [],
  }),
  actions: {
    async fetchNews(params = {}) {
      const { data } = await client.get('/news/', { params })
      this.items = data
      return data
    },
    // Новость «в избранное» — тем же принципом, что и файлы/видео уроков.
    async toggleFavorite(item) {
      const { data } = item.is_favorite
        ? await client.delete(`/news/${item.id}/favorite/`)
        : await client.post(`/news/${item.id}/favorite/`)
      const idx = this.items.findIndex((n) => n.id === item.id)
      if (idx !== -1) this.items[idx] = data
      return data
    },
    async fetchFavorites() {
      const { data } = await client.get('/news/favorites/')
      this.favorites = data
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
