<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../../components/common/Sidebar.vue'
import ProgressBar from '../../components/learner/ProgressBar.vue'
import { useAuthStore } from '../../store/auth'
import { useUiStore } from '../../store/ui'
import { useCoursesStore } from '../../store/courses'
import { learnerLinks as links } from '../../nav'

const auth = useAuthStore()
const ui = useUiStore()
const coursesStore = useCoursesStore()
const router = useRouter()

const loadingCourses = ref(true)
onMounted(async () => {
  if (coursesStore.courses.length === 0) await coursesStore.fetchCourses()
  loadingCourses.value = false
})

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

const fullName = computed(() => `${auth.user?.first_name || ''} ${auth.user?.last_name || ''}`.trim() || 'Без имени')
const cityCountry = computed(() => [auth.user?.country, auth.user?.city].filter(Boolean).join(', ') || '—')

// ===== Режим редактирования =====
const isEditing = ref(false)
const form = reactive({ first_name: '', last_name: '', country: '', city: '', phone: '', birth_date: '' })
const saving = ref(false)

function startEditing() {
  form.first_name = auth.user?.first_name || ''
  form.last_name = auth.user?.last_name || ''
  form.country = auth.user?.country || ''
  form.city = auth.user?.city || ''
  form.phone = auth.user?.phone || ''
  form.birth_date = auth.user?.birth_date || ''
  pendingAvatarFile.value = null
  avatarPreview.value = auth.user?.avatar || null
  isEditing.value = true
}

const avatarInput = ref(null)
const avatarPreview = ref(auth.user?.avatar || null)
const pendingAvatarFile = ref(null)

const initials = computed(() => {
  const name = fullName.value === 'Без имени' ? '' : fullName.value
  return name.split(' ').filter(Boolean).map((w) => w[0]).join('').toUpperCase() || '??'
})

function pickAvatar() {
  avatarInput.value?.click()
}

function onAvatarChosen(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ui.showToast('Выберите файл изображения', 'error')
    return
  }
  pendingAvatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
}

// Бесплатные сгенерированные аватарки через DiceBear (без ключей и регистрации).
// Каждое нажатие — новый случайный вариант в выбранном стиле.
const generatingAvatar = ref(false)

