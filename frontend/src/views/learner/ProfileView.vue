<script setup>
import { reactive, ref } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useAuthStore } from '../../store/auth'
import { useUiStore } from '../../store/ui'
import { learnerLinks as links } from '../../nav'

const auth = useAuthStore()
const ui = useUiStore()
const firstName = ref(auth.user?.first_name || '')
const lastName = ref(auth.user?.last_name || '')
const country = ref(auth.user?.country || '')
const city = ref(auth.user?.city || '')

async function save() {
  await auth.updateProfile({ first_name: firstName.value, last_name: lastName.value, country: country.value, city: city.value })
  ui.showToast('Профиль обновлён', 'success')
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
        <div class="mini-card" style="max-width:460px;">
          <h4>Данные аккаунта</h4>
          <div class="field"><label>Имя</label><input v-model="firstName" @change="save"></div>
          <div class="field"><label>Фамилия</label><input v-model="lastName" @change="save"></div>
          <div class="field">
            <label>Email</label>
            <div style="display:flex; align-items:center; gap:8px;">
              <input :value="auth.user?.email" disabled style="flex:1;">
              <span style="color:var(--ok); font-size:14px;">✓</span>
            </div>
          </div>
          <div class="field"><label>Страна</label><input v-model="country" @change="save"></div>
          <div class="field"><label>Город</label><input v-model="city" @change="save"></div>
          <button class="btn-ghost" @click="openChangePassword">Сменить пароль</button>
        </div>

        <div class="mini-card" style="max-width:460px; margin-top:18px;">
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
