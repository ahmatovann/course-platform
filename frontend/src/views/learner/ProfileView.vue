<script setup>
import { computed, reactive, ref } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useAuthStore } from '../../store/auth'
import { useUiStore } from '../../store/ui'
import { learnerLinks as links } from '../../nav'

const auth = useAuthStore()
const ui = useUiStore()

const form = reactive({
  first_name: auth.user?.first_name || '',
  last_name: auth.user?.last_name || '',
  country: auth.user?.country || '',
  city: auth.user?.city || '',
})
const saving = ref(false)
const dirty = ref(false)

function markDirty() {
  dirty.value = true
}

const avatarInput = ref(null)
const avatarPreview = ref(auth.user?.avatar || null)
const pendingAvatarFile = ref(null)

const initials = computed(() => {
  const name = `${form.first_name} ${form.last_name}`.trim()
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
  dirty.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = new FormData()
    payload.append('first_name', form.first_name)
    payload.append('last_name', form.last_name)
    payload.append('country', form.country)
    payload.append('city', form.city)
    if (pendingAvatarFile.value) payload.append('avatar', pendingAvatarFile.value)

    await auth.updateProfile(payload)
    pendingAvatarFile.value = null
    dirty.value = false
    ui.showToast('Профиль обновлён', 'success')
  } catch (e) {
    ui.showToast('Не удалось сохранить профиль', 'error')
  } finally {
    saving.value = false
  }
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
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header"><div><h1>Мой профиль</h1><p>Email закреплён администратором</p></div></div>

        <div class="profile-layout">
          <div class="mini-card profile-card">
            <h4>Данные аккаунта</h4>

            <div class="profile-avatar-row">
              <div class="profile-avatar" @click="pickAvatar">
                <img v-if="avatarPreview" :src="avatarPreview" alt="">
                <span v-else>{{ initials }}</span>
                <div class="profile-avatar-edit">✎</div>
              </div>
              <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="onAvatarChosen">
              <div class="profile-avatar-hint">
                <strong>{{ form.first_name || form.last_name ? `${form.first_name} ${form.last_name}`.trim() : 'Без имени' }}</strong>
                <button type="button" class="link-btn" @click="pickAvatar">Изменить фото</button>
              </div>
            </div>

            <div class="field"><label>Имя</label><input v-model="form.first_name" @input="markDirty"></div>
            <div class="field"><label>Фамилия</label><input v-model="form.last_name" @input="markDirty"></div>
            <div class="field">
              <label>Email</label>
              <div style="display:flex; align-items:center; gap:8px;">
                <input :value="auth.user?.email" disabled style="flex:1;">
                <span style="color:var(--ok); font-size:14px;">✓</span>
              </div>
            </div>
            <div class="field"><label>Страна</label><input v-model="form.country" @input="markDirty"></div>
            <div class="field"><label>Город</label><input v-model="form.city" @input="markDirty"></div>

            <div class="profile-actions">
              <button class="btn-primary" :disabled="!dirty || saving" @click="save">
                {{ saving ? 'Сохранение...' : 'Сохранить изменения' }}
              </button>
              <button class="btn-ghost" @click="openChangePassword">Сменить пароль</button>
            </div>
          </div>

          <div class="mini-card profile-card">
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
  </div>
</template>
