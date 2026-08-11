import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/base.css'

// Применяем сохранённую тему (тёмная/светлая) до первой отрисовки —
// чтобы страница не «моргала» цветом при загрузке.
document.documentElement.setAttribute('data-theme', localStorage.getItem('course_theme') || 'dark')

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
