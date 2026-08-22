<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useUiStore } from '../../store/ui'
import { useAdminStore } from '../../store/admin'
import { adminLinks as links } from '../../nav'

const ui = useUiStore()
const admin = useAdminStore()

// ===== Библиотека видео =====
const search = ref('')
const courseFilter = ref('')
let debounceTimer = null

onMounted(async () => {
  await Promise.all([admin.fetchVideos(), admin.fetchAdminCourses()])
})

watch([search, courseFilter], () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    admin.fetchVideos({ search: search.value || undefined, course: courseFilter.value || undefined })
  }, 300)
})
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return '—'
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`
}

function formatDuration(sec) {
  if (!sec) return '—'
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

const playingVideo = ref(null)
function openPlayer(v) {
  playingVideo.value = v
}
function closePlayer() {
  playingVideo.value = null
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header"><div><h1>Настройки</h1><p>Оформление и параметры кабинета</p></div></div>
        <div class="mini-card" style="max-width:460px;">
          <h4>Настройки</h4>
          <div class="settings-row">
            <div class="lbl">Оформление<small>Тёмная или светлая тема интерфейса</small></div>
            <div class="settings-switch">
              <button type="button" :class="{ active: ui.theme === 'dark' }" @click="ui.setTheme('dark')">Тёмная</button>
              <button type="button" :class="{ active: ui.theme === 'light' }" @click="ui.setTheme('light')">Светлая</button>
            </div>
          </div>
        </div>

        <div class="mini-card" style="margin-top:20px;">
          <h4>Видео уроков</h4>
          <p style="color:var(--text-dim); font-size:12.5px; margin:-4px 0 14px;">Все загруженные видео по всем тренингам</p>

          <div class="search-row">
            <input class="search-input" v-model="search" placeholder="Поиск по названию урока, модуля или курса...">
            <select v-model="courseFilter">
              <option value="">Все тренинги</option>
              <option v-for="c in admin.adminCourses" :key="c.id" :value="c.id">{{ c.title }}</option>
            </select>
          </div>

          <div class="grid">
            <div class="card" v-for="v in admin.videos" :key="v.id">
              <div
                class="video-thumb"
                :style="v.video_poster ? { backgroundImage: `url(${v.video_poster})` } : {}"
                @click="openPlayer(v)"
              >
                <span v-if="!v.video_poster" class="video-thumb-fallback">▶</span>
                <span class="video-thumb-play">▶</span>
                <span class="video-thumb-duration">{{ formatDuration(v.duration_seconds) }}</span>
              </div>
              <h3>{{ v.title }}</h3>
              <p class="desc">
                {{ v.course_title }} · {{ v.module_title }}<br>
                Размер файла: {{ formatSize(v.file_size) }}
              </p>
              <button type="button" class="btn-ghost" style="width:100%" @click="openPlayer(v)">Смотреть</button>
            </div>
            <p v-if="admin.videos.length === 0" style="color:var(--text-dim); font-size:13px;">Видео не найдены.</p>
          </div>
        </div>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: playingVideo }" @click="closePlayer">
      <div class="modal" style="max-width:720px" v-if="playingVideo" @click.stop>
        <h3>{{ playingVideo.title }}</h3>
        <p class="mod-sub">{{ playingVideo.course_title }} · {{ playingVideo.module_title }}</p>
        <video
          :src="playingVideo.video_file" :poster="playingVideo.video_poster || undefined"
          controls autoplay style="width:100%; border-radius:10px; margin:12px 0; background:#000;"
        ></video>
        <div class="modal-footer">
          <button class="btn-ghost" @click="closePlayer">Закрыть</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.video-thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 10px;
  background: var(--navy-deep) center / cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  margin-bottom: 10px;
}
.video-thumb-fallback { font-size: 28px; color: var(--text-dim); }
.video-thumb-play {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  background: rgba(0, 0, 0, 0.25);
  opacity: 0;
  transition: opacity 0.15s;
}
.video-thumb:hover .video-thumb-play { opacity: 1; }
.video-thumb-duration {
  position: absolute;
  right: 8px;
  bottom: 8px;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
}
</style>
