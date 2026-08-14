<script setup>
import { computed, onMounted } from 'vue'
import { useAuthStore } from '../../store/auth'
import { useUiStore } from '../../store/ui'
import { useRouter } from 'vue-router'
import { useCoursesStore } from '../../store/courses'
import NotificationBell from './NotificationBell.vue'

const props = defineProps({
  links: { type: Array, required: true }, // [{to, label, icon}]
})
const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const courses = useCoursesStore()

// Бейдж с числом показываем только там, где есть настоящие данные —
// сейчас это количество тренингов ученика в пункте "Тренинги" (/).
const badgeCounts = computed(() => ({
  '/': courses.courses.length,
}))

onMounted(() => {
  if (!auth.isAdmin && courses.courses.length === 0) courses.fetchCourses()
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <aside class="sidebar" :class="{ open: ui.sidebarOpen }">
    <button class="hamburger" @click="ui.toggleSidebar()">☰</button>
    <div class="logo">
      <span class="gem"><svg viewBox="0 0 16 22" fill="none"><path d="M8 0L16 6L8 22L0 6L8 0Z" stroke="currentColor" stroke-width="1.2"/></svg></span>COURSE
    </div>
    <div class="side-section-title">{{ auth.isAdmin ? 'Управление' : 'Обучение' }}</div>
    <router-link v-for="l in links" :key="l.to" :to="l.to" class="side-link"
      active-class="active" @click="ui.sidebarOpen = false">
      <span class="icon">{{ l.icon }}</span>
      <span class="side-link-label">{{ l.label }}</span>
      <span v-if="badgeCounts[l.to] !== undefined" class="side-link-badge">{{ badgeCounts[l.to] }}</span>
    </router-link>
    <div class="side-footer">
      <div class="avatar">{{ auth.isAdmin ? 'CA' : auth.initials }}</div>
      <div>
        <div class="name">{{ auth.isAdmin ? 'Course Admin' : (auth.user?.first_name + ' ' + auth.user?.last_name) }}</div>
        <div class="role">{{ auth.isAdmin ? 'Администратор' : 'Ученик' }}</div>
      </div>
      <NotificationBell />
      <button class="logout-btn" @click="logout">⏻</button>
    </div>
  </aside>
</template>
