<script setup>
import { computed, nextTick, ref, watch } from 'vue'

// Простой редактор кадрирования фото под аватар — без сторонних библиотек.
// Пользователь двигает и масштабирует фото внутри круглой рамки фиксированного
// размера, при сохранении вырезаем именно то, что видно в рамке, и отдаём
// квадратную картинку заданного размера (OUTPUT_SIZE) — независимо от того,
// какого размера/пропорций было исходное фото.
const props = defineProps({
  file: { type: [File, null], default: null },
})
const emit = defineEmits(['save', 'cancel'])

const VIEWPORT = 280
const OUTPUT_SIZE = 320
const MIN_ZOOM = 1
const MAX_ZOOM = 3

const imgEl = ref(null)
const imgSrc = ref('')
const naturalWidth = ref(0)
const naturalHeight = ref(0)
const baseScale = ref(1)
const zoom = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)
const saving = ref(false)

watch(() => props.file, async (file) => {
  if (!file) {
    imgSrc.value = ''
    return
  }
  imgSrc.value = URL.createObjectURL(file)
  zoom.value = 1
  await nextTick()
})

function onImgLoad() {
  const el = imgEl.value
  if (!el) return
  naturalWidth.value = el.naturalWidth
  naturalHeight.value = el.naturalHeight
  // Масштаб, при котором фото полностью закрывает круглую рамку (как object-fit: cover).
  baseScale.value = Math.max(VIEWPORT / naturalWidth.value, VIEWPORT / naturalHeight.value)
  centerImage()
}

function centerImage() {
  const scale = baseScale.value * zoom.value
  const w = naturalWidth.value * scale
  const h = naturalHeight.value * scale
  offsetX.value = (VIEWPORT - w) / 2
  offsetY.value = (VIEWPORT - h) / 2
}

const currentScale = computed(() => baseScale.value * zoom.value)
const displayW = computed(() => naturalWidth.value * currentScale.value)
const displayH = computed(() => naturalHeight.value * currentScale.value)

function clampOffsets() {
  const minX = VIEWPORT - displayW.value
  const minY = VIEWPORT - displayH.value
  offsetX.value = Math.min(0, Math.max(minX, offsetX.value))
  offsetY.value = Math.min(0, Math.max(minY, offsetY.value))
}

// При изменении зума держим точку, которая была в центре рамки, на месте,
// а не съезжаем в угол. Считаем через watch (а не в обработчике @input),
// потому что нужны именно СТАРЫЙ и НОВЫЙ масштаб одновременно — иначе
// computed-геттеры уже отдают новое значение раньше времени.
watch(zoom, (newZoom, oldZoom) => {
  if (!naturalWidth.value) return
  const oldW = naturalWidth.value * baseScale.value * oldZoom
  const oldH = naturalHeight.value * baseScale.value * oldZoom
  const ratioX = (VIEWPORT / 2 - offsetX.value) / oldW
  const ratioY = (VIEWPORT / 2 - offsetY.value) / oldH
  const newW = naturalWidth.value * baseScale.value * newZoom
  const newH = naturalHeight.value * baseScale.value * newZoom
  offsetX.value = VIEWPORT / 2 - ratioX * newW
  offsetY.value = VIEWPORT / 2 - ratioY * newH
  clampOffsets()
})

// ===== Перетаскивание (мышь и тач) =====
let dragging = false
let dragStartX = 0
let dragStartY = 0
let startOffsetX = 0
let startOffsetY = 0

function pointerPos(e) {
  if (e.touches && e.touches[0]) return { x: e.touches[0].clientX, y: e.touches[0].clientY }
  return { x: e.clientX, y: e.clientY }
}

function startDrag(e) {
  dragging = true
  const p = pointerPos(e)
  dragStartX = p.x
  dragStartY = p.y
  startOffsetX = offsetX.value
  startOffsetY = offsetY.value
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', endDrag)
  window.addEventListener('touchmove', onDrag, { passive: false })
  window.addEventListener('touchend', endDrag)
}

function onDrag(e) {
  if (!dragging) return
  if (e.cancelable) e.preventDefault()
  const p = pointerPos(e)
  offsetX.value = startOffsetX + (p.x - dragStartX)
  offsetY.value = startOffsetY + (p.y - dragStartY)
  clampOffsets()
}

function endDrag() {
  dragging = false
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', endDrag)
  window.removeEventListener('touchmove', onDrag)
  window.removeEventListener('touchend', endDrag)
}

async function confirmCrop() {
  if (!imgEl.value || !naturalWidth.value) return
  saving.value = true
  try {
    const canvas = document.createElement('canvas')
    canvas.width = OUTPUT_SIZE
    canvas.height = OUTPUT_SIZE
    const ctx = canvas.getContext('2d')
    const scale = currentScale.value
    // Переводим видимую в рамке область обратно в координаты исходного фото.
    const sx = -offsetX.value / scale
    const sy = -offsetY.value / scale
    const sSize = VIEWPORT / scale
    ctx.drawImage(imgEl.value, sx, sy, sSize, sSize, 0, 0, OUTPUT_SIZE, OUTPUT_SIZE)
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png', 0.92))
    const croppedFile = new File([blob], (props.file?.name || 'avatar') + '.png', { type: 'image/png' })
    emit('save', croppedFile)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="modal-overlay" :class="{ active: !!file }">
    <div class="modal" v-if="file">
      <h3>Настройте фото</h3>
      <p class="mod-sub">Перетащите, чтобы выбрать область, и приблизьте ползунком — сохранится ровный квадрат под аватар.</p>

      <div class="cropper-viewport" :style="{ width: VIEWPORT + 'px', height: VIEWPORT + 'px' }"
           @mousedown="startDrag" @touchstart="startDrag">
        <img
          ref="imgEl" :src="imgSrc" alt="" draggable="false"
          @load="onImgLoad"
          :style="{ width: displayW + 'px', height: displayH + 'px', transform: `translate(${offsetX}px, ${offsetY}px)` }"
        >
        <div class="cropper-guide"></div>
      </div>

      <div class="cropper-zoom">
        <span>−</span>
        <input type="range" :min="MIN_ZOOM" :max="MAX_ZOOM" step="0.01" v-model.number="zoom">
        <span>+</span>
      </div>

      <div class="modal-footer">
        <button class="btn-ghost" @click="emit('cancel')">Отмена</button>
        <button class="btn-primary" :disabled="saving" @click="confirmCrop">{{ saving ? 'Сохраняем...' : 'Готово' }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cropper-viewport {
  position: relative;
  margin: 0 auto;
  overflow: hidden;
  border-radius: 12px;
  background: var(--navy-deep);
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.cropper-viewport:active { cursor: grabbing; }
.cropper-viewport img {
  position: absolute;
  top: 0;
  left: 0;
  max-width: none;
  pointer-events: none;
}
.cropper-guide {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.55);
  border: 2px solid rgba(255, 255, 255, 0.85);
  pointer-events: none;
}
.cropper-zoom {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  color: var(--text-dim);
  font-size: 16px;
}
.cropper-zoom input[type="range"] {
  flex: 1;
}
</style>
