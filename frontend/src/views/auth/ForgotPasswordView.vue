<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../store/auth'
import { useUiStore } from '../../store/ui'
import ThemeToggle from '../../components/common/ThemeToggle.vue'

const email = ref('')
const loading = ref(false)
const sent = ref(false)
const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()

async function submit() {
  if (!email.value) {
    ui.showToast('Введите email', 'error')
    return
  }
  loading.value = true
  try {
    await auth.requestPasswordReset(email.value)
    sent.value = true
  } catch (e) {
    ui.showToast('Не получилось отправить запрос. Попробуйте ещё раз', 'error')
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
      <div class="login-sub">Восстановление пароля</div>

      <template v-if="!sent">
        <div class="field">
          <label>Email</label>
          <input type="email" v-model="email" placeholder="you@mail.com" @keyup.enter="submit">
          <div class="hint">Пришлём ссылку для создания нового пароля</div>
        </div>
        <button class="btn-primary" :disabled="loading" @click="submit">
          <span v-if="loading" class="spinner"></span>{{ loading ? 'Отправляем…' : 'Отправить ссылку' }}
        </button>
      </template>

      <template v-else>
        <div class="gen-result show">
          Если такой email зарегистрирован — на него отправлено письмо со ссылкой для сброса пароля.
          Проверьте почту (и папку «Спам»).
        </div>
      </template>

      <button class="btn-ghost" @click="router.push('/login')">← Назад ко входу</button>
    </div>
  </div>
</template>
