import { defineStore } from 'pinia'
import client from '../api/client'

export const useChatsStore = defineStore('chats', {
  state: () => ({
    threads: [],
    messages: [],
  }),
  actions: {
    async fetchThreads() {
      const { data } = await client.get('/chats/')
      this.threads = data
      return data
    },
    async fetchMessages(threadId) {
      const { data } = await client.get(`/chats/${threadId}/messages/`)
      this.messages = data
      return data
    },
    async sendMessage(threadId, text) {
      const { data } = await client.post(`/chats/${threadId}/messages/`, { text })
      this.messages.push(data)
      return data
    },
    async sendVoiceMessage(threadId, audioBlob) {
      const form = new FormData()
      const extension = audioBlob.type.includes('mp4') ? 'm4a' : audioBlob.type.includes('ogg') ? 'ogg' : 'webm'
      form.append('audio_file', audioBlob, `voice-message.${extension}`)
      const { data } = await client.post(`/chats/${threadId}/messages/`, form)
      this.messages.push(data)
      return data
    },
    async sendFileMessage(threadId, file) {
      const form = new FormData()
      form.append('file', file, file.name)
      const { data } = await client.post(`/chats/${threadId}/messages/`, form)
      this.messages.push(data)
      return data
    },
    async deleteMessage(messageId, scope) {
      await client.delete(`/chats/messages/${messageId}/?for=${scope}`)
      if (scope === 'me') {
        this.messages = this.messages.filter((m) => m.id !== messageId)
      } else {
        const idx = this.messages.findIndex((m) => m.id === messageId)
        if (idx !== -1) {
          this.messages[idx] = { ...this.messages[idx], deleted_for_everyone: true, text: '', audio_file: null, file: null, file_name: '' }
        }
      }
    },
    async toggleFavorite(message) {
      const { data } = message.is_favorite
        ? await client.delete(`/chats/messages/${message.id}/favorite/`)
        : await client.post(`/chats/messages/${message.id}/favorite/`)
      const idx = this.messages.findIndex((m) => m.id === message.id)
      if (idx !== -1) this.messages[idx] = data
      return data
    },
  },
})
