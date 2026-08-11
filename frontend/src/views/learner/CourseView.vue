<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from '../../components/common/Sidebar.vue'
import { useCoursesStore } from '../../store/courses'
import { useUiStore } from '../../store/ui'

import { learnerLinks as links } from '../../nav'

const route = useRoute()
const router = useRouter()
const store = useCoursesStore()
const ui = useUiStore()
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
        <div class="main-header">
          <div><h1>{{ course.title }}</h1><p>Модуль открывается только после прохождения предыдущего</p></div>
          <div style="display:flex; gap:10px;">
            <button v-if="course.certificate_available" class="dl-btn" @click="downloadCertificate">Скачать сертификат</button>
            <button class="dl-btn" @click="router.push('/')">← Ко всем тренингам</button>
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
