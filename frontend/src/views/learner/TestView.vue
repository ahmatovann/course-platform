<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from '../../components/common/Sidebar.vue'
import { useCoursesStore } from '../../store/courses'
import { useUiStore } from '../../store/ui'

import { learnerLinks as links } from '../../nav'

const route = useRoute()
const router = useRouter()
const store = useCoursesStore()
const ui = useUiStore()
const test = ref(null)
const answers = reactive({})
const result = ref(null)

onMounted(async () => {
  test.value = await store.fetchTest(route.params.id)
})

function choose(qId, optId) {
  answers[qId] = optId
}

async function submit() {
  if (Object.keys(answers).length < test.value.questions.length) {
    ui.showToast('Ответьте на все вопросы', 'error')
    return
  }
  result.value = await store.submitTest(test.value.id, answers)
  if (result.value.passed) {
    ui.showToast(`Тест сдан на ${result.value.score_percent}%! Следующий модуль открыт.`, 'success')
    router.push('/')
  } else {
    ui.showToast(`Тест не сдан: ${result.value.score_percent}% (нужно больше)`, 'error')
  }
}
</script>

<template>
  <div class="app active" v-if="test">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>{{ test.title }}</h1><p>Выберите один вариант ответа на каждый вопрос</p></div>
          <button class="dl-btn" @click="router.back()">← Назад</button>
        </div>
        <div class="test-box">
          <div v-for="(q, i) in test.questions" :key="q.id" class="q-block">
            <div class="q-title">{{ i + 1 }}. {{ q.text }}</div>
            <label v-for="o in q.options" :key="o.id" class="opt" :class="{ selected: answers[q.id] === o.id }">
              <input type="radio" :name="'q' + q.id" @change="choose(q.id, o.id)">{{ o.text }}
            </label>
          </div>
          <button class="btn-primary" style="max-width:220px" @click="submit">Завершить тест</button>
        </div>
      </div>
    </main>
  </div>
</template>
