<script setup>
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useAdminStore } from '../../store/admin'
import { useUiStore } from '../../store/ui'
import { detectKind, iconForKind, labelForKind } from '../../utils/fileKind'
import VideoTrimModal from '../../components/common/VideoTrimModal.vue'

import { adminLinks as links } from '../../nav'

const admin = useAdminStore()
const ui = useUiStore()
const search = ref('')
let debounceTimer = null
const showLessonModal = ref(false)
const lessonForm = reactive({ id: null, moduleId: null, title: '', description: '', video_url: '', video_file: '', duration_seconds: 0, materials: [] })
const videoFile = ref(null)
const materialForm = reactive({ name: '', file: null })

const showCourseModal = ref(false)
const courseForm = reactive({ title: '', description: '' })
const showModuleModal = ref(false)
const moduleForm = reactive({ courseId: null, title: '' })

const expandedModuleId = ref(null)
function toggleModule(id) {
  expandedModuleId.value = expandedModuleId.value === id ? null : id
}

onMounted(() => admin.fetchAdminCourses())

watch(search, () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    admin.fetchAdminCourses({ search: search.value || undefined })
  }, 300)
})
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

async function saveModule(m) {
  await admin.updateModule(m.id, {
    require_test_to_unlock_next: m.require_test_to_unlock_next,
    pass_threshold_percent: m.pass_threshold_percent,
  })
  ui.showToast('Настройки модуля сохранены', 'success')
}

function resetMaterialForm() {
  materialForm.name = ''
  materialForm.file = null
}

function openAddLesson(moduleId) {
  lessonForm.id = null
  lessonForm.moduleId = moduleId
  lessonForm.title = ''
  lessonForm.description = ''
  lessonForm.video_url = ''
  lessonForm.video_file = ''
  lessonForm.duration_seconds = 0
  lessonForm.materials = []
  videoFile.value = null
  resetMaterialForm()
  showLessonModal.value = true
}

function openEditLesson(moduleId, lesson) {
  lessonForm.id = lesson.id
  lessonForm.moduleId = moduleId
  lessonForm.title = lesson.title
  lessonForm.description = lesson.description || ''
  lessonForm.video_url = lesson.video_url
  lessonForm.video_file = lesson.video_file || ''
  lessonForm.duration_seconds = lesson.duration_seconds
  lessonForm.materials = lesson.materials || []
  videoFile.value = null
  resetMaterialForm()
  showLessonModal.value = true
}

// Создаёт урок «на лету», если он ещё не сохранён (например, ученик сразу
// пытается прикрепить файл к новому уроку, не нажимая отдельную кнопку
// «Сохранить») — иначе прикрепление материалов упиралось в требование
// сначала вручную сохранить урок и молча ничего не делало.
async function ensureLessonId() {
  if (lessonForm.id) return lessonForm.id
  if (!lessonForm.title.trim()) {
    ui.showToast('Сначала введите название урока', 'error')
    return null
  }
  const payload = {
    title: lessonForm.title,
    description: lessonForm.description,
    video_url: lessonForm.video_url,
    duration_seconds: Number(lessonForm.duration_seconds) || 0,
  }
  const created = await admin.createLesson(lessonForm.moduleId, payload)
  lessonForm.id = created.id
  ui.showToast('Урок сохранён — можно прикреплять видео и файлы', 'success')
  return created.id
}

async function saveLesson() {
  if (!lessonForm.title.trim()) { ui.showToast('Введите название урока', 'error'); return }
  const payload = {
    title: lessonForm.title,
    description: lessonForm.description,
    video_url: lessonForm.video_url,
    duration_seconds: Number(lessonForm.duration_seconds) || 0,
  }
  let lessonId = lessonForm.id
  if (lessonId) {
    await admin.updateLesson(lessonId, payload)
    ui.showToast('Урок обновлён', 'success')
  } else {
    lessonId = await ensureLessonId()
    if (!lessonId) return
  }
  if (videoFile.value) {
    const updated = await admin.uploadLessonVideo(lessonId, videoFile.value)
    lessonForm.video_file = updated.video_file || ''
    lessonForm.duration_seconds = updated.duration_seconds
    videoFile.value = null
    ui.showToast('Видео загружено', 'success')
  }
  refreshLessonMaterials(lessonId)
}

