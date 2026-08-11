<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../store/auth'
import { useUiStore } from '../../store/ui'
import ThemeToggle from '../../components/common/ThemeToggle.vue'

const email = ref('anna@mail.com')
const password = ref('')
const loading = ref(false)
const leaving = ref(false)
const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()

async function handleLogin() {
  if (!email.value || !password.value) {
    ui.showToast('Заполните все поля', 'error')
    return
  }
  loading.value = true
  try {
    const data = await auth.login(email.value, password.value)
    ui.showToast('Вход выполнен. Добро пожаловать!', 'success')
    leaving.value = true
    setTimeout(() => {
      router.push(data.user.role === 'admin' ? '/admin/students' : '/')
    }, 300)
  } catch (e) {
    ui.showToast(e.response?.data?.detail || 'Неверный email или пароль', 'error')
    loading.value = false
  }
}
</script>

<template>
  <div class="login-screen">
    <ThemeToggle />
    <div class="login-card" :class="{ leaving }">
      <div class="logo">
        <span class="gem"><svg viewBox="0 0 16 22" fill="none"><path d="M8 0L16 6L8 22L0 6L8 0Z" stroke="#C9A66B" stroke-width="1.2"/><path d="M2 6H14M8 0V22M2 6L8 22L14 6" stroke="#C9A66B" stroke-width="0.7" opacity=".6"/></svg></span>COURSE
      </div>
      <div class="login-sub">Личный кабинет школы</div>
      <div class="field">
        <label>Email</label>
        <input type="email" v-model="email" placeholder="you@mail.com">
      </div>
      <div class="field">
        <label>Пароль</label>
        <input type="password" v-model="password" placeholder="••••••••">
        <div class="hint">
          Пароль выдаёт администратор школы ·
          <a href="#" @click.prevent="router.push('/forgot-password')" style="color:var(--gold); text-decoration:underline;">забыли пароль?</a>
        </div>
      </div>
      <button class="btn-primary" :disabled="loading" @click="handleLogin">
        <span v-if="loading" class="spinner"></span>{{ loading ? 'Входим…' : 'Войти' }}
      </button>
      <div class="login-note">
        Самостоятельная регистрация закрыта.<br>
        Доступ создаёт администратор — логин и временный пароль<br>
        приходят на вашу почту.
        <br><br>
        Демо: anna@mail.com / anna12345 (ученик)<br>
        admin@course.local / admin12345 (админ)
      </div>
    </div>
  </div>
</template>
