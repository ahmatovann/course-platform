import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import client from '../api/client'
import { useNotificationsStore } from './notifications'

describe('notifications store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('computes unreadCount from fetched items', async () => {
    client.get.mockResolvedValueOnce({
      data: [
        { id: 1, text: 'a', is_read: false, created_at: '2026-08-09T10:00:00Z' },
        { id: 2, text: 'b', is_read: true, created_at: '2026-08-09T09:00:00Z' },
      ],
    })
    const store = useNotificationsStore()
    await store.fetch()
    expect(store.unreadCount).toBe(1)
  })

  it('markRead flips a single notification locally after the API call', async () => {
    client.get.mockResolvedValueOnce({
      data: [{ id: 1, text: 'a', is_read: false, created_at: '2026-08-09T10:00:00Z' }],
    })
    client.post.mockResolvedValueOnce({ data: { detail: 'ok' } })

    const store = useNotificationsStore()
    await store.fetch()
    expect(store.unreadCount).toBe(1)

    await store.markRead(1)
    expect(client.post).toHaveBeenCalledWith('/notifications/1/read/')
    expect(store.unreadCount).toBe(0)
  })

  it('markAllRead flips every notification locally after the API call', async () => {
    client.get.mockResolvedValueOnce({
      data: [
        { id: 1, text: 'a', is_read: false, created_at: '2026-08-09T10:00:00Z' },
        { id: 2, text: 'b', is_read: false, created_at: '2026-08-09T09:00:00Z' },
      ],
    })
    client.post.mockResolvedValueOnce({ data: { detail: 'ok' } })

    const store = useNotificationsStore()
    await store.fetch()
    expect(store.unreadCount).toBe(2)

    await store.markAllRead()
    expect(client.post).toHaveBeenCalledWith('/notifications/read-all/')
    expect(store.unreadCount).toBe(0)
    expect(store.items.every((n) => n.is_read)).toBe(true)
  })

  it('ignores a stale in-flight fetch response that resolves after markAllRead', async () => {
    // Симулируем гонку: старый fetch() ещё "летит", пока пользователь уже
    // нажал «Прочитать всё» — устаревший ответ не должен затереть новое состояние.
    let resolveStaleFetch
    client.get.mockReturnValueOnce(new Promise((resolve) => { resolveStaleFetch = resolve }))
    client.post.mockResolvedValueOnce({ data: { detail: 'ok' } })

    const store = useNotificationsStore()
    store.items = [{ id: 1, text: 'a', is_read: false, created_at: '2026-08-09T10:00:00Z' }]

    const staleFetch = store.fetch()
    await store.markAllRead()
    expect(store.unreadCount).toBe(0)

    resolveStaleFetch({ data: [{ id: 1, text: 'a', is_read: false, created_at: '2026-08-09T10:00:00Z' }] })
    await staleFetch

    // Устаревший ответ (ещё непрочитанный) не должен был применяться.
    expect(store.unreadCount).toBe(0)
  })
})
