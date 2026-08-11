<script setup>
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
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
const form = reactive({ title: '', description: '', link_url: '', starts_at: '', course: null })
const search = ref('')
const courseFilter = ref('')
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

function openCreate() {
  form.title = ''
  form.description = ''
  form.link_url = ''
  form.starts_at = ''
  form.course = null
  showModal.value = true
}

// Ученик может ввести ссылку без «https://» (просто example.com) — сервер
// такое не примет как валидный URL, поэтому молча дополняем схему сами,
// чтобы не спотыкаться на этом при сохранении.
function normalizeLink(url) {
  const trimmed = (url || '').trim()
  if (!trimmed) return ''
  if (/^https?:\/\//i.test(trimmed)) return trimmed
  return `https://${trimmed}`
}

async function save() {
  if (!form.title.trim() || !form.starts_at) { ui.showToast('Укажите название и дату', 'error'); return }
  try {
    await store.createNews({
      ...form,
      link_url: normalizeLink(form.link_url),
      starts_at: new Date(form.starts_at).toISOString(),
    })
    ui.showToast('Новость добавлена', 'success')
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
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
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
          <div><h1>Новости</h1><p>Видят ученики выбранного тренинга (или все, если тренинг не указан)</p></div>
          <button class="btn-primary" style="width:auto; padding:12px 22px" @click="openCreate">+ Добавить новость</button>
        </div>
        <div class="search-row">
          <input class="search-input" v-model="search" placeholder="Поиск по названию или описанию...">
          <select v-model="courseFilter">
            <option value="">Все тренинги</option>
            <option value="none">Только общие</option>
            <option v-for="c in admin.adminCourses" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>
        </div>
        <table>
          <thead><tr><th>Дата</th><th>Новость</th><th>Описание</th><th>Ссылка</th><th>Тренинг</th><th></th></tr></thead>
          <tbody>
            <tr v-for="n in store.items" :key="n.id">
              <td>{{ formatDate(n.starts_at) }}</td>
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
              <td class="row-actions"><button @click="remove(n.id)" title="Удалить">✕</button></td>
            </tr>
          </tbody>
        </table>
        <p v-if="store.items.length === 0" style="color:var(--text-dim); margin-top:12px;">Новостей пока нет.</p>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal">
        <h3>Новая новость</h3>
        <div class="field"><label>Название</label><input v-model="form.title" placeholder="Открытие урока «Скулы и контуринг»"></div>
        <div class="field"><label>Описание</label><textarea v-model="form.description" rows="4" placeholder="Подробности новости — необязательно"></textarea></div>
        <div class="field"><label>Ссылка (необязательно)</label><input type="url" v-model="form.link_url" placeholder="https://..."></div>
        <div class="field"><label>Дата и время</label><input type="datetime-local" v-model="form.starts_at"></div>
        <div class="field">
          <label>Тренинг (необязательно — иначе видят все ученики)</label>
          <select v-model="form.course">
            <option :value="null">Для всех</option>
            <option v-for="c in admin.adminCourses" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="showModal = false">Отмена</button>
          <button class="btn-primary" @click="save">Добавить</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" :class="{ active: viewItem }">
      <div class="modal" v-if="viewItem">
        <h3>{{ viewItem.title }}</h3>
        <p class="mod-sub">{{ formatDate(viewItem.starts_at) }} · {{ viewItem.course_title || 'Для всех' }}</p>
        <p class="news-full-text">{{ viewItem.description }}</p>
        <p v-if="viewItem.link_url"><a :href="viewItem.link_url" target="_blank" rel="noopener" style="color:var(--gold);">{{ viewItem.link_url }}</a></p>
        <div class="modal-footer">
          <button class="btn-primary" @click="viewItem = null">Закрыть</button>
        </div>
      </div>
    </div>
  </div>
</template>