// ===== Обрезка видео =====
const trimTarget = ref(null)

function openTrim() {
  trimTarget.value = { lessonId: lessonForm.id, videoUrl: lessonForm.video_file, duration: lessonForm.duration_seconds }
}

async function onTrimmed(updated) {
  trimTarget.value = null
  lessonForm.video_file = updated.video_file || ''
  lessonForm.duration_seconds = updated.duration_seconds
  await admin.fetchAdminCourses()
}

function refreshLessonMaterials(lessonId) {
  for (const course of admin.adminCourses) {
    for (const m of course.modules) {
      const lesson = m.lessons.find((l) => l.id === lessonId)
      if (lesson) { lessonForm.materials = lesson.materials || [] }
    }
  }
}

// Длительность определяется автоматически из самого файла (через скрытый
// video-элемент), без ручного ввода секунд администратором.
function onVideoPicked(e) {
  const file = e.target.files[0] || null
  videoFile.value = file
  if (!file) return
  const url = URL.createObjectURL(file)
  const probe = document.createElement('video')
  probe.preload = 'metadata'
  probe.onloadedmetadata = () => {
    if (isFinite(probe.duration)) lessonForm.duration_seconds = Math.round(probe.duration)
    URL.revokeObjectURL(url)
  }
  probe.src = url
}

// Тип файла (изображение / аудио / PDF / презентация и т.д.) определяется
// автоматически по расширению и MIME — вручную выбирать не нужно.
function onMaterialPicked(e) {
  materialForm.file = e.target.files[0] || null
}

async function addMaterial() {
  if (!materialForm.name.trim() || !materialForm.file) { ui.showToast('Укажите название и выберите файл', 'error'); return }
  const lessonId = await ensureLessonId()
  if (!lessonId) return
  try {
    const kind = detectKind(materialForm.file)
    await admin.addMaterial(lessonId, { name: materialForm.name, kind, file: materialForm.file })
    ui.showToast('Файл добавлен', 'success')
    resetMaterialForm()
    refreshLessonMaterials(lessonId)
  } catch (e) {
    const msg = e.response?.data ? Object.values(e.response.data).flat().join(' ') : 'Не удалось загрузить файл'
    ui.showToast(msg, 'error')
  }
}

async function removeMaterial(id) {
  await admin.deleteMaterial(id)
  ui.showToast('Материал удалён', 'success')
  refreshLessonMaterials(lessonForm.id)
}

function openCreateCourse() {
  courseForm.title = ''
  courseForm.description = ''
  showCourseModal.value = true
}

async function saveCourse() {
  if (!courseForm.title.trim()) { ui.showToast('Введите название тренинга', 'error'); return }
  await admin.createCourse({ title: courseForm.title, description: courseForm.description })
  ui.showToast('Тренинг создан', 'success')
  showCourseModal.value = false
}

function openCreateModule(courseId) {
  moduleForm.courseId = courseId
  moduleForm.title = ''
  showModuleModal.value = true
}

async function saveModuleCreate() {
  if (!moduleForm.title.trim()) { ui.showToast('Введите название модуля', 'error'); return }
  await admin.createModule(moduleForm.courseId, { title: moduleForm.title })
  ui.showToast('Модуль добавлен', 'success')
  showModuleModal.value = false
}

async function removeLesson(id) {
  if (!confirm('Удалить урок?')) return
  await admin.deleteLesson(id)
  ui.showToast('Урок удалён', 'success')
}

