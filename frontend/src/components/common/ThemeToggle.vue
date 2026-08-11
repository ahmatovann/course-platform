<script setup>
// Кнопка переключения темы: тёмная (тёмно-синяя) ↔ светлая.
// Используется на экранах входа/регистрации, а также как часть
// блока «Настройки» в профиле — выбор сохраняется и применяется
// во всём приложении, включая кабинеты ученика и администратора.
// Только иконка, без подписи.
import { useUiStore } from '../../store/ui'

const ui = useUiStore()
</script>

<template>
  <button
    class="theme-toggle"
    type="button"
    @click="ui.toggleTheme()"
    :title="ui.theme === 'dark' ? 'Включить светлый фон' : 'Включить тёмный фон'"
    :aria-label="ui.theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'"
  >
    <span class="theme-toggle-icon" aria-hidden="true">{{ ui.theme === 'dark' ? '☀' : '☾' }}</span>
  </button>
</template>
