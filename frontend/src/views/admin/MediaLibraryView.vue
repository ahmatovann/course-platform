<script setup>
import { computed, onMounted, ref } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useAdminStore } from '../../store/admin'
import { useUiStore } from '../../store/ui'
import { detectKind, iconForKind, labelForKind } from '../../utils/fileKind'
import { adminLinks as links } from '../../nav'

const admin = useAdminStore()
const ui = useUiStore()
const search = ref('')
const typeFilter = ref('')
const usageItemId = ref(null)
const previewItem = ref(null)

onMounted(() => admin.fetchMedia())

// Раздел «Материалы» — независимая библиотека файлов: загружаются сюда
// напрямую (без привязки к уроку), а потом выбираются в конструкторе
// тренинга при добавлении урока (см. CoursesView.vue → «Выбрать из
// Материалы»), без повторной загрузки того же файла.
const materials = computed(() => {
  const q = search.value.trim().toLowerCase()
  const items = admin.media.filter((m) => (
    (m.type === 'material' || m.type === 'video') &&
    (!typeFilter.value || m.file_kind === typeFilter.value || (typeFilter.value === 'video' && m.type === 'video'))
  ))
  if (!q) return items
  return items.filter((m) => m.name.toLowerCase().includes(q) || m.used_in.toLowerCase().includes(q))
})

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}

// ===== Добавление нового материала =====
const showUploadModal = ref(false)
const uploadForm = ref({ name: '', file: null })

function openUpload() {
  uploadForm.value = { name: '', file: null }
  showUploadModal.value = true
}

function onUploadFilePicked(e) {
  const file = e.target.files[0] || null
  uploadForm.value.file = file
  if (file && !uploadForm.value.name) uploadForm.value.name = file.name.replace(/\.[^.]+$/, '')
}

async function submitUpload() {
  if (!uploadForm.value.name.trim() || !uploadForm.value.file) {
    ui.showToast('Укажите название и выберите файл', 'error')
    return
  }
  try {
    const kind = detectKind(uploadForm.value.file)
    await admin.uploadLibraryMaterial({ name: uploadForm.value.name, kind, file: uploadForm.value.file })
    ui.showToast('Материал добавлен в библиотеку', 'success')
    showUploadModal.value = false
  } catch (e) {
    const msg = e.response?.data ? Object.values(e.response.data).flat().join(' ') : 'Не удалось загрузить файл'
    ui.showToast(msg, 'error')
  }
}

// ===== Изменение (переименовать и/или заменить файл) =====
const editItem = ref(null)
const editForm = ref({ name: '', file: null })

function openEdit(item) {
  editItem.value = item
  editForm.value = { name: item.name, file: null }
}

function toggleUsage(item) {
  usageItemId.value = usageItemId.value === item.id ? null : item.id
}

function openPreview(item) {
  previewItem.value = item
}

function onEditFilePicked(e) {
  editForm.value.file = e.target.files[0] || null
}

async function submitEdit() {
  if (!editForm.value.name.trim()) { ui.showToast('Введите название', 'error'); return }
  try {
      if (editItem.value.type === 'video' && editItem.value.lesson_id) {
      await admin.renameLessonVideo(editItem.value.lesson_id, editForm.value.name)
    } else {
      await admin.updateMaterial(editItem.value.material_id, { name: editForm.value.name, file: editForm.value.file })
    }
    await admin.fetchMedia()
    ui.showToast('Материал изменён', 'success')
    editItem.value = null
  } catch (e) {
    ui.showToast('Не удалось изменить материал', 'error')
  }
}