async function removeModule(m) {
  if (!confirm(`Удалить модуль «${m.title}» вместе со всеми уроками и тестом?`)) return
  await admin.deleteModule(m.id)
  ui.showToast('Модуль удалён', 'success')
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>Конструктор тренинга</h1><p>Настройка модулей, порогов прохождения и уроков</p></div>
          <button class="btn-primary" style="width:auto; padding:12px 22px" @click="openCreateCourse">+ Добавить тренинг</button>
        </div>
        <div class="search-row">
          <input class="search-input" v-model="search" placeholder="Поиск по названию тренинга...">
        </div>

        <div v-for="course in admin.adminCourses" :key="course.id">
          <h3 style="font-family:var(--font-display); font-size:20px; margin: 18px 0 10px;">{{ course.title }}</h3>

          <div v-for="m in course.modules" :key="m.id" class="mini-card" style="margin-bottom:16px;">
            <div style="display:flex; align-items:center; justify-content:space-between; cursor:pointer; user-select:none;" @click="toggleModule(m.id)">
              <h4 style="margin:0;">{{ m.title }}</h4>
              <div style="display:flex; align-items:center; gap:10px;">
                <span style="color:var(--text-dim); font-size:13px;">{{ m.lessons.length }} {{ m.lessons.length === 1 ? 'урок' : 'уроков' }}</span>
                <button class="dl-btn" style="border-color:var(--danger); color:var(--danger); padding:6px 10px;" @click.stop="removeModule(m)">Удалить модуль</button>
                <span style="transition: transform .2s;" :style="{ transform: expandedModuleId === m.id ? 'rotate(90deg)' : 'rotate(0deg)' }">›</span>
              </div>
            </div>

            <div v-show="expandedModuleId === m.id" style="margin-top:14px;">
              <div class="toggle-row">
                <div class="lbl">Требовать тест перед открытием следующего модуля<small>Пока ученик не наберёт порог — следующий модуль закрыт</small></div>
                <label class="switch"><input type="checkbox" v-model="m.require_test_to_unlock_next" @change="saveModule(m)"><span class="slider"></span></label>
              </div>
              <div class="toggle-row">
                <div class="lbl">Порог прохождения теста<small>Минимальный процент правильных ответов</small></div>
                <input style="width:70px; text-align:center; padding:8px; background:var(--navy-deep); border:1px solid var(--line); border-radius:8px; color:var(--text-hi)"
                       type="number" min="0" max="100" v-model.number="m.pass_threshold_percent" @change="saveModule(m)">
              </div>

              <div class="module-list" style="margin-top:14px;">
                <div class="module-item" v-for="l in m.lessons" :key="l.id">
                  <div class="num">{{ l.order }}</div>
                  <div class="info">
                    <h4>{{ l.title }}</h4>
                    <span>{{ l.video_file ? 'видео загружено' : (l.video_url ? 'ссылка на видео' : 'без видео') }} · {{ (l.materials || []).length }} файлов материалов</span>
                  </div>
                  <button class="dl-btn" @click="openEditLesson(m.id, l)">Изменить</button>
                  <button class="dl-btn" style="border-color:var(--danger); color:var(--danger);" @click="removeLesson(l.id)">Удалить</button>
                </div>
              </div>
              <button class="dl-btn" style="margin-top:10px;" @click="openAddLesson(m.id)">+ Добавить урок</button>
            </div>
          </div>

          <button class="dl-btn" @click="openCreateModule(course.id)">+ Добавить модуль</button>
          <p v-if="course.modules.length === 0" style="color:var(--text-dim); font-size:13px; margin-top:8px;">
            В этом тренинге пока нет модулей — добавьте первый.
          </p>
        </div>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: showLessonModal }">
      <div class="modal">
        <h3>{{ lessonForm.id ? 'Редактирование урока' : 'Новый урок' }}</h3>
        <div class="field"><label>Название</label><input v-model="lessonForm.title" placeholder="Введение в инструменты"></div>
        <div class="field"><label>Короткое описание урока</label><textarea v-model="lessonForm.description" rows="3" placeholder="О чём этот урок — необязательно"></textarea></div>
        <div class="field"><label>Ссылка на видео (необязательно, если загружаете файл ниже)</label><input v-model="lessonForm.video_url" placeholder="https://..."></div>

        <div class="field">
          <label>Видео-файл</label>
          <input type="file" accept="video/*" @change="onVideoPicked" :disabled="!lessonForm.title.trim()">
          <div class="hint" v-if="!lessonForm.title.trim()">Сначала введите название урока выше.</div>
          <div class="hint" v-else-if="lessonForm.duration_seconds">Длительность определена автоматически: {{ Math.round(lessonForm.duration_seconds / 60) }} мин.</div>
          <button v-if="lessonForm.video_file" type="button" class="dl-btn" style="margin-top:8px;" @click="openTrim">✂ Обрезать загруженное видео</button>
        </div>

        <!-- Файлы можно добавлять сразу, ещё до нажатия «Сохранить» — урок
             при необходимости создаётся автоматически при первом файле
             (см. addMaterial/ensureLessonId), без отдельного шага. -->
        <div class="materials-box">
          <h4>Файлы урока (любые: слайды, документы Word/Excel, аудио, PDF, презентации, архивы — сколько угодно)</h4>
          <div class="material-row" v-for="mat in lessonForm.materials" :key="mat.id">
            <div class="type-icon">{{ iconForKind(mat.kind) }}</div>
            <div class="name">{{ mat.name }}<span class="kind-label">{{ labelForKind(mat.kind) }}</span></div>
            <a class="dl" :href="mat.file" target="_blank">Открыть</a>
            <button class="dl-btn" style="padding:4px 8px; margin-left:8px;" @click="removeMaterial(mat.id)">Удалить</button>
          </div>
          <p v-if="lessonForm.materials.length === 0" style="color:var(--text-dim); font-size:12px; margin:4px 0 10px;">Файлов пока нет.</p>
          <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap; align-items:center;">
            <input v-model="materialForm.name" placeholder="Название файла" :disabled="!lessonForm.title.trim()" style="flex:1; min-width:160px; padding:9px 12px; background:var(--navy-deep); border:1px solid var(--line); border-radius:8px; color:var(--text-hi);">
            <input type="file" @change="onMaterialPicked" :disabled="!lessonForm.title.trim()">
            <button class="dl-btn" @click="addMaterial" :disabled="!lessonForm.title.trim()">+ Ещё файл</button>
          </div>
          <div class="hint" v-if="!lessonForm.title.trim()">Сначала введите название урока выше — файл прикрепится к нему автоматически.</div>
          <div class="hint" v-else-if="materialForm.file">Тип определён автоматически: {{ labelForKind(detectKind(materialForm.file)) }}</div>
        </div>

        <div class="modal-footer">
          <button class="btn-ghost" @click="showLessonModal = false">Закрыть</button>
          <button class="btn-primary" @click="saveLesson">Сохранить</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" :class="{ active: showCourseModal }">
      <div class="modal">
        <h3>Новый тренинг</h3>
        <div class="field"><label>Название</label><input v-model="courseForm.title" placeholder="Продвинутый макияж"></div>
        <div class="field"><label>Описание</label><input v-model="courseForm.description" placeholder="Краткое описание тренинга"></div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="showCourseModal = false">Отмена</button>
          <button class="btn-primary" @click="saveCourse">Создать</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" :class="{ active: showModuleModal }">
      <div class="modal">
        <h3>Новый модуль</h3>
        <div class="field"><label>Название модуля</label><input v-model="moduleForm.title" placeholder="Модуль 1. Введение"></div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="showModuleModal = false">Отмена</button>
          <button class="btn-primary" @click="saveModuleCreate">Добавить</button>
        </div>
      </div>
    </div>

    <VideoTrimModal :video="trimTarget" @trimmed="onTrimmed" @cancel="trimTarget = null" />
  </div>
</template>
