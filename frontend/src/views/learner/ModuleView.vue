<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from '../../components/common/Sidebar.vue'
import { useCoursesStore } from '../../store/courses'

import { learnerLinks as links } from '../../nav'

const route = useRoute()
const router = useRouter()
const store = useCoursesStore()
const module = ref(null)

async function load() {
  module.value = await store.fetchModule(route.params.id)
}
onMounted(load)
watch(() => route.params.id, load)
</script>

<template>
  <div class="app active" v-if="module">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>{{ module.title }}</h1><p>{{ module.status.lessons_watched }}/{{ module.status.lessons_total }} уроков просмотрено</p></div>
          <button class="dl-btn" @click="router.back()">← Назад к модулям</button>
        </div>
        <div class="lesson-list">
          <div v-for="l in module.lessons" :key="l.id" class="lesson-item" @click="router.push({ name: 'lesson', params: { id: l.id } })">
            <div class="num">{{ l.order }}</div>
            <div class="info"><h4>{{ l.title }}</h4><span>Видео {{ Math.round(l.duration_seconds / 60) }} мин</span></div>
            <div class="status-icon" :style="{ color: l.watched ? 'var(--ok)' : 'var(--gold)' }">{{ l.watched ? '✓' : '●' }}</div>
          </div>
          <div v-if="module.has_test" class="lesson-item" @click="router.push({ name: 'test', params: { id: module.test_id } })">
            <div class="num">T</div>
            <div class="info"><h4>Тест модуля</h4><span>Порог прохождения — {{ module.pass_threshold_percent }}%</span></div>
            <div class="status-icon" :style="{ color: module.status.test_passed ? 'var(--ok)' : 'var(--gold)' }">{{ module.status.test_passed ? '✓' : '●' }}</div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
