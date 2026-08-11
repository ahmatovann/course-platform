<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useAdminStore } from '../../store/admin'
import { useCoursesStore } from '../../store/courses'
import { useUiStore } from '../../store/ui'

import { adminLinks as links } from '../../nav'

const admin = useAdminStore()
const courses = useCoursesStore()
const ui = useUiStore()
const showModal = ref(false)
const result = ref(null)
const form = reactive({ name: '', email: '', phone: '', course_id: null })
const search = ref('')
const status = ref('')
let debounceTimer = null

onMounted(async () => {
  await admin.fetchStudents()
  await courses.fetchCourses()
})

watch([search, status], () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    admin.fetchStudents({ search: search.value || undefined, status: status.value || undefined })
  }, 300)
})
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

async function exportStudents() {
  try {
    await admin.exportStudents()
  } catch (e) {
    ui.showToast('Не удалось экспортировать', 'error')
  }
}

function openModal() {
  showModal.value = true
  result.value = null
  form.name = ''; form.email = ''; form.phone = ''
  form.course_id = courses.courses[0]?.id || null
}

async function createStudent() {
  if (!form.name || !form.email) { ui.showToast('Заполните имя и email', 'error'); return }
  try {
    const data = await admin.createStudent(form)
    result.value = data
    ui.showToast(`Ученик ${form.name} создан! Письмо отправлено.`, 'success')
  } catch (e) {
    const msg = e.response?.data ? Object.values(e.response.data).flat().join(' ') : 'Ошибка создания'
    ui.showToast(msg, 'error')
  }
}

async function toggle(s) {
  await admin.toggleStudent(s.id)
  ui.showToast(s.is_active_student ? 'Ученик деактивирован' : 'Ученик активирован', s.is_active_student ? 'error' : 'success')
}

const coursesModalStudentId = ref(null)
const coursesModalStudent = computed(() => admin.students.find((s) => s.id === coursesModalStudentId.value) || null)

function openCoursesModal(s) {
  coursesModalStudentId.value = s.id
}

function isEnrolled(courseId) {
  return !!coursesModalStudent.value?.course_ids?.includes(courseId)
}

// Без ограничений: можно свободно добавлять ученику доступ сразу к нескольким
// тренингам, не теряя доступ к уже имеющимся — просто отмечаем/снимаем галочку.
async function toggleCourse(c) {
  const s = coursesModalStudent.value
  if (!s) return
  try {
    if (isEnrolled(c.id)) {
      await admin.unenrollStudent(s.id, c.id)
      ui.showToast(`Доступ к «${c.title}» закрыт`, 'success')
    } else {
      await admin.enrollStudent(s.id, c.id)
      ui.showToast(`Открыт доступ к «${c.title}»`, 'success')
    }
  } catch (e) {
    ui.showToast('Не удалось изменить доступ', 'error')
  }
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>Ученики</h1><p>Регистрация возможна только через администратора</p></div>
          <div style="display:flex; gap:10px;">
            <button class="dl-btn" @click="exportStudents">⬇ Экспорт в Excel</button>
            <button class="btn-primary" style="width:auto; padding:12px 22px" @click="openModal">+ Добавить ученика</button>
          </div>
        </div>
        <div class="search-row">
          <input class="search-input" v-model="search" placeholder="Поиск по имени или email...">
          <select v-model="status">
            <option value="">Все статусы</option>
            <option value="active">Активные</option>
            <option value="inactive">Не активные</option>
          </select>
        </div>
        <table>
          <thead><tr><th>Ученик</th><th>Email</th><th>Телефон</th><th>Статус</th><th>Курсы</th><th></th></tr></thead>
          <tbody>
            <tr v-for="s in admin.students" :key="s.id">
              <td>{{ s.first_name }} {{ s.last_name }}</td>
              <td>{{ s.email }}</td>
              <td>{{ s.phone || '—' }}</td>
              <td>
                <button
                  type="button" class="status-dot status-toggle" :class="s.is_active_student ? 'active' : 'inactive'"
                  @click="toggle(s)" :title="s.is_active_student ? 'Нажмите, чтобы деактивировать' : 'Нажмите, чтобы активировать'"
                >{{ s.is_active_student ? 'Активен' : 'Не активен' }}</button>
              </td>
              <td>{{ s.course_titles.join(', ') || '—' }}</td>
              <td class="row-actions">
                <button @click="openCoursesModal(s)" title="Изменить курсы">Курсы</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal">
        <h3>Новый ученик</h3>
        <p class="mod-sub">Пароль сгенерируется автоматически и отправится на email.</p>
        <div class="field"><label>Имя и фамилия</label><input v-model="form.name" placeholder="Мария Кузнецова"></div>
        <div class="field"><label>Email</label><input v-model="form.email" type="email" placeholder="maria@mail.com"></div>
        <div class="field"><label>Телефон</label><input v-model="form.phone" placeholder="+996 700 000 000"></div>
        <div class="field">
          <label>Курс</label>
          <select v-model="form.course_id">
            <option v-for="c in courses.courses" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>
        </div>
        <div class="gen-result" :class="{ show: result }" v-if="result">
          Ученик создан. Письмо отправлено на <b>{{ result.email }}</b><br>
          Логин: <b>{{ result.login }}</b><br>
          Временный пароль: <b>{{ result.password }}</b>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="showModal = false">Закрыть</button>
          <button class="btn-primary" @click="createStudent">Создать и отправить</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" :class="{ active: coursesModalStudent }">
      <div class="modal" v-if="coursesModalStudent">
        <h3>Курсы ученика</h3>
        <p class="mod-sub">
          {{ coursesModalStudent.first_name }} {{ coursesModalStudent.last_name }} — отметьте тренинги,
          доступ к которым должен быть открыт. Можно выбрать сразу несколько без ограничений,
          уже имеющийся доступ при этом не отзывается.
        </p>
        <div style="display:flex; flex-direction:column; gap:10px; max-height:340px; overflow-y:auto; margin:14px 0;">
          <label v-for="c in courses.courses" :key="c.id"
                 style="display:flex; align-items:center; gap:10px; cursor:pointer; padding:8px 10px; border-radius:8px; background:var(--navy-deep);">
            <input type="checkbox" :checked="isEnrolled(c.id)" @change="toggleCourse(c)">
            <span>{{ c.title }}</span>
          </label>
          <p v-if="courses.courses.length === 0" style="color:var(--text-dim); font-size:12.5px;">Тренингов пока нет.</p>
        </div>
        <div class="modal-footer">
          <button class="btn-primary" @click="coursesModalStudentId = null">Готово</button>
        </div>
      </div>
    </div>
  </div>
</template>
