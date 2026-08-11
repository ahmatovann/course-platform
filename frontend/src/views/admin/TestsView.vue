<script setup>
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useAdminStore } from '../../store/admin'
import { useCoursesStore } from '../../store/courses'
import { useUiStore } from '../../store/ui'

import { adminLinks as links } from '../../nav'

const admin = useAdminStore()
const courses = useCoursesStore()
const ui = useUiStore()
const search = ref('')
let debounceTimer = null

const showModal = ref(false)
const editingId = ref(null)
const form = reactive({ title: '', module: null, questions: [] })

// модули без теста (для создания нового) + модуль редактируемого теста
const availableModules = ref([])

onMounted(async () => {
  await admin.fetchTests()
  await admin.fetchAdminCourses()
  computeAvailableModules()
})

watch(search, () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    admin.fetchTests({ search: search.value || undefined })
  }, 300)
})
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

function computeAvailableModules() {
  const list = []
  admin.adminCourses.forEach((c) => {
    c.modules.forEach((m) => {
      if (!m.has_test) list.push({ id: m.id, label: `${c.title} · ${m.title}` })
    })
  })
  availableModules.value = list
}

function blankQuestion() {
  return { text: '', options: [{ text: '', is_correct: true }, { text: '', is_correct: false }] }
}

function openCreate() {
  editingId.value = null
  form.title = ''
  form.module = availableModules.value[0]?.id || null
  form.questions = [blankQuestion()]
  showModal.value = true
}

async function openEdit(test) {
  editingId.value = test.id
  const detail = await admin.fetchTestDetail(test.id)
  form.title = detail.title
  form.module = detail.module
  form.questions = detail.questions.map((q) => ({
    text: q.text,
    options: q.options.map((o) => ({ text: o.text, is_correct: o.is_correct })),
  }))
  showModal.value = true
}

function addQuestion() {
  form.questions.push(blankQuestion())
}
function removeQuestion(i) {
  form.questions.splice(i, 1)
}
function addOption(qi) {
  form.questions[qi].options.push({ text: '', is_correct: false })
}
function removeOption(qi, oi) {
  form.questions[qi].options.splice(oi, 1)
}
function markCorrect(qi, oi) {
  form.questions[qi].options.forEach((o, i) => { o.is_correct = i === oi })
}

async function save() {
  if (!form.title.trim() || !form.module) { ui.showToast('Укажите название и модуль', 'error'); return }
  try {
    if (editingId.value) {
      await admin.updateTest(editingId.value, form)
      ui.showToast('Тест сохранён', 'success')
    } else {
      await admin.createTest(form)
      ui.showToast('Тест создан', 'success')
    }
    showModal.value = false
    await admin.fetchAdminCourses()
    computeAvailableModules()
  } catch (e) {
    const msg = e.response?.data ? JSON.stringify(e.response.data) : 'Ошибка сохранения'
    ui.showToast(msg, 'error')
  }
}

async function remove(id) {
  if (!confirm('Удалить тест?')) return
  await admin.deleteTest(id)
  await admin.fetchAdminCourses()
  computeAvailableModules()
  ui.showToast('Тест удалён', 'success')
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>Управление тестами</h1><p>Список тестов по модулям. Нажмите «Редактировать» для изменения.</p></div>
          <button class="btn-primary" style="width:auto; padding:12px 22px" @click="openCreate">+ Создать тест</button>
        </div>
        <div class="search-row">
          <input class="search-input" v-model="search" placeholder="Поиск по названию теста...">
        </div>
        <div class="grid">
          <div class="card" v-for="t in admin.tests" :key="t.id">
            <span class="badge ok">Тест</span>
            <h3>{{ t.title }}</h3>
            <p class="desc">{{ t.module_title }} · {{ t.questions.length }} вопросов</p>
            <div style="display:flex; gap:8px; margin-top:10px;">
              <button class="dl-btn" @click="openEdit(t)">✎ Редактировать</button>
              <button class="dl-btn" style="border-color:var(--danger); color:var(--danger);" @click="remove(t.id)">Удалить</button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal">
        <h3>{{ editingId ? 'Редактирование теста' : 'Новый тест' }}</h3>
        <p class="mod-sub">Добавляйте, удаляйте и редактируйте вопросы. Отметьте правильный вариант.</p>

        <div class="field"><label>Название теста</label><input v-model="form.title" placeholder="Тест модуля 2"></div>
        <div class="field" v-if="!editingId">
          <label>Модуль</label>
          <select v-model="form.module">
            <option v-for="m in availableModules" :key="m.id" :value="m.id">{{ m.label }}</option>
          </select>
        </div>

        <div v-for="(q, qi) in form.questions" :key="qi" class="q-block">
          <div class="q-title">Вопрос {{ qi + 1 }}</div>
          <input style="width:100%; padding:10px 12px; background:var(--navy-deep); border:1px solid var(--line); border-radius:8px; color:var(--text-hi); margin-bottom:10px; font-size:13px;"
                 v-model="q.text" placeholder="Текст вопроса...">
          <label v-for="(o, oi) in q.options" :key="oi" class="opt" :class="{ selected: o.is_correct }">
            <input type="radio" :name="'correct' + qi" :checked="o.is_correct" @change="markCorrect(qi, oi)">
            <input type="text" v-model="o.text" :placeholder="'Вариант ' + (oi + 1)" style="flex:1;">
            <button class="dl-btn" style="padding:4px 8px;" @click.prevent="removeOption(qi, oi)">✕</button>
          </label>
          <button class="dl-btn" style="margin-top:6px;" @click="addOption(qi)">+ Вариант</button>
          <button class="dl-btn" style="margin-top:8px; margin-left:8px; border-color:var(--danger); color:var(--danger);" @click="removeQuestion(qi)">Удалить вопрос</button>
        </div>

        <div style="margin-top: 10px;">
          <button class="dl-btn" @click="addQuestion">+ Добавить вопрос</button>
        </div>
        <div class="modal-footer">
          <button class="btn-ghost" @click="showModal = false">Закрыть</button>
          <button class="btn-primary" @click="save">Сохранить</button>
        </div>
      </div>
    </div>
  </div>
</template>
