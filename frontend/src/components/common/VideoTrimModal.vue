<script setup>
import { computed, ref, watch } from 'vue'
import { useAdminStore } from '../../store/admin'
import { useUiStore } from '../../store/ui'

// video: { lessonId, videoUrl, duration } | null — модалка видна, пока задан.
const props = defineProps({
  video: { type: Object, default: null },
})
const emit = defineEmits(['trimmed', 'cancel'])

const admin = useAdminStore()
const ui = useUiStore()

const videoEl = ref(null)
const start = ref(0)
const end = ref(0)
const saving = ref(false)
const previewing = ref(false)

watch(() => props.video, (v) => {
  if (!v) return
  start.value = 0
  end.value = v.duration || 0
  previewing.value = false
})

function formatTime(sec) {
  const s = Math.max(0, Math.round(sec))
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, '0')}`
}

// Не даём ползункам «начало» и «конец» поменяться местами.
function onStartInput() {
  if (start.value >= end.value) end.value = Math.min(props.video.duration, start.value + 1)
}
function onEndInput() {
  if (end.value <= start.value) start.value = Math.max(0, end.value - 1)
}

const trimmedLength = computed(() => Math.max(0, end.value - start.value))

function seekTo(t) {
  if (videoEl.value) videoEl.value.currentTime = t
}

function previewSelection() {
  const el = videoEl.value
  if (!el) return
  el.currentTime = start.value
  el.play()
  previewing.value = true
}

function onTimeUpdate() {
  const el = videoEl.value
  if (!el || !previewing.value) return
  if (el.currentTime >= end.value) {
    el.pause()
    previewing.value = false
  }
}

async function confirmTrim() {
  if (trimmedLength.value < 1) {
    ui.showToast('Отрезок должен быть не короче 1 секунды', 'error')
    return
  }
  saving.value = true
  try {
    const updated = await admin.trimLessonVideo(props.video.lessonId, start.value, end.value)
    ui.showToast('Видео обрезано', 'success')
    emit('trimmed', updated)
  } catch (e) {
    ui.showToast(e.response?.data?.detail || 'Не удалось обрезать видео', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="modal-overlay" :class="{ active: !!video }">
    <div class="modal" style="max-width:520px" v-if="video">
      <h3>Обрезать видео</h3>
      <p class="mod-sub">Перетащите ползунки, чтобы выбрать отрезок, и проверьте кнопкой «Просмотреть».</p>

      <video
        ref="videoEl" :src="video.videoUrl" controls
        style="width:100%; border-radius:10px; margin:12px 0; background:#000;"
        @timeupdate="onTimeUpdate"
      ></video>

      <div class="field">
        <label>Начало: {{ formatTime(start) }}</label>
        <input
          type="range" min="0" :max="video.duration" step="0.1" v-model.number="start"
          @input="onStartInput" @change="seekTo(start)"
        >
      </div>
      <div class="field">
        <label>Конец: {{ formatTime(end) }}</label>
        <input
          type="range" min="0" :max="video.duration" step="0.1" v-model.number="end"
          @input="onEndInput" @change="seekTo(end)"
        >
      </div>
      <p style="color:var(--text-dim); font-size:12.5px; margin-top:-4px;">Длина отрезка: {{ formatTime(trimmedLength) }}</p>

      <button type="button" class="dl-btn" style="width:100%; margin-top:6px;" @click="previewSelection">▶ Просмотреть отрезок</button>

      <div class="modal-footer">
        <button class="btn-ghost" @click="emit('cancel')">Отмена</button>
        <button class="btn-primary" :disabled="saving" @click="confirmTrim">{{ saving ? 'Обрезаем...' : 'Обрезать' }}</button>
      </div>
    </div>
  </div>
</template>
