<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import Sidebar from './Sidebar.vue'
import { useChatsStore } from '../../store/chats'
import { useUiStore } from '../../store/ui'
import { useAuthStore } from '../../store/auth'
import { dayKey, dayLabel, timeLabel } from '../../utils/dates'

defineProps({
  links: { type: Array, required: true },
})

const store = useChatsStore()
const ui = useUiStore()
const auth = useAuthStore()
const openThreadId = ref(null)
const draft = ref('')
const scrollEl = ref(null)
const fileInputEl = ref(null)
const openMenuId = ref(null)
let poll = null

function toggleMenu(id) {
  openMenuId.value = openMenuId.value === id ? null : id
}

function pickFile() {
  fileInputEl.value?.click()
}

async function onFileChosen(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file || !openThreadId.value) return
  try {
    await store.sendFileMessage(openThreadId.value, file)
    await scrollToBottom()
  } catch (err) {
    ui.showToast('Не удалось отправить файл', 'error')
  }
}

async function deleteMessage(message, scope) {
  openMenuId.value = null
  try {
    await store.deleteMessage(message.id, scope)
  } catch (err) {
    ui.showToast('Не удалось удалить сообщение', 'error')
  }
}

async function toggleFavorite(message) {
  openMenuId.value = null
  try {
    await store.toggleFavorite(message)
  } catch (err) {
    ui.showToast('Не удалось изменить избранное', 'error')
  }
}

function fileIsImage(name) {
  return /\.(png|jpe?g|gif|webp|svg)$/i.test(name || '')
}

// Если файл голосового сообщения по какой-то причине недоступен на сервере
// (например, поврежденная/устаревшая запись), плеер молча оставался бы
// пустым без единого признака ошибки — ученик слышал тишину и не понимал,
// в чём дело. Показываем явную подпись вместо немого плеера.
function onAudioError(e) {
  const el = e.target
  if (el.dataset.errorShown) return
  el.dataset.errorShown = '1'
  el.style.display = 'none'
  const note = document.createElement('div')
  note.className = 'chat-bubble-audio-error'
  note.textContent = 'Голосовое сообщение недоступно'
  el.insertAdjacentElement('afterend', note)
}

// Голосовые сообщения: запись через MediaRecorder — доступно в любом чате.
const isRecording = ref(false)
const recordSeconds = ref(0)
let mediaRecorder = null
let audioChunks = []
let mediaStream = null
let recordTimer = null

function pickAudioMimeType() {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
  ]
  return candidates.find((type) => MediaRecorder.isTypeSupported?.(type)) || ''
}

function formatRecordTime(s) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}

async function startRecording() {
  if (!openThreadId.value || isRecording.value) return
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    ui.showToast('Запись голоса не поддерживается этим браузером', 'error')
    return
  }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch (e) {
    ui.showToast('Не удалось получить доступ к микрофону', 'error')
    return
  }
  audioChunks = []
  const mimeType = pickAudioMimeType()
  mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : undefined)
  mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
  mediaRecorder.start()
  isRecording.value = true
  recordSeconds.value = 0
  recordTimer = setInterval(() => { recordSeconds.value += 1 }, 1000)
}

function stopMediaStream() {
  if (mediaStream) { mediaStream.getTracks().forEach((t) => t.stop()); mediaStream = null }
  if (recordTimer) { clearInterval(recordTimer); recordTimer = null }
  isRecording.value = false
}

async function stopRecordingAndSend() {
  if (!mediaRecorder || !isRecording.value) return
  const threadId = openThreadId.value
  const mimeType = mediaRecorder.mimeType || 'audio/webm'
  mediaRecorder.onstop = async () => {
    const blob = new Blob(audioChunks, { type: mimeType })
    stopMediaStream()
    if (blob.size > 0 && threadId) {
      try {
        await store.sendVoiceMessage(threadId, blob)
        await scrollToBottom()
      } catch (e) {
        ui.showToast('Не удалось отправить голосовое сообщение', 'error')
      }
    }
  }
  mediaRecorder.stop()
}

function cancelRecording() {
  if (mediaRecorder && isRecording.value) {
    mediaRecorder.onstop = () => stopMediaStream()
    mediaRecorder.stop()
  } else {
    stopMediaStream()
  }
}

onMounted(async () => {
  await store.fetchThreads()
})
onUnmounted(() => {
  if (poll) clearInterval(poll)
  if (isRecording.value) cancelRecording()
})

