<script setup>
import { onMounted, ref } from 'vue'
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

onMounted(() => {
  if (!auth.isAdmin && courses.courses.length === 0) courses.fetchCourses()
})

function logout() {
  auth.logout()
  router.push('/login')
}

// Клик по аватарке в подвале меню — посмотреть фото крупнее.
const showAvatarLightbox = ref(false)
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
    </router-link>
    <div class="side-footer">
      <button
        type="button" class="avatar" :class="{ clickable: auth.user?.avatar }"
        @click="auth.user?.avatar && (showAvatarLightbox = true)"
        :aria-label="auth.user?.avatar ? 'Посмотреть фото' : undefined"
      >
        <img v-if="auth.user?.avatar" :src="auth.user.avatar" alt="">
        <template v-else>{{ auth.isAdmin ? 'CA' : auth.initials }}</template>
      </button>
      <div>
        <div class="name">{{ auth.isAdmin ? 'Course Admin' : (auth.user?.first_name + ' ' + auth.user?.last_name) }}</div>
        <div class="role">{{ auth.isAdmin ? 'Администратор' : 'Ученик' }}</div>
      </div>
      <NotificationBell />
      <button class="logout-btn" @click="logout">⏻</button>
    </div>
  </aside>

  <div class="modal-overlay avatar-lightbox-overlay" :class="{ active: showAvatarLightbox }" @click="showAvatarLightbox = false">
    <button type="button" class="avatar-lightbox-close" @click="showAvatarLightbox = false" aria-label="Закрыть">×</button>
    <img v-if="auth.user?.avatar" :src="auth.user.avatar" class="avatar-lightbox-img" alt="Фото профиля" @click.stop>
  </div>
</template>
