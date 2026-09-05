<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import ProgressRing from '../../components/common/ProgressRing.vue'
import { useAdminStore } from '../../store/admin'
import { useUiStore } from '../../store/ui'
import { adminLinks as links } from '../../nav'
import client from '../../api/client'

const admin = useAdminStore()
const ui = useUiStore()
const selectedId = ref(null)
const progress = ref(null)
const loading = ref(false)

// Поиск/фильтр по списку учеников — тот же паттерн, что и в разделе «Ученики».
const studentSearch = ref('')
const filteredStudents = computed(() => {
  const q = studentSearch.value.trim().toLowerCase()
  if (!q) return admin.students
  return admin.students.filter((s) => (
    `${s.first_name} ${s.last_name} ${s.email}`.toLowerCase().includes(q)
  ))
})

// Фильтр «сколько учеников прошли определённый модуль» — своя мини-выборка,
// не зависящая от выбранного в основном селекте ученика.
const moduleFilterId = ref('')
const moduleFilterStudents = ref(null)
const moduleFilterLoading = ref(false)

async function loadModuleFilter() {
  if (!moduleFilterId.value) { moduleFilterStudents.value = null; return }
  moduleFilterLoading.value = true
  try {
    const { data } = await client.get('/admin/students/', { params: { module_completed: moduleFilterId.value } })
    moduleFilterStudents.value = data
  } finally {
    moduleFilterLoading.value = false
  }
}
watch(moduleFilterId, loadModuleFilter)

const moduleFilterStat = computed(() => admin.moduleStats.find((m) => String(m.id) === String(moduleFilterId.value)))

onMounted(async () => {
  await admin.fetchStudents()
  await admin.fetchModuleStats()
  if (admin.students.length) {
    selectedId.value = admin.students[0].id
    await load()
  }
})

async function load() {
  if (!selectedId.value) return
  loading.value = true
  progress.value = await admin.fetchStudentProgress(selectedId.value)
  loading.value = false
}

function pickStudent(id) {
  selectedId.value = id
  load()
}

async function exportProgress() {
  if (!selectedId.value) return
  const student = admin.students.find((s) => s.id === selectedId.value)
  try {
    await admin.exportStudentProgress(selectedId.value, student?.email)
  } catch (e) {
    ui.showToast('Не удалось экспортировать', 'error')
  }
}

