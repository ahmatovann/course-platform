<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../../components/common/Sidebar.vue'
import { useAdminStore } from '../../store/admin'
import { useCoursesStore } from '../../store/courses'
import { useChatsStore } from '../../store/chats'
import { useUiStore } from '../../store/ui'

import { adminLinks as links } from '../../nav'

const admin = useAdminStore()
const courses = useCoursesStore()
const chats = useChatsStore()
const ui = useUiStore()
const router = useRouter()
const showModal = ref(false)
const result = ref(null)
const form = reactive({ name: '', email: '', phone: '', course_id: null, access_amount: 3, access_unit: 'month' })
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

async function exportStudentsPdf() {
  try {
    await admin.exportStudentsPdf()
  } catch (e) {
    ui.showToast('Не удалось экспортировать PDF', 'error')
  }
}

function openModal() {
  showModal.value = true
  result.value = null
  form.name = ''; form.email = ''; form.phone = ''
  form.course_id = courses.courses[0]?.id || null
  form.access_amount = 3
  form.access_unit = 'month'
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

async function removeStudent(student) {
  if (!confirm(`Удалить ученика «${student.first_name} ${student.last_name}»? Это удалит его доступ и прогресс.`)) return
  try {
    await admin.deleteStudent(student.id)
    ui.showToast('Ученик удалён', 'success')
  } catch (e) {
    ui.showToast('Не удалось удалить ученика', 'error')
  }
}

// Срок доступа ученика — показываем дату и подсвечиваем, если доступ уже
// истёк или истекает в ближайшие 14 дней.
function formatExpiry(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function isExpired(iso) {
  if (!iso) return false
  return new Date(iso) < new Date()
}

function isExpiringSoon(iso) {
  if (!iso) return false
  const days = (new Date(iso) - new Date()) / 86400000
  return days > 0 && days <= 14
}

const unitLabels = { day: 'дн.', week: 'нед.', month: 'мес.' }

// Продление доступа — администратор сам выбирает количество и единицу
// (день/неделя/месяц), а не только фиксированные месяцы.
const extendModalStudentId = ref(null)
const extendAmount = ref(1)
const extendUnit = ref('month')
const extendModalStudent = computed(() => admin.students.find((s) => s.id === extendModalStudentId.value) || null)

function openExtendModal(s) {
  extendModalStudentId.value = s.id
  extendAmount.value = 1
  extendUnit.value = 'month'
}

async function confirmExtend() {
  const s = extendModalStudent.value
  if (!s) return
  try {
    await admin.extendStudentAccess(s.id, extendAmount.value, extendUnit.value)
    ui.showToast(`Доступ продлён на ${extendAmount.value} ${unitLabels[extendUnit.value]}`, 'success')
    extendModalStudentId.value = null
  } catch (e) {
    ui.showToast('Не удалось продлить доступ', 'error')
  }
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

// ===== Карточка ученика (прогресс + материалы + чат) =====
const cardStudentId = ref(null)
const cardStudent = computed(() => admin.students.find((s) => s.id === cardStudentId.value) || null)
const cardProgress = ref(null)
const cardProgressLoading = ref(false)
const openingChat = ref(false)

async function openCard(s) {
  cardStudentId.value = s.id
  cardProgress.value = null
  cardProgressLoading.value = true
  try {
    const [progress] = await Promise.all([
      admin.fetchStudentProgress(s.id),
      admin.media.length === 0 ? admin.fetchMedia() : Promise.resolve(),
    ])
    cardProgress.value = progress
  } finally {
    cardProgressLoading.value = false
  }
}

function closeCard() {
  cardStudentId.value = null
}

// Материалы, доступные этому ученику — все файлы уроков курсов, на
// которые он записан (то же самое, что видно в библиотеке «Материалы»,
// просто отфильтровано под конкретного ученика).
const cardMaterials = computed(() => {
  if (!cardStudent.value) return []
  const courseIds = new Set(cardStudent.value.course_ids || [])
  return admin.media.filter((item) => courseIds.has(item.course_id))
})

async function goToChat(s) {
  openingChat.value = true
  try {
    const thread = await chats.getDirectThread(s.id)
    router.push({ path: '/admin/chats', query: { thread: thread.id } })
  } catch (e) {
    ui.showToast('Не удалось открыть чат', 'error')
  } finally {
    openingChat.value = false
  }
}

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return '—'
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`
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
            <button class="dl-btn" @click="exportStudents">⬇ Excel</button>
            <button class="dl-btn" @click="exportStudentsPdf">⬇ PDF</button>
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
          <thead><tr><th>Ученик</th><th>Email</th><th>Телефон</th><th>Статус</th><th>Доступ до</th><th>Курсы</th><th></th></tr></thead>
          <tbody>
            <tr v-for="s in admin.students" :key="s.id" style="cursor:pointer;" @click="openCard(s)">
              <td style="color:var(--gold); text-decoration:underline;">{{ s.first_name }} {{ s.last_name }}</td>
              <td>{{ s.email }}</td>
              <td>{{ s.phone || '—' }}</td>
              <td>
                <button
                  type="button" class="status-dot status-toggle" :class="s.is_active_student ? 'active' : 'inactive'"
                  @click.stop="toggle(s)" :title="s.is_active_student ? 'Нажмите, чтобы деактивировать' : 'Нажмите, чтобы активировать'"
                >{{ s.is_active_student ? 'Активен' : 'Не активен' }}</button>
              </td>
              <td>
                <span :style="{ color: isExpired(s.access_expires_at) ? 'var(--danger)' : (isExpiringSoon(s.access_expires_at) ? 'var(--gold)' : 'var(--text-mid)') }">
                  {{ formatExpiry(s.access_expires_at) }}
                </span>
              </td>
              <td>{{ s.course_titles.join(', ') || '—' }}</td>
              <td class="row-actions">
                <button @click.stop="openCoursesModal(s)" title="Изменить курсы">Курсы</button>
                <button @click.stop="openExtendModal(s)" title="Продлить доступ на выбранный срок">Продлить</button>
                <button @click.stop="removeStudent(s)" title="Удалить ученика" style="color:var(--danger);">Удалить</button>
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
        <div class="field">
          <label>Срок доступа</label>
          <div style="display:flex; gap:8px;">
            <input type="number" min="1" v-model.number="form.access_amount" style="width:90px;">
            <select v-model="form.access_unit" style="flex:1;">
              <option value="day">Дней</option>
              <option value="week">Недель</option>
              <option value="month">Месяцев</option>
            </select>
          </div>
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

    <div class="modal-overlay" :class="{ active: cardStudent }" @click="closeCard">
      <div class="modal" style="max-width:640px" v-if="cardStudent" @click.stop>
        <h3>{{ cardStudent.first_name }} {{ cardStudent.last_name }}</h3>
        <p class="mod-sub">{{ cardStudent.email }} · {{ cardStudent.phone || 'без телефона' }}</p>
        <div style="display:flex; gap:10px; align-items:center; margin:12px 0 20px;">
          <button
            type="button" class="status-dot status-toggle" :class="cardStudent.is_active_student ? 'active' : 'inactive'"
            @click="toggle(cardStudent)"
          >{{ cardStudent.is_active_student ? 'Активен' : 'Не активен' }}</button>
          <button type="button" class="btn-primary" style="width:auto; padding:9px 16px;" :disabled="openingChat" @click="goToChat(cardStudent)">
            💬 {{ openingChat ? 'Открываем...' : 'Написать в чат' }}
          </button>
        </div>

        <h4>Прогресс</h4>
        <div v-if="cardProgressLoading" style="color:var(--text-dim); font-size:13px; margin-bottom:16px;">Загрузка...</div>
        <template v-else-if="cardProgress">
          <p v-if="cardProgress.courses.length === 0" style="color:var(--text-dim); font-size:13px;">Не записан ни на один тренинг.</p>
          <div v-for="c in cardProgress.courses" :key="c.course_id" class="chart-bar-row" style="margin-bottom:10px;">
            <span class="chart-bar-label">{{ c.course_title }} — {{ c.modules_completed }}/{{ c.modules_total }} модулей ({{ c.completion_percent }}%)</span>
            <div class="chart-bar-track"><div class="chart-bar-fill" :style="{ width: c.completion_percent + '%' }"></div></div>
          </div>
        </template>

        <h4 style="margin-top:20px;">Материалы</h4>
        <p style="color:var(--text-dim); font-size:12.5px; margin:-4px 0 10px;">Файлы курсов, на которые записан ученик</p>
        <div style="display:flex; flex-direction:column; gap:6px; max-height:220px; overflow-y:auto;">
          <a
            v-for="item in cardMaterials" :key="item.id" :href="item.url" target="_blank" rel="noopener"
            style="display:flex; justify-content:space-between; gap:10px; padding:8px 10px; border-radius:8px; background:var(--navy-deep); color:var(--text-hi); text-decoration:none; font-size:13px;"
          >
            <span>{{ item.name }}</span>
            <span style="color:var(--text-dim); flex-shrink:0;">{{ item.kind_label }} · {{ formatSize(item.size_bytes) }}</span>
          </a>
          <p v-if="cardMaterials.length === 0" style="color:var(--text-dim); font-size:12.5px;">Материалов пока нет.</p>
        </div>

        <div class="modal-footer">
          <button class="btn-ghost" @click="closeCard">Закрыть</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay" :class="{ active: extendModalStudent }">
      <div class="modal" v-if="extendModalStudent">
        <h3>Продлить доступ</h3>
        <p class="mod-sub">
          {{ extendModalStudent.first_name }} {{ extendModalStudent.last_name }} — выберите, на сколько
          продлить доступ (от сегодняшнего дня). Текущий срок: {{ formatExpiry(extendModalStudent.access_expires_at) }}.
        </p>
        <div class="field">
          <label>Период продления</label>
          <div style="display:flex; gap:8px;">
            <input type="number" min="1" v-model.number="extendAmount" style="width:90px;">
            <select v-model="extendUnit" style="flex:1;">
              <option value="day">Дней</option>
              <option value="week">Недель</option>
              <option value="month">Месяцев</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="extendModalStudentId = null">Отмена</button>
          <button class="btn-primary" @click="confirmExtend">Продлить</button>
        </div>
      </div>
    </div>
  </div>
</template>
