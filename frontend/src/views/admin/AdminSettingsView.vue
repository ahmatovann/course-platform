<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useUiStore } from '../../store/ui'
import { useAdminStore } from '../../store/admin'
import { useAuthStore } from '../../store/auth'
import { iconForKind } from '../../utils/fileKind'
import { adminLinks as links } from '../../nav'

const ui = useUiStore()
const admin = useAdminStore()
const auth = useAuthStore()

// ===== Мой профиль (аватар администратора) =====
const avatarInput = ref(null)
const avatarPreview = ref(auth.user?.avatar || null)
const generatingAvatar = ref(false)
const savingAvatar = ref(false)
const showAvatarLightbox = ref(false)
const adminActivity = ref([])

function pickAvatar() {
  avatarInput.value?.click()
}

async function onAvatarChosen(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ui.showToast('Выберите файл изображения', 'error')
    return
  }
  avatarPreview.value = URL.createObjectURL(file)
  await saveAvatar(file)
}

// Бесплатные сгенерированные аватарки через DiceBear (без ключей и регистрации).
// Каждое нажатие — новый случайный вариант в выбранном стиле.
async function generateAvatar() {
  generatingAvatar.value = true
  try {
    const seed = Math.random().toString(36).slice(2)
    const url = `https://api.dicebear.com/9.x/lorelei/png?seed=${seed}&size=256`
    const res = await fetch(url)
    if (!res.ok) throw new Error('bad response')
    const blob = await res.blob()
    const file = new File([blob], `avatar-${seed}.png`, { type: 'image/png' })
    avatarPreview.value = URL.createObjectURL(blob)
    await saveAvatar(file)
  } catch (e) {
    ui.showToast('Не удалось сгенерировать аватар — проверьте интернет', 'error')
  } finally {
    generatingAvatar.value = false
  }
}

async function saveAvatar(file) {
  savingAvatar.value = true
  try {
    const payload = new FormData()
    payload.append('avatar', file)
    await auth.updateProfile(payload)
    ui.showToast('Фото профиля обновлено', 'success')
  } catch (e) {
    ui.showToast('Не удалось сохранить фото', 'error')
  } finally {
    savingAvatar.value = false
  }
}

// ===== Библиотека материалов (все видео уроков + файлы уроков) =====
const search = ref('')
const sortBy = ref('name_asc')
let debounceTimer = null

onMounted(async () => {
  await auth.fetchProfile()
  avatarPreview.value = auth.user?.avatar || null
  adminActivity.value = await admin.fetchAdminActivity()
  await load()
})

function formatActivityDate(value) {
  return new Date(value).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

watch([search, sortBy], () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(load, 300)
})
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

