import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

import client from '../api/client'
import { useNewsStore } from './news'

describe('news store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchNews forwards search/course filters as query params', async () => {
    client.get.mockResolvedValueOnce({ data: [{ id: 1, title: 'Новость', link_url: 'https://example.com' }] })
    const store = useNewsStore()
    await store.fetchNews({ search: 'визаж', course: 'none' })
    expect(client.get).toHaveBeenCalledWith('/news/', { params: { search: 'визаж', course: 'none' } })
    expect(store.items).toHaveLength(1)
    expect(store.items[0].link_url).toBe('https://example.com')
  })

  it('createNews posts the payload (including link_url) then refetches the list', async () => {
    client.post.mockResolvedValueOnce({ data: { id: 2, title: 'Новая', link_url: 'https://x.io' } })
    client.get.mockResolvedValueOnce({ data: [] })
    const store = useNewsStore()
    await store.createNews({ title: 'Новая', link_url: 'https://x.io', starts_at: '2026-09-01T00:00:00Z' })
    expect(client.post).toHaveBeenCalledWith('/news/create/', expect.objectContaining({ link_url: 'https://x.io' }))
    expect(client.get).toHaveBeenCalledWith('/news/', { params: {} })
  })
})