async function generateAvatar() {
  generatingAvatar.value = true
  try {
    const seed = Math.random().toString(36).slice(2)
    const url = `https://api.dicebear.com/9.x/personas/png?seed=${seed}&size=256`
    const res = await fetch(url)
    if (!res.ok) throw new Error('bad response')
    const blob = await res.blob()
    const file = new File([blob], `avatar-${seed}.png`, { type: 'image/png' })
    pendingAvatarFile.value = file
    avatarPreview.value = URL.createObjectURL(blob)
  } catch (e) {
    ui.showToast('Не удалось сгенерировать аватар — проверьте интернет', 'error')
  } finally {
    generatingAvatar.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const payload = new FormData()
    payload.append('first_name', form.first_name)
    payload.append('last_name', form.last_name)
    payload.append('country', form.country)
    payload.append('city', form.city)
    payload.append('phone', form.phone)
    if (form.birth_date) payload.append('birth_date', form.birth_date)
    if (pendingAvatarFile.value) payload.append('avatar', pendingAvatarFile.value)

    await auth.updateProfile(payload)
    isEditing.value = false
    ui.showToast('Профиль обновлён', 'success')
  } catch (e) {
    ui.showToast('Не удалось сохранить профиль', 'error')
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  isEditing.value = false
}

// ===== Смена пароля =====
const showPasswordModal = ref(false)
const pwForm = reactive({ newPass: '', confirmPass: '' })

function openChangePassword() {
  pwForm.newPass = ''
  pwForm.confirmPass = ''
  showPasswordModal.value = true
}

async function changePassword() {
  if (pwForm.newPass.length < 8) { ui.showToast('Пароль должен быть не менее 8 символов', 'error'); return }
  if (pwForm.newPass !== pwForm.confirmPass) { ui.showToast('Пароли не совпадают', 'error'); return }
  try {
    await auth.changePassword(pwForm.newPass, pwForm.confirmPass)
    ui.showToast('Пароль успешно изменён', 'success')
    showPasswordModal.value = false
  } catch (e) {
    const msg = e.response?.data ? Object.values(e.response.data).flat().join(' ') : 'Ошибка смены пароля'
    ui.showToast(msg, 'error')
  }
}

// Просмотр фото профиля крупно по клику на аватар.
const showAvatarLightbox = ref(false)

function courseStatus(c) {
  if (!c.enrolled) return { label: 'Недоступен', cls: 'locked' }
  if (c.progress_percent >= 100) return { label: 'Завершён', cls: 'done' }
  if (c.progress_percent > 0) return { label: `В процессе · ${c.progress_percent}%`, cls: 'progress' }
  return { label: 'Не начат', cls: 'todo' }
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header"><div><h1>Профиль</h1><p>Email закреплён администратором</p></div></div>

        <div class="profile-grid">
          <div class="mini-card profile-hero">
            <button v-if="!isEditing" type="button" class="profile-edit-btn" @click="startEditing" aria-label="Редактировать профиль">✎</button>

            <template v-if="!isEditing">
              <div class="profile-hero-top">
                <button
                  type="button" class="profile-avatar-lg" :class="{ clickable: avatarPreview }"
                  @click="avatarPreview && (showAvatarLightbox = true)"
                  :aria-label="avatarPreview ? 'Посмотреть фото' : undefined"
                >
                  <img v-if="avatarPreview" :src="avatarPreview" alt="">
                  <span v-else>{{ initials }}</span>
                </button>
                <div class="profile-hero-info">
                  <h2>{{ fullName }}</h2>
                  <div class="profile-info-row"><span>Дата регистрации:</span> {{ formatDate(auth.user?.date_joined) }}</div>
                  <div class="profile-info-row"><span>Страна, город:</span> {{ cityCountry }}</div>
                  <div class="profile-info-row"><span>Дата рождения:</span> {{ formatDate(auth.user?.birth_date) }}</div>
                  <div class="profile-info-row"><span>E-mail:</span> {{ auth.user?.email }}</div>
                  <div class="profile-info-row"><span>Телефон:</span> {{ auth.user?.phone || '—' }}</div>
                </div>
              </div>
              <button type="button" class="link-btn mt-8" @click="openChangePassword">Сменить пароль</button>
            </template>

            <template v-else>
              <div class="profile-avatar-row">
                <div class="profile-avatar-lg profile-avatar-lg-edit">
                  <img v-if="avatarPreview" :src="avatarPreview" alt="">
                  <span v-else>{{ initials }}</span>
                </div>
                <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="onAvatarChosen">
                <div class="profile-avatar-links">
                  <button type="button" class="avatar-action-btn" @click="pickAvatar">Загрузить фото</button>
                  <button type="button" class="avatar-action-btn" :disabled="generatingAvatar" @click="generateAvatar">
                    {{ generatingAvatar ? 'Генерируем...' : 'Сгенерировать аватар' }}
                  </button>
                </div>
              </div>

              <div class="field-row">
                <div class="field"><label>Имя</label><input v-model="form.first_name"></div>
                <div class="field"><label>Фамилия</label><input v-model="form.last_name"></div>
              </div>
              <div class="field-row">
                <div class="field"><label>Страна</label><input v-model="form.country"></div>
                <div class="field"><label>Город</label><input v-model="form.city"></div>
              </div>
              <div class="field-row">
                <div class="field"><label>Телефон</label><input v-model="form.phone" placeholder="+996 700 000 000"></div>
                <div class="field"><label>Дата рождения</label><input type="date" v-model="form.birth_date"></div>
              </div>
              <div class="field">
                <label>Email</label>
                <input :value="auth.user?.email" disabled>
              </div>

              <div class="profile-actions">
                <button class="btn-primary" :disabled="saving" @click="save">
                  {{ saving ? 'Сохранение...' : 'Сохранить изменения' }}
                </button>
                <button class="btn-ghost" @click="cancelEdit">Отмена</button>
              </div>
            </template>
          </div>

          <div class="mini-card">
            <h4>Мои курсы</h4>
            <div class="course-timeline" v-if="!loadingCourses">
              <div class="course-timeline-item" v-for="c in coursesStore.courses" :key="c.id">
                <span class="course-timeline-dot" :class="courseStatus(c).cls"></span>
                <div class="course-timeline-body">
                  <div class="course-timeline-top">
                    <div>
                      <strong>{{ c.title }}</strong>
                      <p>{{ c.description }}</p>
                      <span class="course-timeline-meta">{{ c.modules_count }} модулей</span>
                    </div>
                    <span class="badge-pill" :class="courseStatus(c).cls">{{ courseStatus(c).label }}</span>
                  </div>
                  <ProgressBar v-if="c.enrolled" :percent="c.progress_percent" :label="`${c.progress_percent}%`" />
                  <button
                    v-if="c.enrolled" type="button" class="link-btn mt-8"
                    @click="router.push(`/courses/${c.slug}`)"
                  >Открыть курс →</button>
                </div>
              </div>
              <p v-if="coursesStore.courses.length === 0" style="color:var(--text-dim); font-size:13px;">Курсы пока не назначены.</p>
            </div>
          </div>

          <div class="mini-card">
            <h4>Настройки</h4>
            <div class="settings-row">
              <div class="lbl">Оформление<small>Тёмная или светлая тема интерфейса</small></div>
              <div class="settings-switch">
                <button type="button" :class="{ active: ui.theme === 'dark' }" @click="ui.setTheme('dark')">Тёмная</button>
                <button type="button" :class="{ active: ui.theme === 'light' }" @click="ui.setTheme('light')">Светлая</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: showPasswordModal }">
      <div class="modal">
        <h3>Смена пароля</h3>
        <p class="mod-sub">Введите новый пароль. Он должен содержать минимум 8 символов.</p>
        <div class="field"><label>Новый пароль</label><input type="password" v-model="pwForm.newPass" placeholder="••••••••"></div>
        <div class="field"><label>Подтверждение</label><input type="password" v-model="pwForm.confirmPass" placeholder="••••••••"></div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="showPasswordModal = false">Отмена</button>
          <button class="btn-primary" @click="changePassword">Сохранить</button>
        </div>
      </div>
    </div>

    <div class="modal-overlay avatar-lightbox-overlay" :class="{ active: showAvatarLightbox }" @click="showAvatarLightbox = false">
      <button type="button" class="avatar-lightbox-close" @click="showAvatarLightbox = false" aria-label="Закрыть">×</button>
      <img v-if="avatarPreview" :src="avatarPreview" class="avatar-lightbox-img" alt="Фото профиля" @click.stop>
    </div>
  </div>
</template>
