import { defineStore } from 'pinia'
import client from '../api/client'

export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    items: [],
    _fetchSeq: 0,
  }),
  getters: {
    unreadCount: (state) => state.items.filter((n) => !n.is_read).length,
  },
  actions: {
    async fetch() {
      // Опрос идёт каждые 20 сек в фоне. Если пользователь успел нажать
      // «Прочитать всё» (или открыть уведомление) пока старый запрос ещё
      // летел, его устаревший ответ не должен затирать свежее состояние —
      // применяем только ответ самого последнего запроса.
      const seq = ++this._fetchSeq
      const { data } = await client.get('/notifications/')
      if (seq !== this._fetchSeq) return this.items
      this.items = data
      return data
    },
    async markRead(id) {
      await client.post(`/notifications/${id}/read/`)
      const item = this.items.find((n) => n.id === id)
      if (item) item.is_read = true
      this._fetchSeq++
    },
    async markAllRead() {
      await client.post('/notifications/read-all/')
      this.items.forEach((n) => { n.is_read = true })
      this._fetchSeq++
    },
  },
})