// ===== Удаление =====
async function remove(item) {
  if (!confirm(`Удалить материал «${item.name}»?`)) return
  if (item.type === 'video' && item.lesson_id) await admin.deleteLessonVideo(item.lesson_id)
  else await admin.deleteLibraryMaterial(item.material_id)
  ui.showToast('Материал удалён', 'success')
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>Материалы</h1><p>Общая библиотека файлов — загружайте сюда один раз, прикрепляйте к любым урокам без повторной загрузки</p></div>
          <button class="btn-primary" style="width:auto; padding:12px 22px" @click="openUpload">+ Добавить материал</button>
        </div>
        <div class="search-row">
          <input class="search-input" v-model="search" placeholder="Поиск по названию или месту использования...">
          <select v-model="typeFilter" title="Фильтр по типу">
            <option value="">Все типы</option>
            <option value="pdf">PDF</option>
            <option value="video">Видео</option>
            <option value="image">Изображения</option>
            <option value="file">Файлы</option>
          </select>
        </div>

        <table>
          <thead><tr><th>Тип</th><th>Название</th><th>Размер</th><th>Используется</th><th></th></tr></thead>
          <tbody>
            <tr v-for="m in materials" :key="m.id">
              <td>{{ iconForKind(m.file_kind) }} {{ labelForKind(m.file_kind) }}</td>
              <td>
                <button v-if="m.type === 'video' || m.file_kind === 'video'" class="text-button" @click="openPreview(m)">
                  ▶ {{ m.name }}
                </button>
                <a v-else :href="m.url" target="_blank" rel="noopener">{{ m.name }}</a>
              </td>
              <td>{{ formatSize(m.size_bytes) }}</td>
              <td style="color:var(--text-dim); font-size:12.5px;">
                <button class="text-button" @click="toggleUsage(m)">
                  Используется {{ m.usage_count || 0 }} {{ (m.usage_count || 0) === 1 ? 'раз' : 'раза' }}
                </button>
                <div v-if="usageItemId === m.id" class="usage-list">
                  <div v-for="place in m.usage_places" :key="place">{{ place }}</div>
                  <div v-if="!m.usage_places?.length">Пока не прикреплён к урокам</div>
                </div>
              </td>
              <td class="row-actions">
                <button @click="openEdit(m)" title="Изменить">✎</button>
                <button @click="remove(m)" title="Удалить">✕</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="materials.length === 0" style="color:var(--text-dim); margin-top:12px;">
          Материалов пока нет — добавьте первый, чтобы потом выбирать его при построении тренинга.
        </p>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: showUploadModal }">
      <div class="modal">
        <h3>Новый материал</h3>
        <p class="mod-sub">Файл сразу попадёт в общую библиотеку — прикрепить к уроку(-ам) можно позже в конструкторе тренинга.</p>
        <div class="field"><label>Название</label><input v-model="uploadForm.name" placeholder="Рабочая тетрадь — модуль 1"></div>
        <div class="field">
          <label>Файл</label>
          <input type="file" accept="video/*,.pdf,.xls,.xlsx,.csv,.doc,.docx,.ppt,.pptx,.zip,.rar" @change="onUploadFilePicked">
          <div class="hint" v-if="uploadForm.file">Тип определён автоматически: {{ labelForKind(detectKind(uploadForm.file)) }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="showUploadModal = false">Отмена</button>
          <button class="btn-primary" @click="submitUpload">Добавить</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" :class="{ active: editItem }">
      <div class="modal" v-if="editItem">
        <h3>Изменить материал</h3>
        <div class="field"><label>Название</label><input v-model="editForm.name" placeholder="Название файла"></div>
        <div class="field">
          <label>Заменить файл (необязательно)</label>
          <input v-if="editItem.type !== 'video' || !editItem.lesson_id" type="file" @change="onEditFilePicked">
          <div class="hint">Для видео доступно переименование, для файлов также можно заменить PDF или другой файл.</div>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="editItem = null">Отмена</button>
          <button class="btn-primary" @click="submitEdit">Сохранить</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" :class="{ active: previewItem }" @click.self="previewItem = null">
      <div class="modal video-preview-modal" v-if="previewItem">
        <h3>{{ previewItem.name }}</h3>
        <video :src="previewItem.url" controls autoplay style="width:100%; max-height:65vh; background:#000;"></video>
        <div class="modal-footer">
          <button class="btn-ghost" @click="previewItem = null">Закрыть</button>
          <a class="btn-primary" :href="previewItem.url" target="_blank" rel="noopener">Открыть отдельно</a>
        </div>
      </div>
    </div>
  </div>
</template>