async function exportProgressPdf() {
  if (!selectedId.value) return
  const student = admin.students.find((s) => s.id === selectedId.value)
  try {
    await admin.exportStudentProgressPdf(selectedId.value, student?.email)
  } catch (e) {
    ui.showToast('Не удалось экспортировать PDF', 'error')
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// Простая статистика по открытому ученику — среднее по всем тренингам и
// сколько модулей всего пройдено/не пройдено (используется для диаграммы).
const overallStats = computed(() => {
  if (!progress.value?.courses?.length) return null
  const totalModules = progress.value.courses.reduce((sum, c) => sum + c.modules_total, 0)
  const completedModules = progress.value.courses.reduce((sum, c) => sum + c.modules_completed, 0)
  const avgPercent = Math.round(
    progress.value.courses.reduce((sum, c) => sum + c.completion_percent, 0) / progress.value.courses.length,
  )
  return { totalModules, completedModules, avgPercent }
})

const expandedAttempts = ref(new Set())
function toggleAttempts(moduleId) {
  const next = new Set(expandedAttempts.value)
  if (next.has(moduleId)) next.delete(moduleId)
  else next.add(moduleId)
  expandedAttempts.value = next
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>Прогресс ученика</h1><p>Выберите ученика, чтобы увидеть его прогресс по тренингам, статистику и историю тестов</p></div>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button class="dl-btn" @click="exportProgress" :disabled="!selectedId">⬇ Excel</button>
            <button class="dl-btn" @click="exportProgressPdf" :disabled="!selectedId">⬇ PDF</button>
          </div>
        </div>

        <div class="search-row">
          <input class="search-input" v-model="studentSearch" placeholder="Поиск ученика по имени или email...">
          <select v-model="selectedId" @change="load">
            <option v-for="s in filteredStudents" :key="s.id" :value="s.id">
              {{ s.first_name }} {{ s.last_name }} ({{ s.email }})
            </option>
          </select>
        </div>
        <p v-if="filteredStudents.length === 0" style="color:var(--text-dim); font-size:12.5px; margin-top:6px;">Никого не найдено.</p>

        <!-- Аналитика: сколько учеников прошли конкретный модуль -->
        <div class="mini-card" style="margin-top:22px;">
          <h4>Сколько учеников прошли модуль</h4>
          <div class="field" style="max-width:420px;">
            <select v-model="moduleFilterId">
              <option value="">Выберите модуль...</option>
              <option v-for="m in admin.moduleStats" :key="m.id" :value="m.id">
                {{ m.course_title }} — {{ m.title }}
              </option>
            </select>
          </div>
          <div v-if="moduleFilterStat" style="margin-top:14px; display:flex; align-items:center; gap:20px; flex-wrap:wrap;">
            <ProgressRing :percent="moduleFilterStat.completed_percent" :size="88" :stroke-width="8" />
            <div style="flex:1; min-width:220px;">
              <div class="chart-bar-row">
                <span class="chart-bar-label">{{ moduleFilterStat.completed_count }} из {{ moduleFilterStat.total_enrolled }} ({{ moduleFilterStat.completed_percent }}%)</span>
                <div class="chart-bar-track"><div class="chart-bar-fill" :style="{ width: moduleFilterStat.completed_percent + '%' }"></div></div>
              </div>
            </div>
            <div v-if="moduleFilterStudents?.length" style="margin-top:12px; display:flex; flex-wrap:wrap; gap:8px; width:100%;">
              <button
                v-for="s in moduleFilterStudents" :key="s.id" class="dl-btn" style="padding:7px 12px; font-size:12px;"
                @click="pickStudent(s.id)"
              >{{ s.first_name }} {{ s.last_name }}</button>
            </div>
            <p v-else-if="!moduleFilterLoading" style="color:var(--text-dim); font-size:12.5px; margin-top:10px;">Пока никто из записанных учеников не прошёл этот модуль.</p>
          </div>
        </div>

        <div v-if="!loading && progress" style="margin-top:20px;">
          <p v-if="progress.courses.length === 0" style="color:var(--text-dim)">Ученик не записан ни на один тренинг.</p>

          <!-- Сводная статистика и диаграмма по выбранному ученику -->
          <div class="mini-card" v-if="overallStats" style="margin-bottom:22px;">
            <h4>Сводная статистика — {{ progress.student.name }}</h4>
            <div style="display:flex; align-items:center; gap:22px; flex-wrap:wrap; margin-bottom:14px;">
              <ProgressRing :percent="overallStats.avgPercent" :size="110" label="средний прогресс" />
              <p style="font-size:13px; color:var(--text-mid); flex:1; min-width:200px;">
                Пройдено модулей: {{ overallStats.completedModules }} из {{ overallStats.totalModules }} ·
                Средний процент прохождения по тренингам: {{ overallStats.avgPercent }}%
              </p>
            </div>
            <div class="chart-bar-row" v-for="c in progress.courses" :key="c.course_id">
              <span class="chart-bar-label">{{ c.course_title }} — {{ c.modules_completed }}/{{ c.modules_total }} ({{ c.completion_percent }}%)</span>
              <div class="chart-bar-track"><div class="chart-bar-fill" :style="{ width: c.completion_percent + '%' }"></div></div>
            </div>
          </div>

          <div v-for="c in progress.courses" :key="c.course_id" style="margin-bottom:22px;">
            <h3 style="font-family:var(--font-display); font-size:20px; margin-bottom:10px;">{{ c.course_title }}</h3>
            <div class="module-list">
              <div class="module-item-wrap" v-for="m in c.modules" :key="m.id">
                <div class="module-item">
                  <div class="num">{{ m.order }}</div>
                  <div class="info">
                    <h4>{{ m.title }}</h4>
                    <span>
                      {{ m.lessons_watched }}/{{ m.lessons_total }} уроков просмотрено
                      <template v-if="m.has_test">
                        · тест: {{ m.test_passed ? `сдан на ${m.test_best_score}%` : (m.test_best_score !== null ? `не сдан (${m.test_best_score}%)` : 'не начат') }}
                      </template>
                      <template v-if="!m.unlocked"> · заблокирован</template>
                    </span>
                    <div class="chart-bar-track slim" v-if="m.lessons_total">
                      <div class="chart-bar-fill" :style="{ width: Math.round(m.lessons_watched / m.lessons_total * 100) + '%' }"></div>
                    </div>
                  </div>
                  <div class="status-icon" :style="{ color: m.completed ? 'var(--ok)' : (m.unlocked ? 'var(--gold)' : '') }">
                    {{ m.completed ? '✓' : (m.unlocked ? '●' : '▪') }}
                  </div>
                </div>
                <!-- История прохождения теста: не только лучший результат, а все попытки -->
                <div class="attempts-box" v-if="m.has_test">
                  <button class="attempts-toggle" @click="toggleAttempts(m.id)">
                    {{ expandedAttempts.has(m.id) ? '▾' : '▸' }} История попыток теста ({{ m.test_attempts_count }})
                  </button>
                  <table class="attempts-table" v-if="expandedAttempts.has(m.id)">
                    <thead><tr><th>#</th><th>Дата</th><th>Результат</th><th>Статус</th></tr></thead>
                    <tbody>
                      <tr v-for="(a, idx) in m.test_attempts" :key="a.id">
                        <td>{{ m.test_attempts_count - idx }}</td>
                        <td>{{ formatDate(a.submitted_at) }}</td>
                        <td>{{ a.score_percent }}%</td>
                        <td :style="{ color: a.passed ? 'var(--ok)' : 'var(--danger)' }">{{ a.passed ? 'Сдан' : 'Не сдан' }}</td>
                      </tr>
                      <tr v-if="m.test_attempts_count === 0"><td colspan="4" style="color:var(--text-dim);">Попыток ещё не было.</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
