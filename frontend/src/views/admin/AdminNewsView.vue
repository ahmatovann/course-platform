<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useNewsStore } from '../../store/news'
import { useAdminStore } from '../../store/admin'
import { useUiStore } from '../../store/ui'
import { adminLinks as links } from '../../nav'

const store = useNewsStore()
const admin = useAdminStore()
const ui = useUiStore()
const showModal = ref(false)
const viewItem = ref(null)
const editingId = ref(null)
const form = reactive({ title: '', description: '', link_url: '', publish_at: '', hide_at: '', course: null })
const search = ref('')
const courseFilter = ref('')
const sortBy = ref('publish_desc')
let debounceTimer = null

onMounted(async () => {
  await store.fetchNews()
  await admin.fetchAdminCourses()
})

watch([search, courseFilter], () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    store.fetchNews({ search: search.value || undefined, course: courseFilter.value || undefined })
  }, 300)
})
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

const statusLabels = { scheduled: 'Запланирована', published: 'Опубликована', hidden: 'Скрыта' }
const statusClass = { scheduled: 'pending', published: 'ok', hidden: 'locked' }

// Сортировка списка новостей — по дате рассылки или по названию, рядом с
// поиском/фильтром по тренингу.
const sortedItems = computed(() => {
  const items = [...store.items]
  switch (sortBy.value) {
    case 'publish_asc':
      return items.sort((a, b) => a.publish_at.localeCompare(b.publish_at))
    case 'title_asc':
      return items.sort((a, b) => a.title.localeCompare(b.title, 'ru'))
    case 'title_desc':
      return items.sort((a, b) => b.title.localeCompare(a.title, 'ru'))
    case 'publish_desc':
    default:
      return items.sort((a, b) => b.publish_at.localeCompare(a.publish_at))
  }
})

