import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useUiStore } from './ui'

describe('ui store — theme setting', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    setActivePinia(createPinia())
  })

  it('setTheme persists the choice and updates <html data-theme>', () => {
    const ui = useUiStore()
    ui.setTheme('light')
    expect(ui.theme).toBe('light')
    expect(localStorage.getItem('course_theme')).toBe('light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('toggleTheme switches between dark and light', () => {
    const ui = useUiStore()
    ui.setTheme('dark')
    ui.toggleTheme()
    expect(ui.theme).toBe('light')
    ui.toggleTheme()
    expect(ui.theme).toBe('dark')
  })

  it('showToast adds and then auto-removes a toast', async () => {
    const ui = useUiStore()
    ui.showToast('Готово', 'success')
    expect(ui.toasts).toHaveLength(1)
    expect(ui.toasts[0]).toMatchObject({ message: 'Готово', type: 'success' })
  })
})
