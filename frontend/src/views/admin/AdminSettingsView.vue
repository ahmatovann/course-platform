<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useUiStore } from '../../store/ui'
import { useAdminStore } from '../../store/admin'
import { useAuthStore } from '../../store/auth'
import AvatarCropper from '../../components/common/AvatarCropper.vue'
import VideoTrimModal from '../../components/common/VideoTrimModal.vue'
import { detectKind, iconForKind } from '../../utils/fileKind'
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

function pickAvatar() {
  avatarInput.value?.click()
}

// Фото сначала идёт в редактор кадрирования (кроп под ровный квадрат
// нужного размера) — сохраняется только результат кропа.
const cropperFile = ref(null)

function onAvatarChosen(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ui.showToast('Выберите файл изображения', 'error')
    return
  }
  cropperFile.value = file
}

async function onCropSave(croppedFile) {
  avatarPreview.value = URL.createObjectURL(croppedFile)
  cropperFile.value = null
  await saveAvatar(croppedFile)
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

onMounted(() => {
  load()
  // Нужно для выпадающих списков «Курс → Модуль → Урок» в форме «+ Добавить материал».
  admin.fetchAdminCourses()
})

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

// ===== История действий администратора =====
onMounted(() => admin.fetchAuditLog())

const actionLabels = { created: 'создал(а)', updated: 'изменил(а)', deleted: 'удалил(а)', toggled: 'переключил(а)' }

function formatLogDate(iso) {
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// ===== Подробности по файлу: где именно (во всех местах) он используется =====
// Один и тот же файл может быть прикреплён сразу к нескольким урокам (см.
// бэкенд AdminMediaListView) — вместо N одинаковых строк список показывает
// одну строку с пометкой «Используется в N местах», а по клику открывается
// это окно с полным перечнем и действиями (переименовать/удалить) для
// каждого места по отдельности.
const detailItem = ref(null)
function openDetail(item) {
  detailItem.value = item
}
function closeDetail() {
  detailItem.value = null
}

// ===== Переименование (действует на конкретное место использования —
// одну запись Material либо видео одного конкретного урока) =====
const renameTarget = ref(null)
const renameValue = ref('')

function openRename(usage) {
  renameTarget.value = usage
  renameValue.value = usage.name
}

async function saveRename() {
  const target = renameTarget.value
  if (!target || !renameValue.value.trim()) return
  try {
    if (target.kind === 'lesson_video') {
      await admin.renameLessonVideo(target.lesson_id, renameValue.value.trim())
    } else {
      await admin.renameMaterial(target.material_id, renameValue.value.trim())
    }
    ui.showToast('Название обновлено', 'success')
    renameTarget.value = null
    await load()
    // Если переименовывали из окна подробностей — оно ссылается на уже
    // устаревший список usages, закрываем, чтобы не путать.
    closeDetail()
  } catch (e) {
    ui.showToast('Не удалось переименовать', 'error')
  }
}

// ===== Обрезка видео =====
const trimTarget = ref(null)

function openTrim(item) {
  const usage = item.usages[0]
  trimTarget.value = { lessonId: usage.lesson_id, videoUrl: item.url, duration: item.duration_seconds }
}

async function onTrimmed() {
  trimTarget.value = null
  await load()
}

// ===== Удаление одного места использования =====
async function removeUsage(usage) {
  const what = usage.kind === 'lesson_video' ? 'видео' : 'файл'
  if (!confirm(`Удалить ${what} «${usage.name}»? Это уберёт его из урока «${usage.lesson_title}».`)) return
  try {
    if (usage.kind === 'lesson_video') {
      await admin.deleteLessonVideo(usage.lesson_id)
    } else {
      await admin.deleteMaterial(usage.material_id)
    }
    ui.showToast('Удалено', 'success')
    await load()
    closeDetail()
  } catch (e) {
    ui.showToast('Не удалось удалить', 'error')
  }
}

// ===== Добавление нового материала прямо из библиотеки (без захода в
// конструктор тренинга) — админ выбирает урок, к которому прикрепится файл =====
const showAddModal = ref(false)
const addForm = reactive({ courseId: null, moduleId: null, lessonId: null, name: '', file: null })

const modulesForCourse = computed(() => {
  const course = admin.adminCourses.find((c) => c.id === addForm.courseId)
  return course?.modules || []
})
const lessonsForModule = computed(() => {
  const mod = modulesForCourse.value.find((m) => m.id === addForm.moduleId)
  return mod?.lessons || []
})

watch(() => addForm.courseId, () => { addForm.moduleId = null; addForm.lessonId = null })
watch(() => addForm.moduleId, () => { addForm.lessonId = null })

function openAddModal() {
  addForm.courseId = admin.adminCourses[0]?.id || null
  addForm.moduleId = null
  addForm.lessonId = null
  addForm.name = ''
  addForm.file = null
  showAddModal.value = true
}

function onAddFilePicked(e) {
  addForm.file = e.target.files[0] || null
}

async function submitAddMaterial() {
  if (!addForm.lessonId) { ui.showToast('Выберите урок, к которому прикрепить файл', 'error'); return }
  if (!addForm.name.trim() || !addForm.file) { ui.showToast('Укажите название и выберите файл', 'error'); return }
  try {
    const kind = detectKind(addForm.file)
    await admin.addMaterial(addForm.lessonId, { name: addForm.name, kind, file: addForm.file })
    ui.showToast('Материал добавлен', 'success')
    showAddModal.value = false
    await load()
  } catch (e) {
    const msg = e.response?.data ? Object.values(e.response.data).flat().join(' ') : 'Не удалось добавить материал'
    ui.showToast(msg, 'error')
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

        <div class="mini-card" style="margin-top:20px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
            <div>
              <h4>Материалы</h4>
              <p style="color:var(--text-dim); font-size:12.5px; margin:-4px 0 14px;">Все загруженные видео уроков и файлы — в одном месте: где используются, размер, переименование и удаление</p>
            </div>
            <button class="btn-primary" style="width:auto; padding:9px 16px; white-space:nowrap;" @click="openAddModal">+ Добавить материал</button>
          </div>

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
                <td style="color:var(--text-mid); font-size:12.5px;">
                  <span v-if="item.used_in_count === 1">{{ item.used_in }}</span>
                  <button v-else type="button" class="link-btn" style="font-size:12.5px;" @click="openDetail(item)">{{ item.used_in }} ▸</button>
                </td>
                <td class="row-actions">
                  <template v-if="item.used_in_count === 1">
                    <button v-if="item.type === 'video'" @click="openTrim(item)" title="Обрезать видео">✂</button>
                    <button @click="openRename(item.usages[0])" title="Изменить название">✎</button>
                    <button @click="removeUsage(item.usages[0])" title="Удалить">✕</button>
                  </template>
                  <button v-else @click="openDetail(item)" title="Показать все места использования">Подробнее</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="admin.media.length === 0" style="color:var(--text-dim); margin-top:12px;">Пока ничего не загружено — видео и файлы уроков появятся здесь автоматически, либо добавьте материал вручную кнопкой выше.</p>
        </div>

        <div class="mini-card" style="margin-top:20px;">
          <h4>История</h4>
          <p style="color:var(--text-dim); font-size:12.5px; margin:-4px 0 14px;">Действия администраторов — кто и что сделал, сначала новые</p>
          <table>
            <thead><tr><th>Когда</th><th>Кто</th><th>Действие</th></tr></thead>
            <tbody>
              <tr v-for="entry in admin.auditLog" :key="entry.id">
                <td style="white-space:nowrap; color:var(--text-dim); font-size:12.5px;">{{ formatLogDate(entry.created_at) }}</td>
                <td>{{ entry.actor_name }}</td>
                <td>{{ actionLabels[entry.action] || entry.action }} {{ entry.target_type }} «{{ entry.target_repr }}»</td>
              </tr>
            </tbody>
          </table>
          <p v-if="admin.auditLog.length === 0" style="color:var(--text-dim); margin-top:12px;">Пока ничего не записано.</p>
        </div>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: renameTarget }">
      <div class="modal" v-if="renameTarget">
        <h3>Переименовать</h3>
        <p class="mod-sub">{{ renameTarget.label }}</p>
        <div class="field"><label>Название</label><input v-model="renameValue" @keyup.enter="saveRename"></div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="renameTarget = null">Отмена</button>
          <button class="btn-primary" @click="saveRename">Сохранить</button>
        </div>
      </div>
    </div>

    <!-- Подробности: полный список мест использования одного файла -->
    <div class="modal-overlay" :class="{ active: detailItem }" @click="closeDetail">
      <div class="modal" v-if="detailItem" @click.stop>
        <h3>{{ detailItem.name }}</h3>
        <p class="mod-sub">{{ detailItem.kind_label }} · {{ formatSize(detailItem.size_bytes) }} · используется в {{ detailItem.used_in_count }} местах</p>
        <div style="display:flex; flex-direction:column; gap:8px; max-height:340px; overflow-y:auto; margin:14px 0;">
          <div
            v-for="usage in detailItem.usages" :key="usage.kind + '-' + (usage.material_id || usage.lesson_id)"
            style="display:flex; align-items:center; gap:10px; padding:9px 10px; border-radius:8px; background:var(--navy-deep);"
          >
            <span style="flex:1; min-width:0; font-size:13px; color:var(--text-hi); overflow-wrap:anywhere;">{{ usage.label }}</span>
            <button class="dl-btn" style="padding:4px 10px;" @click="openRename(usage)">✎</button>
            <button class="dl-btn" style="padding:4px 10px; border-color:var(--danger); color:var(--danger);" @click="removeUsage(usage)">✕</button>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-primary" @click="closeDetail">Закрыть</button>
        </div>
      </div>
    </div>

    <!-- Добавить материал: выбор урока (курс → модуль → урок) + файл -->
    <div class="modal-overlay" :class="{ active: showAddModal }">
      <div class="modal" v-if="showAddModal">
        <h3>Добавить материал</h3>
        <p class="mod-sub">Файл прикрепится к выбранному уроку — так же, как при добавлении из конструктора тренинга.</p>
        <div class="field">
          <label>Тренинг</label>
          <select v-model.number="addForm.courseId">
            <option v-for="c in admin.adminCourses" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>
        </div>
        <div class="field">
          <label>Модуль</label>
          <select v-model.number="addForm.moduleId" :disabled="!modulesForCourse.length">
            <option :value="null" disabled>Выберите модуль</option>
            <option v-for="m in modulesForCourse" :key="m.id" :value="m.id">{{ m.title }}</option>
          </select>
        </div>
        <div class="field">
          <label>Урок</label>
          <select v-model.number="addForm.lessonId" :disabled="!lessonsForModule.length">
            <option :value="null" disabled>Выберите урок</option>
            <option v-for="l in lessonsForModule" :key="l.id" :value="l.id">{{ l.title }}</option>
          </select>
          <div class="hint" v-if="addForm.moduleId && !lessonsForModule.length">В этом модуле пока нет уроков.</div>
        </div>
        <div class="field"><label>Название файла</label><input v-model="addForm.name" placeholder="Например: Чек-лист по уходу"></div>
        <div class="field">
          <label>Файл</label>
          <input type="file" @change="onAddFilePicked">
          <div class="hint" v-if="addForm.file">Тип определён автоматически.</div>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="showAddModal = false">Отмена</button>
          <button class="btn-primary" @click="submitAddMaterial">Добавить</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay avatar-lightbox-overlay" :class="{ active: showAvatarLightbox }" @click="showAvatarLightbox = false">
      <button type="button" class="avatar-lightbox-close" @click="showAvatarLightbox = false" aria-label="Закрыть">×</button>
      <img v-if="avatarPreview" :src="avatarPreview" class="avatar-lightbox-img" alt="Фото профиля" @click.stop>
    </div>

    <AvatarCropper :file="cropperFile" @save="onCropSave" @cancel="cropperFile = null" />
    <VideoTrimModal :video="trimTarget" @trimmed="onTrimmed" @cancel="trimTarget = null" />
  </div>
</template>