async function scrollToBottom() {
  await nextTick()
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
}

async function openThread(id) {
  openThreadId.value = id
  await store.fetchMessages(id)
  await scrollToBottom()
  if (poll) clearInterval(poll)
  poll = setInterval(async () => {
    await store.fetchMessages(id)
    await scrollToBottom()
  }, 5000)
}

function backToList() {
  if (isRecording.value) cancelRecording()
  openThreadId.value = null
  if (poll) clearInterval(poll)
}

async function send() {
  const text = draft.value.trim()
  if (!text || !openThreadId.value) return
  await store.sendMessage(openThreadId.value, text)
  draft.value = ''
  await scrollToBottom()
}

function currentThread() {
  return store.threads.find((t) => t.id === openThreadId.value)
}

// Сообщения, размеченные разделителями дат (как в WhatsApp): перед первым
// сообщением каждого нового дня вставляется метка «Сегодня»/«Вчера»/дата.
const timeline = computed(() => {
  const items = []
  let lastDay = null
  for (const m of store.messages) {
    const key = dayKey(m.created_at)
    if (key !== lastDay) {
      items.push({ type: 'separator', key, label: dayLabel(m.created_at) })
      lastDay = key
    }
    items.push({ type: 'message', ...m })
  }
  return items
})

watch(() => store.messages.length, scrollToBottom)
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header"><div><h1>Чаты</h1><p>Общение по тренингам и с администрацией</p></div></div>

        <div class="chat-shell">
          <div class="chat-threads" :class="{ 'mobile-hidden': openThreadId }">
            <div
              class="chat-thread-row" v-for="t in store.threads" :key="t.id"
              :class="{ active: t.id === openThreadId }" @click="openThread(t.id)"
            >
              <div class="avatar">{{ t.title.slice(0, 2).toUpperCase() }}</div>
              <div class="chat-thread-info">
                <div class="chat-thread-top">
                  <span class="chat-thread-title">{{ t.title }}</span>
                  <span class="chat-thread-time" v-if="t.last_message">{{ timeLabel(t.last_message.created_at) }}</span>
                </div>
                <div class="chat-thread-preview">
                  <span class="badge" :class="t.kind === 'group' ? 'ok' : 'locked'">{{ t.kind === 'group' ? 'Групповой' : 'Личный' }}</span>
                  <span>{{ t.last_message ? `${t.last_message.sender_name}: ${t.last_message.text}` : 'Сообщений пока нет' }}</span>
                </div>
              </div>
            </div>
            <p v-if="store.threads.length === 0" style="color:var(--text-dim); padding:14px;">Чатов пока нет.</p>
          </div>

          <div class="chat-conversation" :class="{ 'mobile-hidden': !openThreadId }">
            <template v-if="openThreadId">
              <div class="chat-conv-header">
                <button class="chat-back" @click="backToList">←</button>
                <div>
                  <div class="chat-conv-title">{{ currentThread()?.title }}</div>
                  <div class="chat-conv-sub">{{ currentThread()?.kind === 'group' ? 'Групповой чат' : 'Личный чат' }}</div>
                </div>
              </div>
              <div class="chat-messages" ref="scrollEl" @click="openMenuId = null">
                <template v-for="item in timeline" :key="item.type === 'separator' ? 'sep-' + item.key : 'msg-' + item.id">
                  <div class="chat-date-sep" v-if="item.type === 'separator'"><span>{{ item.label }}</span></div>
                  <div class="chat-bubble-row" v-else :class="{ mine: item.is_mine }">
                    <div class="chat-bubble">
                      <div class="chat-bubble-who" v-if="!item.is_mine">{{ item.sender_name }}</div>

                      <!-- Админ видит содержимое удалённых «у всех» сообщений (с пометкой,
                           когда удалено) — обычные участники чата об этом не знают и
                           по-прежнему видят просто «Сообщение удалено». См. ChatMessageSerializer. -->
                      <template v-if="item.deleted_for_everyone && auth.isAdmin">
                        <div class="chat-bubble-deleted-admin-tag">🛈 Удалено{{ item.deleted_at ? ' · ' + timeLabel(item.deleted_at) : '' }} (видно только администратору)</div>
                        <audio v-if="item.audio_file" class="chat-bubble-audio" controls controlsList="nodownload" :src="item.audio_file"></audio>
                        <a v-if="item.file" class="chat-bubble-file" :href="item.file" target="_blank" rel="noopener">
                          <img v-if="fileIsImage(item.file_name)" :src="item.file" class="chat-bubble-file-thumb" alt="">
                          <span v-else class="chat-bubble-file-icon">📎</span>
                          <span class="chat-bubble-file-name">{{ item.file_name || 'Файл' }}</span>
                        </a>
                        <div class="chat-bubble-text" v-if="item.text">{{ item.text }}</div>
                      </template>
                      <p v-else-if="item.deleted_for_everyone" class="chat-bubble-deleted">Сообщение удалено</p>
                      <template v-else>
                        <audio v-if="item.audio_file" class="chat-bubble-audio" controls controlsList="nodownload" :src="item.audio_file" @error="onAudioError"></audio>
                        <a v-if="item.file" class="chat-bubble-file" :href="item.file" target="_blank" rel="noopener">
                          <img v-if="fileIsImage(item.file_name)" :src="item.file" class="chat-bubble-file-thumb" alt="">
                          <span v-else class="chat-bubble-file-icon">📎</span>
                          <span class="chat-bubble-file-name">{{ item.file_name || 'Файл' }}</span>
                        </a>
                        <div class="chat-bubble-text" v-if="item.text">{{ item.text }}</div>
                      </template>

                      <div class="chat-bubble-foot">
                        <span v-if="item.is_favorite" class="chat-bubble-fav-mark" title="В избранном">★</span>
                        <div class="chat-bubble-time">{{ timeLabel(item.created_at) }}</div>
                      </div>

                      <button
                        v-if="!item.deleted_for_everyone" type="button" class="chat-bubble-menu-btn"
                        @click.stop="toggleMenu(item.id)" aria-label="Действия с сообщением"
                      >⋮</button>
                      <div v-if="openMenuId === item.id" class="chat-bubble-menu" @click.stop>
                        <button @click="toggleFavorite(item)">{{ item.is_favorite ? 'Убрать из избранного' : 'В избранное' }}</button>
                        <button @click="deleteMessage(item, 'me')">Удалить у меня</button>
                        <button v-if="item.is_mine" @click="deleteMessage(item, 'everyone')" class="danger">Удалить у всех</button>
                      </div>
                    </div>
                  </div>
                </template>
                <p v-if="store.messages.length === 0" style="color:var(--text-dim); font-size:12.5px; text-align:center; margin-top:20px;">Сообщений пока нет — начните разговор.</p>
              </div>
              <div class="chat-input-bar" v-if="!isRecording">
                <input ref="fileInputEl" type="file" style="display:none" @change="onFileChosen">
                <button class="mic-btn" @click="pickFile" aria-label="Прикрепить файл" title="Прикрепить файл">
                  <svg viewBox="0 0 20 20" fill="none" width="17" height="17"><path d="M14.5 7.5 8 14a2.5 2.5 0 0 1-3.5-3.5l7-7a1.8 1.8 0 0 1 2.5 2.5l-6.5 6.5a1 1 0 0 1-1.5-1.5L11.5 6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <input v-model="draft" placeholder="Написать сообщение..." @keyup.enter="send">
                <button class="mic-btn" @click="startRecording" aria-label="Записать голосовое сообщение" title="Записать голосовое сообщение">
                  <svg viewBox="0 0 20 20" fill="none" width="17" height="17"><rect x="7" y="2" width="6" height="11" rx="3" stroke="currentColor" stroke-width="1.4"/><path d="M4 10a6 6 0 0 0 12 0M10 16v2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
                </button>
                <button @click="send" aria-label="Отправить">
                  <svg viewBox="0 0 20 20" fill="none" width="18" height="18"><path d="M3 10l14-7-5 14-3-5-6-2Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>
                </button>
              </div>
              <div class="chat-input-bar recording" v-else>
                <span class="record-dot"></span>
                <span class="record-time">{{ formatRecordTime(recordSeconds) }}</span>
                <span class="record-hint">Идёт запись голосового сообщения...</span>
                <button class="dl-btn" @click="cancelRecording" aria-label="Отменить">Отмена</button>
                <button @click="stopRecordingAndSend" aria-label="Остановить и отправить">
                  <svg viewBox="0 0 20 20" fill="none" width="18" height="18"><path d="M3 10l14-7-5 14-3-5-6-2Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>
                </button>
              </div>
            </template>
            <div class="chat-empty-state" v-else>Выберите чат слева, чтобы начать переписку</div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
