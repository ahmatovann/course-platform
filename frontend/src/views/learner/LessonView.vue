<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from '../../components/common/Sidebar.vue'
import { useCoursesStore } from '../../store/courses'
import { useUiStore } from '../../store/ui'
import { useAuthStore } from '../../store/auth'
import { iconForKind } from '../../utils/fileKind'

import { learnerLinks as links } from '../../nav'

const route = useRoute()
const router = useRouter()
const store = useCoursesStore()
const ui = useUiStore()
const auth = useAuthStore()
const lesson = ref(null)
const draft = ref('')
const commentsEl = ref(null)
const videoEl = ref(null)
const isMuted = ref(false)
const volumeLevel = ref(1)
const attachedTimestamp = ref(null)
let alreadyMarking = false

function attachCurrentMoment() {
  const v = videoEl.value
  if (!v) return
  attachedTimestamp.value = Math.floor(v.currentTime)
}

function clearAttachedMoment() {
  attachedTimestamp.value = null
}

function formatTimestamp(seconds) {
  if (seconds == null) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function seekTo(seconds) {
  const v = videoEl.value
  if (!v || seconds == null) return
  v.currentTime = seconds
  v.play().catch(() => {})
}

function toggleMute() {
  const v = videoEl.value
  if (!v) return
  v.muted = !v.muted
  if (!v.muted && v.volume === 0) v.volume = 1
  isMuted.value = v.muted
  volumeLevel.value = v.volume
}

function onVolumeChange() {
  const v = videoEl.value
  if (!v) return
  isMuted.value = v.muted || v.volume === 0
  volumeLevel.value = v.volume
}

async function scrollCommentsToBottom() {
  await nextTick()
  if (commentsEl.value) commentsEl.value.scrollTop = commentsEl.value.scrollHeight
}

async function load() {
  lesson.value = await store.fetchLesson(route.params.id)
  await store.fetchComments(route.params.id)
  await scrollCommentsToBottom()
}
onMounted(load)
watch(() => route.params.id, load)
// Уже отправленные комментарии «уезжают» вверх, а новый всегда виден снизу —
// как в чате: скроллится только список комментариев, поле ввода не двигается.
watch(() => store.lessonComments.length, scrollCommentsToBottom)

// Урок отмечается просмотренным полностью автоматически — как только видео
// доиграло до конца или ученик долистал его почти целиком (90%+), без
// какой-либо кнопки. Повторные события просмотра урок уже не трогают.
async function markWatchedAuto() {
  if (alreadyMarking || lesson.value?.watched) return
  alreadyMarking = true
  try {
    await store.markLessonWatched(lesson.value.id)
    lesson.value.watched = true
  } finally {
    alreadyMarking = false
  }
}

function onVideoEnded() {
  markWatchedAuto()
}

function onTimeUpdate(e) {
  const video = e.target
  if (!video.duration) return
  if (video.currentTime / video.duration >= 0.9) markWatchedAuto()
}

async function sendComment() {
  const text = draft.value.trim()
  if (!text) return
  try {
    await store.postComment(lesson.value.id, text, attachedTimestamp.value)
    draft.value = ''
    attachedTimestamp.value = null
    await scrollCommentsToBottom()
  } catch (e) {
    ui.showToast('Не удалось отправить комментарий', 'error')
  }
}

function formatTime(iso) {
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="app active" v-if="lesson">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header">
          <div><h1>{{ lesson.title }}</h1><p>Урок {{ lesson.order }}</p></div>
          <button class="dl-btn" @click="router.push({ name: 'module', params: { id: lesson.module } })">← К списку уроков</button>
        </div>
        <div class="lesson-layout">
          <div>
            <div class="player-box" v-if="lesson.video_file">
              <video
                ref="videoEl"
                :src="lesson.video_file" :poster="lesson.video_poster || undefined"
                controls controlsList="nodownload" style="width:100%; height:100%; display:block;"
                @ended="onVideoEnded" @timeupdate="onTimeUpdate" @volumechange="onVolumeChange"
              ></video>
              <button type="button" class="video-mute-btn" @click="toggleMute" :aria-label="isMuted ? 'Включить звук' : 'Выключить звук'">
                <svg v-if="isMuted" viewBox="0 0 20 20" fill="none" width="17" height="17"><path d="M3 8v4h3l4 3V5L6 8H3z" fill="currentColor"/><path d="m13 8 4 4M17 8l-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
                <svg v-else viewBox="0 0 20 20" fill="none" width="17" height="17"><path d="M3 8v4h3l4 3V5L6 8H3z" fill="currentColor"/><path d="M13.5 7a3.5 3.5 0 0 1 0 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M15.5 4.5a7 7 0 0 1 0 11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity=".6"/></svg>
              </button>
              <div class="video-watermark" aria-hidden="true">
                <span v-for="n in 6" :key="n">{{ auth.user?.email }}</span>
              </div>
            </div>
            <a v-else-if="lesson.video_url" :href="lesson.video_url" target="_blank" class="player-box" style="text-decoration:none;" @click="markWatchedAuto">
              <div class="play-btn">▶</div>
            </a>
            <div v-else class="player-box"><div class="play-btn">▶</div></div>

            <div class="video-extras" v-if="lesson.video_poster || lesson.video_audio_file">
              <img v-if="lesson.video_poster" :src="lesson.video_poster" alt="Кадр из видео" class="video-poster-thumb">
              <div class="video-audio-alt" v-if="lesson.video_audio_file">
                <span class="video-audio-alt-label">Аудио-версия урока</span>
                <audio :src="lesson.video_audio_file" controls controlsList="nodownload"></audio>
              </div>
            </div>

            <p class="lesson-description" v-if="lesson.description">{{ lesson.description }}</p>

            <div class="materials-box" v-if="lesson.materials?.length">
              <h4>Материалы урока</h4>
              <div class="material-row" v-for="m in lesson.materials" :key="m.id">
                <div class="type-icon">{{ iconForKind(m.kind) }}</div><div class="name">{{ m.name }}</div>
                <a class="dl" :href="m.file" target="_blank">Смотреть</a>
              </div>
            </div>

            <div class="comments-box">
              <h4>Комментарии</h4>
              <div class="comments-list" ref="commentsEl">
                <div class="comment" v-for="c in store.lessonComments" :key="c.id">
                  <div class="avatar">{{ c.user_name.slice(0, 2).toUpperCase() }}</div>
                  <div class="body">
                    <div class="who">
                      {{ c.user_name }} <span class="comment-time">{{ formatTime(c.created_at) }}</span>
                      <button
                        v-if="c.video_timestamp_seconds != null" type="button" class="comment-timestamp-badge"
                        @click="seekTo(c.video_timestamp_seconds)"
                      >▶ {{ formatTimestamp(c.video_timestamp_seconds) }}</button>
                    </div>
                    <div class="txt">{{ c.text }}</div>
                  </div>
                </div>
                <p v-if="store.lessonComments.length === 0" style="color:var(--text-dim); font-size:12.5px;">Комментариев пока нет.</p>
              </div>
              <div class="comment-attach-row" v-if="lesson.video_file">
                <button v-if="attachedTimestamp == null" type="button" class="comment-attach-btn" @click="attachCurrentMoment">
                  ▶ Привязать текущий момент видео
                </button>
                <span v-else class="comment-attach-badge">
                  Момент {{ formatTimestamp(attachedTimestamp) }}
                  <button type="button" @click="clearAttachedMoment" aria-label="Убрать привязку">×</button>
                </span>
              </div>
              <div class="comment-input">
                <input v-model="draft" placeholder="Написать комментарий..." @keyup.enter="sendComment">
                <button @click="sendComment" aria-label="Отправить">
                  <svg viewBox="0 0 20 20" fill="none" width="16" height="16"><path d="M3 10l14-7-5 14-3-5-6-2Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>
                </button>
              </div>
            </div>
          </div>
          <div class="sidebar-panel">
            <div class="mini-card">
              <h4>Статус</h4>
              <p style="font-size:13px;color:var(--text-mid)">{{ lesson.watched ? '✓ Просмотрено' : 'Ещё не просмотрено' }}</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
