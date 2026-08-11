<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '../../store/notifications'
import { useAuthStore } from '../../store/auth'
import { useUiStore } from '../../store/ui'

const store = useNotificationsStore()
const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const open = ref(false)
const btnEl = ref(null)
const panelEl = ref(null)
const panelStyle = ref({})
let timer = null

// Уведомления генерируются на бэкенде с "ученическими" адресами (/chats,
// /news и т.д.). У администратора те же разделы живут под /admin/...,
// поэтому при переходе по уведомлению адрес нужно адаптировать под роль —
// иначе роутер видит несовпадение role и молча уводит админа на /admin/students.
function resolveUrl(url) {
  if (!url) return null
  if (!auth.isAdmin || url.startsWith('/admin')) return url
  if (url.startsWith('/chats')) return '/admin/chats'
  if (url.startsWith('/news')) return '/admin/news'
  // Разделы конкретного урока/теста ученика у админа не существуют —
  // ведём на список тренингов, откуда до них можно дойти.
  if (url.startsWith('/lessons') || url.startsWith('/tests') || url.startsWith('/courses')) return '/admin/courses'
  return '/admin/students'
}

// Панель уведомлений телепортируется в <body>, поэтому клик "снаружи"
// должен проверяться и по кнопке-колокольчику, и по самой панели —
// иначе после телепортации клик по кнопке из панели считался бы "внешним".
function handleOutsideClick(e) {
  if (!open.value) return
  const inBtn = btnEl.value && btnEl.value.contains(e.target)
  const inPanel = panelEl.value && panelEl.value.contains(e.target)
  if (!inBtn && !inPanel) open.value = false
}

async function reposition() {
  await nextTick()
  if (!btnEl.value) return
  const rect = btnEl.value.getBoundingClientRect()
  const width = 320
  let left = rect.left
  if (left + width > window.innerWidth - 12) left = window.innerWidth - width - 12
  if (left < 12) left = 12
  // Открываем панель вверх от колокольчика (он обычно внизу сайдбара),
  // но если места сверху не хватает — вниз.
  const spaceAbove = rect.top
  const openUpward = spaceAbove > 260
  panelStyle.value = openUpward
    ? { left: `${left}px`, bottom: `${window.innerHeight - rect.top + 10}px`, top: 'auto' }
    : { left: `${left}px`, top: `${rect.bottom + 10}px`, bottom: 'auto' }
}

onMounted(() => {
  store.fetch()
  // обновляем раз в 20 секунд, пока пользователь в кабинете
  timer = setInterval(() => store.fetch(), 20000)
  document.addEventListener('click', handleOutsideClick)
  window.addEventListener('resize', reposition)
  window.addEventListener('scroll', reposition, true)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
  document.removeEventListener('click', handleOutsideClick)
  window.removeEventListener('resize', reposition)
  window.removeEventListener('scroll', reposition, true)
})

async function toggle() {
  open.value = !open.value
  if (open.value) await reposition()
}

async function openItem(n) {
  open.value = false
  try {
    if (!n.is_read) await store.markRead(n.id)
  } catch (e) {
    ui.showToast('Не удалось отметить уведомление прочитанным', 'error')
  }
  const target = resolveUrl(n.url)
  if (target) router.push(target)
}

async function markAll() {
  try {
    await store.markAllRead()
    ui.showToast('Все уведомления отмечены прочитанными', 'success')
  } catch (e) {
    ui.showToast('Не удалось отметить уведомления прочитанными', 'error')
  }
}

function formatTime(iso) {
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="bell-wrap">
    <button class="bell-btn" type="button" ref="btnEl" @click.stop="toggle" title="Уведомления" aria-label="Уведомления">
      <svg class="bell-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M10 2.5c-2.5 0-4.2 1.9-4.2 4.5v2.6c0 .5-.2 1.2-.6 1.7l-.9 1.1c-.6.7-.2 1.9.8 1.9h9.8c1 0 1.4-1.2.8-1.9l-.9-1.1c-.4-.5-.6-1.2-.6-1.7V7c0-2.6-1.7-4.5-4.2-4.5Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
        <path d="M8.3 16.3a1.9 1.9 0 0 0 3.4 0" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
      </svg>
      <span class="bell-badge" v-if="store.unreadCount">{{ store.unreadCount > 9 ? '9+' : store.unreadCount }}</span>
    </button>
    <!-- Телепортируем панель в <body>, чтобы она всегда была поверх любой
         страницы/раздела и никогда не обрезалась контейнерами с overflow. -->
    <Teleport to="body">
      <div class="bell-dropdown" v-if="open" ref="panelEl" :style="panelStyle" @click.stop>
        <div class="bell-dropdown-header">
          <span>Уведомления</span>
          <button class="bell-mark-all" v-if="store.unreadCount" @click="markAll" type="button">Прочитать всё</button>
        </div>
        <div class="bell-empty" v-if="store.items.length === 0">Пока нет уведомлений</div>
        <div
          class="bell-item" v-for="n in store.items" :key="n.id"
          :class="{ unread: !n.is_read }" @click="openItem(n)"
        >
          <div class="bell-item-text">{{ n.text }}</div>
          <div class="bell-item-time">{{ formatTime(n.created_at) }}</div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
