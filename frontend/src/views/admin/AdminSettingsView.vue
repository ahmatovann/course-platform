<script setup>
import { onMounted, ref } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useUiStore } from '../../store/ui'
import { useAdminStore } from '../../store/admin'
import { useAuthStore } from '../../store/auth'
import AvatarCropper from '../../components/common/AvatarCropper.vue'
import { adminLinks as links } from '../../nav'

const ui = useUiStore()
const admin = useAdminStore()
const auth = useAuthStore()

// ===== Мой профиль (аватар администратора) =====
const avatarInput = ref(null)
const avatarPreview = ref(auth.user?.avatar || null)
const generatingAvatar = ref(false)
const savingAvatar = ref(false)
const showAvatarLightbox = ref(false)

function pickAvatar() {
  avatarInput.value?.click()
}

// Фото сначала идёт в редактор кадрирования (кроп под ровный квадрат
// нужного размера) — сохраняется только результат кропа.
const cropperFile = ref(null)

function onAvatarChosen(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ui.showToast('Выберите файл изображения', 'error')
    return
  }
  cropperFile.value = file
}

async function onCropSave(croppedFile) {
  avatarPreview.value = URL.createObjectURL(croppedFile)
  cropperFile.value = null
  await saveAvatar(croppedFile)
}

// Бесплатные сгенерированные аватарки через DiceBear (без ключей и регистрации).
// Каждое нажатие — новый случайный вариант в выбранном стиле.
async function generateAvatar() {
  generatingAvatar.value = true
  try {
    const seed = Math.random().toString(36).slice(2)
    const url = `https://api.dicebear.com/9.x/lorelei/png?seed=${seed}&size=256`
    const res = await fetch(url)
    if (!res.ok) throw new Error('bad response')
    const blob = await res.blob()
    const file = new File([blob], `avatar-${seed}.png`, { type: 'image/png' })
    avatarPreview.value = URL.createObjectURL(blob)
    await saveAvatar(file)
  } catch (e) {
    ui.showToast('Не удалось сгенерировать аватар — проверьте интернет', 'error')
  } finally {
    generatingAvatar.value = false
  }
}

async function saveAvatar(file) {
  savingAvatar.value = true
  try {
    const payload = new FormData()
    payload.append('avatar', file)
    await auth.updateProfile(payload)
    ui.showToast('Фото профиля обновлено', 'success')
  } catch (e) {
    ui.showToast('Не удалось сохранить фото', 'error')
  } finally {
    savingAvatar.value = false
  }
}

// ===== История действий администратора =====
onMounted(() => admin.fetchAuditLog())

const actionLabels = { created: 'создал(а)', updated: 'изменил(а)', deleted: 'удалил(а)', toggled: 'переключил(а)' }

function formatLogDate(iso) {
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header"><div><h1>Настройки</h1><p>Оформление и параметры кабинета</p></div></div>

        <div class="mini-card" style="max-width:460px;">
          <h4>Мой профиль</h4>
          <div class="profile-avatar-row">
            <button
              type="button" class="profile-avatar-lg profile-avatar-lg-edit" :class="{ clickable: avatarPreview }"
              @click="avatarPreview && (showAvatarLightbox = true)"
            >
              <img v-if="avatarPreview" :src="avatarPreview" alt="">
              <span v-else>CA</span>
            </button>
            <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="onAvatarChosen">
            <div class="profile-avatar-links">
              <button type="button" class="avatar-action-btn" :disabled="savingAvatar" @click="pickAvatar">Загрузить фото</button>
              <button type="button" class="avatar-action-btn" :disabled="generatingAvatar || savingAvatar" @click="generateAvatar">
                {{ generatingAvatar ? 'Генерируем...' : 'Сгенерировать аватар' }}
              </button>
            </div>
          </div>
        </div>

        <div class="mini-card" style="max-width:460px; margin-top:20px;">
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
          <h4>История</h4>
          <p style="color:var(--text-dim); font-size:12.5px; margin:-4px 0 14px;">Действия администраторов — кто и что сделал, сначала новые</p>
          <table>
            <thead><tr><th>Когда</th><th>Кто</th><th>Действие</th></tr></thead>
            <tbody>
              <tr v-for="entry in admin.auditLog" :key="entry.id">
                <td style="white-space:nowrap; color:var(--text-dim); font-size:12.5px;">{{ formatLogDate(entry.created_at) }}</td>
                <td>{{ entry.actor_name }}</td>
                <td>{{ actionLabels[entry.action] || entry.action }} {{ entry.target_type }} «{{ entry.target_repr }}»</td>
              </tr>
            </tbody>
          </table>
          <p v-if="admin.auditLog.length === 0" style="color:var(--text-dim); margin-top:12px;">Пока ничего не записано.</p>
        </div>
      </div>
    </main>

    <div class="modal-overlay avatar-lightbox-overlay" :class="{ active: showAvatarLightbox }" @click="showAvatarLightbox = false">
      <button type="button" class="avatar-lightbox-close" @click="showAvatarLightbox = false" aria-label="Закрыть">×</button>
      <img v-if="avatarPreview" :src="avatarPreview" class="avatar-lightbox-img" alt="Фото профиля" @click.stop>
    </div>

    <AvatarCropper :file="cropperFile" @save="onCropSave" @cancel="cropperFile = null" />
  </div>
</template>
