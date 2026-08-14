import { defineStore } from 'pinia'

let idCounter = 0
const THEME_KEY = 'course_theme'

export const useUiStore = defineStore('ui', {
  state: () => ({
    toasts: [],
    sidebarOpen: false,
    theme: localStorage.getItem(THEME_KEY) || 'light',
  }),
  actions: {
    showToast(message, type = 'success') {
      const id = ++idCounter
      this.toasts.push({ id, message, type })
      setTimeout(() => {
        this.toasts = this.toasts.filter((t) => t.id !== id)
      }, 3500)
    },
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen
    },
    // Переключение цветовой темы: тёмная (по умолчанию) или светлый фон.
    // Выбор сохраняется в localStorage, поэтому применяется при каждом визите.
    setTheme(theme) {
      this.theme = theme
      localStorage.setItem(THEME_KEY, theme)
      document.documentElement.setAttribute('data-theme', theme)
    },
    toggleTheme() {
      this.setTheme(this.theme === 'dark' ? 'light' : 'dark')
    },
  },
})
