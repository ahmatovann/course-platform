<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../../components/common/Sidebar.vue'
import ProgressBar from '../../components/learner/ProgressBar.vue'
import OnboardingTour from '../../components/common/OnboardingTour.vue'
import { useCoursesStore } from '../../store/courses'

import { learnerLinks as links } from '../../nav'

const tourDescriptions = {
  '/': 'Здесь все ваши курсы — открывайте и проходите уроки по порядку.',
  '/my-tests': 'Сводный список всех тестов по вашим курсам и результаты попыток.',
  '/chats': 'Общайтесь с куратором и группой, можно отправить и голосовое сообщение.',
  '/news': 'Объявления и расписание от администратора школы.',
  '/profile': 'Смена пароля, оформление и личные данные.',
}

const store = useCoursesStore()
const router = useRouter()
const loading = ref(true)

onMounted(async () => {
  await store.fetchCourses()
  loading.value = false
})
</script>

<template>
  <div class="app active">
    <OnboardingTour :links="links" :descriptions="tourDescriptions" />
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>Мои тренинги</h1></div>
        </div>
        <div class="grid" v-if="!loading">
          <div v-for="c in store.courses" :key="c.id" class="card"
               :style="{ cursor: c.enrolled ? 'pointer' : 'not-allowed', opacity: c.enrolled ? 1 : .7 }"
               @click="c.enrolled && router.push(`/courses/${c.slug}`)">
            <span class="badge" :class="c.enrolled ? 'ok' : 'locked'">{{ c.enrolled ? (c.progress_percent > 0 ? 'В процессе' : 'Не начат') : 'Недоступен' }}</span>
            <h3>{{ c.title }}</h3>
            <p class="desc">{{ c.description }}</p>
            <ProgressBar :percent="c.progress_percent" :label="`${c.modules_count} модулей · ${c.progress_percent}%`" />
          </div>
        </div>
        <p v-if="!loading && store.courses.length === 0" style="color:var(--text-dim)">Курсы пока не назначены.</p>
      </div>
    </main>
  </div>
</template>
