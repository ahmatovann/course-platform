<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../store/auth'
import { useUiStore } from '../../store/ui'
import ThemeToggle from '../../components/common/ThemeToggle.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const uid = route.query.uid || ''
const token = route.query.token || ''
const linkValid = !!uid && !!token

const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const done = ref(false)

async function submit() {
  if (newPassword.value.length < 8) {
    ui.showToast('Пароль должен быть не короче 8 символов', 'error')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    ui.showToast('Пароли не совпадают', 'error')
    return
  }
  loading.value = true
  try {
    await auth.confirmPasswordReset({ uid, token, newPassword: newPassword.value, confirmPassword: confirmPassword.value })
    done.value = true
    ui.showToast('Пароль изменён', 'success')
  } catch (e) {
    const data = e.response?.data
    const msg = data ? Object.values(data).flat().join(' ') : 'Ссылка недействительна или устарела'
    ui.showToast(msg, 'error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-screen">
    <ThemeToggle />
    <div class="login-card">
      <div class="logo">
        <span class="gem"><svg viewBox="0 0 16 22" fill="none"><path d="M8 0L16 6L8 22L0 6L8 0Z" stroke="#C9A66B" stroke-width="1.2"/></svg></span>COURSE
      </div>
      <div class="login-sub">Новый пароль</div>

      <template v-if="!linkValid">
        <div class="gen-result show">Ссылка неполная или повреждена. Запросите восстановление пароля ещё раз.</div>
        <button class="btn-ghost" @click="router.push('/forgot-password')">Запросить ссылку заново</button>
      </template>

      <template v-else-if="!done">
        <div class="field">
          <label>Новый пароль</label>
          <input type="password" v-model="newPassword" placeholder="Минимум 8 символов">
        </div>
        <div class="field">
          <label>Подтверждение пароля</label>
          <input type="password" v-model="confirmPassword" placeholder="Повторите пароль" @keyup.enter="submit">
        </div>
        <button class="btn-primary" :disabled="loading" @click="submit">
          <span v-if="loading" class="spinner"></span>{{ loading ? 'Сохраняем…' : 'Сохранить пароль' }}
        </button>
      </template>

      <template v-else>
        <div class="gen-result show">Пароль успешно изменён. Теперь можно войти.</div>
        <button class="btn-primary" @click="router.push('/login')">Войти</button>
      </template>
    </div>
  </div>
</template>