// input type="datetime-local" ожидает строку в локальном времени без
// таймзоны (YYYY-MM-DDTHH:mm), поэтому форматируем Date/ISO вручную.
function toLocalInput(value) {
  if (!value) return ''
  const date = value instanceof Date ? value : new Date(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function openCreate() {
  editingId.value = null
  form.title = ''
  form.description = ''
  form.link_url = ''
  // Дата и время рассылки по умолчанию — сейчас (новость публикуется
  // сразу), администратор при необходимости переносит на будущее.
  form.publish_at = toLocalInput(new Date())
  form.hide_at = ''
  form.course = null
  showModal.value = true
}

function openEdit(n) {
  editingId.value = n.id
  form.title = n.title
  form.description = n.description || ''
  form.link_url = n.link_url || ''
  form.publish_at = toLocalInput(n.publish_at)
  form.hide_at = n.hide_at ? toLocalInput(n.hide_at) : ''
  form.course = n.course
  showModal.value = true
}

// Администратор может ввести ссылку без «https://» (просто example.com) —
// сервер такое не примет как валидный URL, поэтому молча дополняем схему
// сами, чтобы не спотыкаться на этом при сохранении.
function normalizeLink(url) {
  const trimmed = (url || '').trim()
  if (!trimmed) return ''
  if (/^https?:\/\//i.test(trimmed)) return trimmed
  return `https://${trimmed}`
}

async function save() {
  if (!form.title.trim() || !form.publish_at) { ui.showToast('Укажите название, дату и время рассылки', 'error'); return }
  if (form.hide_at && form.hide_at <= form.publish_at) {
    ui.showToast('Дата и время скрытия должны быть позже даты и времени рассылки', 'error')
    return
  }
  const payload = {
    ...form,
    link_url: normalizeLink(form.link_url),
    hide_at: form.hide_at || null,
  }
  try {
    if (editingId.value) {
      await store.updateNews(editingId.value, payload)
      ui.showToast('Новость обновлена', 'success')
    } else {
      await store.createNews(payload)
      ui.showToast('Новость добавлена', 'success')
    }
    showModal.value = false
  } catch (e) {
    const msg = e.response?.data ? Object.values(e.response.data).flat().join(' ') : 'Ошибка сохранения'
    ui.showToast(msg, 'error')
  }
}

async function remove(id) {
  if (!confirm('Удалить новость?')) return
  await store.deleteNews(id)
  ui.showToast('Новость удалена', 'success')
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function excerpt(text) {
  if (!text) return ''
  return text.length > 100 ? text.slice(0, 100).trim() + '…' : text
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>Новости</h1><p>Видят ученики выбранного тренинга (или все, если тренинг не указан) начиная с даты рассылки</p></div>
          <button class="btn-primary" style="width:auto; padding:12px 22px" @click="openCreate">+ Добавить новость</button>
        </div>
        <div class="search-row">
          <input class="search-input" v-model="search" placeholder="Поиск по названию или описанию...">
          <select v-model="courseFilter">
            <option value="">Все тренинги</option>
            <option value="none">Только общие</option>
            <option v-for="c in admin.adminCourses" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>
          <select v-model="sortBy">
            <option value="publish_desc">Сначала новые</option>
            <option value="publish_asc">Сначала старые</option>
            <option value="title_asc">По названию А→Я</option>
            <option value="title_desc">По названию Я→А</option>
          </select>
        </div>
        <table>
          <thead><tr><th>Дата и время рассылки</th><th>Скрыть после</th><th>Статус</th><th>Новость</th><th>Описание</th><th>Ссылка</th><th>Тренинг</th><th></th></tr></thead>
          <tbody>
            <tr v-for="n in sortedItems" :key="n.id">
              <td>{{ formatDate(n.publish_at) }}</td>
              <td>{{ n.hide_at ? formatDate(n.hide_at) : '—' }}</td>
              <td><span class="badge" :class="statusClass[n.status]">{{ statusLabels[n.status] }}</span></td>
              <td>{{ n.title }}</td>
              <td>
                <span v-if="n.description" style="cursor:pointer; color:var(--gold);" @click="viewItem = n">{{ excerpt(n.description) }}</span>
                <span v-else style="color:var(--text-dim);">—</span>
              </td>
              <td>
                <a v-if="n.link_url" :href="n.link_url" target="_blank" rel="noopener" style="color:var(--gold);">Перейти</a>
                <span v-else style="color:var(--text-dim);">—</span>
              </td>
              <td>{{ n.course_title || 'Для всех' }}</td>
              <td class="row-actions">
                <button @click="openEdit(n)" title="Изменить">✎</button>
                <button @click="remove(n.id)" title="Удалить">✕</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="sortedItems.length === 0" style="color:var(--text-dim); margin-top:12px;">Новостей пока нет.</p>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal">
        <h3>{{ editingId ? 'Редактирование новости' : 'Новая новость' }}</h3>
        <div class="field"><label>Название</label><input v-model="form.title" placeholder="Открытие урока «Скулы и контуринг»"></div>
        <div class="field">
          <label>Описание</label>
          <textarea v-model="form.description" rows="4" placeholder="Подробности новости — необязательно"></textarea>
        </div>
        <div class="field"><label>Ссылка (необязательно)</label><input type="url" v-model="form.link_url" placeholder="https://..."></div>
        <div class="field">
          <label>Дата и время рассылки</label>
          <input type="datetime-local" v-model="form.publish_at">
          <div class="hint">С этого момента новость видна ученикам.</div>
        </div>
        <div class="field">
          <label>Дата и время скрытия (необязательно)</label>
          <input type="datetime-local" v-model="form.hide_at">
          <div class="hint">После этого момента новость автоматически перестанет быть видна ученикам (сама запись не удаляется).</div>
        </div>
        <div class="field">
          <label>Тренинг (необязательно — иначе видят все ученики)</label>
          <select v-model="form.course">
            <option :value="null">Для всех</option>
            <option v-for="c in admin.adminCourses" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="showModal = false">Отмена</button>
          <button class="btn-primary" @click="save">{{ editingId ? 'Сохранить' : 'Добавить' }}</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" :class="{ active: viewItem }">
      <div class="modal" v-if="viewItem">
        <h3>{{ viewItem.title }}</h3>
        <p class="mod-sub">{{ formatDate(viewItem.publish_at) }} · {{ viewItem.course_title || 'Для всех' }}</p>
        <p class="news-full-text">{{ viewItem.description }}</p>
        <p v-if="viewItem.link_url"><a :href="viewItem.link_url" target="_blank" rel="noopener" style="color:var(--gold);">{{ viewItem.link_url }}</a></p>
        <div class="modal-footer">
          <button class="btn-primary" @click="viewItem = null">Закрыть</button>
        </div>
      </div>
    </div>
  </div>
</template>
