<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from '../../components/common/Sidebar.vue'
import ProgressOrbit from '../../components/common/ProgressOrbit.vue'
import { useCoursesStore } from '../../store/courses'
import { useUiStore } from '../../store/ui'
import { useAuthStore } from '../../store/auth'

import { learnerLinks as links } from '../../nav'

const route = useRoute()
const router = useRouter()
const store = useCoursesStore()
const ui = useUiStore()
const auth = useAuthStore()
const course = ref(null)

async function load() {
  course.value = await store.fetchCourse(route.params.slug)
}
onMounted(load)
watch(() => route.params.slug, load)

function openModule(m) {
  if (!m.unlocked) {
    ui.showToast('Этот модуль пока закрыт', 'error')
    return
  }
  router.push({ name: 'module', params: { id: m.id } })
}

const orbitModules = computed(() => (course.value?.modules || []).map((m) => ({
  title: m.title, completed: m.status.completed, unlocked: m.unlocked, raw: m,
})))
const studentName = computed(() => `${auth.user?.first_name || ''} ${auth.user?.last_name || ''}`.trim() || 'Ученик')
const studentInitials = computed(() => studentName.value.split(' ').filter(Boolean).map((w) => w[0]).join('').toUpperCase() || '??')

async function downloadCertificate() {
  try {
    await store.downloadCertificate(course.value.slug)
    ui.showToast('Сертификат скачан', 'success')
  } catch (e) {
    ui.showToast('Не удалось скачать сертификат', 'error')
  }
}
</script>

<template>
  <div class="app active" v-if="course">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="course-hero">
          <div class="course-hero-side">
            <div class="course-hero-avatar">
              <img v-if="auth.user?.avatar" :src="auth.user.avatar" alt="">
              <span v-else>{{ studentInitials }}</span>
            </div>
            <div>
              <div class="course-hero-eyebrow">Добрый день,</div>
              <strong class="course-hero-title">{{ studentName }}</strong>
            </div>
          </div>

          <div class="course-hero-arc">
            <ProgressOrbit :modules="orbitModules" :size="190" @select="(seg) => openModule(seg.raw)" />
          </div>

          <div class="course-hero-side right">
            <div>
              <div class="course-hero-eyebrow">Тренинг</div>
              <strong class="course-hero-title">{{ course.title }}</strong>
            </div>
            <div class="course-hero-actions">
              <button v-if="course.certificate_available" class="dl-btn" @click="downloadCertificate">Сертификат</button>
              <button class="dl-btn" @click="router.push('/')">← Назад</button>
            </div>
          </div>
        </div>

        <div class="module-list">
          <div v-for="m in course.modules" :key="m.id"
               class="module-item" :class="m.unlocked ? 'unlocked' : 'locked'"
               @click="openModule(m)">
            <div class="num">{{ m.order }}</div>
            <div class="info">
              <h4>{{ m.title }}</h4>
              <span v-if="!m.unlocked">Доступно после предыдущего модуля</span>
              <span v-else-if="m.status.completed">{{ m.status.lessons_total }} уроков · пройден{{ m.status.test_best_score !== null ? ' на ' + m.status.test_best_score + '%' : '' }}</span>
              <span v-else>{{ m.status.lessons_watched }}/{{ m.status.lessons_total }} уроков{{ m.has_test ? ' · тест не сдан' : '' }}</span>
            </div>
            <div class="status-icon" :style="{ color: m.status.completed ? 'var(--ok)' : (m.unlocked ? 'var(--gold)' : '') }">
              {{ m.status.completed ? '✓' : (m.unlocked ? '●' : '▪') }}
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.course-hero {
  position: relative;
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  background: var(--navy-soft); border: 1px solid var(--line); border-radius: 20px;
  padding: 22px 28px; margin-bottom: 24px;
  transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
}
.course-hero:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 32px rgba(0, 0, 0, .18);
  border-color: var(--gold-soft, var(--gold));
}
.course-hero-side { display: flex; align-items: center; gap: 14px; flex: 1; min-width: 0; }
.course-hero-side.right { justify-content: flex-end; text-align: right; }
.course-hero-avatar {
  width: 52px; height: 52px; border-radius: 50%; flex-shrink: 0; overflow: hidden;
  background: var(--navy-deep); display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; color: var(--gold);
  transition: transform .25s ease;
}
.course-hero:hover .course-hero-avatar { transform: scale(1.06); }
.course-hero-avatar img { width: 100%; height: 100%; object-fit: cover; }
.course-hero-eyebrow { font-size: 11.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .04em; }
.course-hero-title {
  display: block; font-size: 16px; color: var(--text-hi); font-family: var(--font-display);
  margin-top: 2px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.course-hero-arc { flex-shrink: 0; }
.course-hero-actions { display: flex; gap: 8px; margin-top: 10px; justify-content: flex-end; }

@media (max-width: 860px) {
  .course-hero { flex-direction: column; }
  .course-hero-side.right { justify-content: center; text-align: center; }
  .course-hero-title { max-width: none; white-space: normal; }
}
</style>