async function load() {
  await admin.fetchMedia({ search: search.value || undefined, sort: sortBy.value })
}

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return '—'
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`
}

function formatDuration(seconds) {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

// ===== Переименование =====
const renameItem = ref(null)
const renameValue = ref('')

function openRename(item) {
  renameItem.value = item
  renameValue.value = item.name
}

async function saveRename() {
  const item = renameItem.value
  if (!item || !renameValue.value.trim()) return
  try {
    if (item.type === 'video') {
      await admin.renameLessonVideo(item.lesson_id, renameValue.value.trim())
    } else {
      await admin.renameMaterial(item.material_id, renameValue.value.trim())
    }
    ui.showToast('Название обновлено', 'success')
    renameItem.value = null
    await load()
  } catch (e) {
    ui.showToast('Не удалось переименовать', 'error')
  }
}

// ===== Удаление =====
async function removeItem(item) {
  const what = item.type === 'video' ? 'видео' : 'файл'
  if (!confirm(`Удалить ${what} «${item.name}»? Это уберёт его из урока.`)) return
  try {
    if (item.type === 'video') {
      await admin.deleteLessonVideo(item.lesson_id)
    } else {
      await admin.deleteMaterial(item.material_id)
    }
    ui.showToast('Удалено', 'success')
    await load()
  } catch (e) {
    ui.showToast('Не удалось удалить', 'error')
  }
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header"><div><h1>Настройки</h1><p>Оформление и параметры кабинета</p></div></div>

        <div class="mini-card" style="max-width:460px;">
          <h4>Мой профиль</h4>
          <div class="profile-avatar-row">
            <button
              type="button" class="profile-avatar-lg profile-avatar-lg-edit" :class="{ clickable: avatarPreview }"
              @click="avatarPreview && (showAvatarLightbox = true)"
            >
              <img v-if="avatarPreview" :src="avatarPreview" alt="">
              <span v-else>CA</span>
            </button>
            <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="onAvatarChosen">
            <div class="profile-avatar-links">
              <button type="button" class="avatar-action-btn" :disabled="savingAvatar" @click="pickAvatar">Загрузить фото</button>
              <button type="button" class="avatar-action-btn" :disabled="generatingAvatar || savingAvatar" @click="generateAvatar">
                {{ generatingAvatar ? 'Генерируем...' : 'Сгенерировать аватар' }}
              </button>
            </div>
          </div>
        </div>

        <div class="mini-card" style="max-width:460px; margin-top:20px;">
          <h4>Настройки</h4>
          <div class="settings-row">
            <div class="lbl">Оформление<small>Тёмная или светлая тема интерфейса</small></div>
            <div class="settings-switch">
              <button type="button" :class="{ active: ui.theme === 'dark' }" @click="ui.setTheme('dark')">Тёмная</button>
              <button type="button" :class="{ active: ui.theme === 'light' }" @click="ui.setTheme('light')">Светлая</button>
            </div>
          </div>
        </div>

        <div class="mini-card admin-history-card">
          <h4>История действий</h4>
          <p class="section-subtitle">Действия администратора по ученикам и курсам</p>
          <div class="admin-history-table" v-if="adminActivity.length">
            <div class="admin-history-row admin-history-head"><span>Когда</span><span>Действие</span></div>
            <div class="admin-history-row" v-for="item in adminActivity" :key="item.id">
              <time>{{ formatActivityDate(item.created_at) }}</time><span>{{ item.description }}<small v-if="item.student_name && item.student_name !== 'Общее действие'"> · {{ item.student_name }}</small></span>
            </div>
          </div>
          <p v-else class="empty-state">История пока пуста.</p>
        </div>

        <div v-if="false" class="mini-card" style="margin-top:20px;">
          <h4>Материалы</h4>
          <p style="color:var(--text-dim); font-size:12.5px; margin:-4px 0 14px;">Все загруженные видео уроков и файлы — в одном месте: где используются, размер, переименование и удаление</p>

          <div class="search-row">
            <input class="search-input" v-model="search" placeholder="Поиск по названию или тренингу...">
            <select v-model="sortBy" title="Сортировка">
              <option value="name_asc">Название А→Я</option>
              <option value="name_desc">Название Я→А</option>
              <option value="size_desc">Сначала большие</option>
              <option value="size_asc">Сначала маленькие</option>
              <option value="used_in_asc">По тренингу</option>
            </select>
          </div>

          <table>
            <thead>
              <tr><th></th><th>Название</th><th>Тип</th><th>Размер</th><th>Где используется</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="item in admin.media" :key="item.id">
                <td style="width:56px;">
                  <img v-if="item.thumb" :src="item.thumb" alt="" style="width:44px; height:44px; object-fit:cover; border-radius:8px; display:block;">
                  <div v-else style="width:44px; height:44px; border-radius:8px; background:var(--navy-deep); display:flex; align-items:center; justify-content:center; font-size:18px; color:var(--gold);">
                    {{ item.type === 'video' ? '▶' : iconForKind(item.file_kind) }}
                  </div>
                </td>
                <td>
                  <a :href="item.url" target="_blank" rel="noopener" style="color:var(--text-hi);">{{ item.name }}</a>
                  <span v-if="item.duration_seconds" style="color:var(--text-dim); font-size:11.5px;"> · {{ formatDuration(item.duration_seconds) }}</span>
                </td>
                <td>{{ item.kind_label }}</td>
                <td>{{ formatSize(item.size_bytes) }}</td>
                <td style="color:var(--text-mid); font-size:12.5px;">{{ item.used_in }}</td>
                <td class="row-actions">
                  <button @click="openRename(item)" title="Изменить название">✎</button>
                  <button @click="removeItem(item)" title="Удалить">✕</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="admin.media.length === 0" style="color:var(--text-dim); margin-top:12px;">Пока ничего не загружено — видео и файлы уроков появятся здесь автоматически.</p>
        </div>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: renameItem }">
      <div class="modal" v-if="renameItem">
        <h3>Переименовать</h3>
        <p class="mod-sub">{{ renameItem.used_in }}</p>
        <div class="field"><label>Название</label><input v-model="renameValue" @keyup.enter="saveRename"></div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="renameItem = null">Отмена</button>
          <button class="btn-primary" @click="saveRename">Сохранить</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay avatar-lightbox-overlay" :class="{ active: showAvatarLightbox }" @click="showAvatarLightbox = false">
      <button type="button" class="avatar-lightbox-close" @click="showAvatarLightbox = false" aria-label="Закрыть">×</button>
      <img v-if="avatarPreview" :src="avatarPreview" class="avatar-lightbox-img" alt="Фото профиля" @click.stop>
    </div>
  </div>
</template>
