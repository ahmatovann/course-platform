<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../../components/common/Sidebar.vue'
import { useCoursesStore } from '../../store/courses'
import { useUiStore } from '../../store/ui'
import { learnerLinks as links } from '../../nav'

const store = useCoursesStore()
const ui = useUiStore()
const router = useRouter()
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  const courses = await store.fetchCourses()
  const enrolled = courses.filter((c) => c.enrolled)
  const result = []
  for (const c of enrolled) {
    const detail = await store.fetchCourse(c.slug)
    detail.modules.forEach((m) => {
      if (m.has_test) {
        result.push({
          courseTitle: c.title,
          moduleTitle: m.title,
          testId: m.test_id,
          unlocked: m.unlocked,
          passed: m.status.test_passed,
          bestScore: m.status.test_best_score,
          threshold: m.pass_threshold_percent,
        })
      }
    })
  }
  items.value = result
  loading.value = false
})

function open(item) {
  if (!item.unlocked) { ui.showToast('Тест пока закрыт', 'error'); return }
  router.push({ name: 'test', params: { id: item.testId } })
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header"><div><h1>Тестирования</h1><p>Доступные тесты по модулям</p></div></div>
        <div class="grid" v-if="!loading">
          <div class="card" v-for="(item, i) in items" :key="i"
               :style="{ cursor: item.unlocked ? 'pointer' : 'not-allowed', opacity: item.unlocked ? 1 : .7 }"
               @click="open(item)">
            <span class="badge" :class="item.unlocked ? 'ok' : 'locked'">{{ item.unlocked ? (item.passed ? 'Сдан' : 'Доступен') : 'Закрыт' }}</span>
            <h3>{{ item.moduleTitle }}</h3>
            <p class="desc">
              {{ item.courseTitle }}<br>
              <span v-if="item.passed">Пройден на {{ item.bestScore }}% (порог {{ item.threshold }}%)</span>
              <span v-else-if="!item.unlocked">Откроется после предыдущего модуля</span>
              <span v-else>Порог прохождения — {{ item.threshold }}%</span>
            </p>
          </div>
        </div>
        <p v-if="!loading && items.length === 0" style="color:var(--text-dim)">Пока нет доступных тестов.</p>
      </div>
    </main>
  </div>
</template>
