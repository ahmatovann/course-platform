<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'

// Кольцо прогресса тренинга — не просто процент, а по одному сегменту на
// каждый модуль: пройденные горят золотом, текущий доступный модуль мягко
// пульсирует, ещё не открытые — приглушены. При появлении сегменты
// «дорисовываются» по очереди, а число в центре считается вверх.
// Полностью на SVG/CSS, без сторонних библиотек.
const props = defineProps({
  modules: { type: Array, required: true }, // [{ title, completed, unlocked }]
  size: { type: Number, default: 240 },
})

const emit = defineEmits(['select'])

const total = computed(() => props.modules.length || 1)
const completedCount = computed(() => props.modules.filter((m) => m.completed).length)
const percent = computed(() => Math.round((completedCount.value / total.value) * 100))

const cx = 100
const cy = 100
const r = 80
const strokeWidth = 15
const gapDeg = Math.min(10, 140 / total.value)

function polarToCartesian(angleDeg) {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(startAngle, endAngle) {
  const start = polarToCartesian(endAngle)
  const end = polarToCartesian(startAngle)
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`
}

const segSpan = computed(() => 360 / total.value)

const segments = computed(() => props.modules.map((m, i) => {
  const startAngle = i * segSpan.value + gapDeg / 2
  const endAngle = (i + 1) * segSpan.value - gapDeg / 2
  const spanRad = ((endAngle - startAngle) * Math.PI) / 180
  const length = r * spanRad
  let state = 'locked'
  if (m.completed) state = 'completed'
  else if (m.unlocked) state = 'current'
  return { ...m, index: i, path: describeArc(startAngle, endAngle), length, state }
}))

// Сегменты «дорисовываются» по очереди при появлении компонента.
const revealed = ref(false)
onMounted(async () => {
  await nextTick()
  requestAnimationFrame(() => { revealed.value = true })
})

// Число в центре считается вверх от 0 до текущего процента.
const animatedPercent = ref(0)
watch(percent, (target) => animateTo(target), { immediate: false })
onMounted(() => animateTo(percent.value))
function animateTo(target) {
  const start = animatedPercent.value
  const startTime = performance.now()
  const duration = 700
  function step(now) {
    const t = Math.min(1, (now - startTime) / duration)
    const eased = 1 - Math.pow(1 - t, 3)
    animatedPercent.value = Math.round(start + (target - start) * eased)
    if (t < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}
</script>

<template>
  <div class="progress-orbit" :style="{ width: size + 'px', height: size + 'px' }">
    <div class="progress-orbit-glow" />
    <svg viewBox="0 0 200 200" :width="size" :height="size">
      <circle class="progress-orbit-track" :cx="cx" :cy="cy" :r="r" fill="none" :stroke-width="strokeWidth" />
      <path
        v-for="seg in segments" :key="seg.index"
        class="progress-orbit-seg" :class="seg.state"
        :d="seg.path" fill="none" :stroke-width="strokeWidth" stroke-linecap="round"
        :stroke-dasharray="seg.length" :stroke-dashoffset="revealed ? 0 : seg.length"
        :style="{ transitionDelay: (seg.index * 90) + 'ms' }"
        @click="seg.unlocked && emit('select', seg)"
      ><title>{{ seg.title }}</title></path>
    </svg>
    <div class="progress-orbit-center">
      <strong>{{ animatedPercent }}%</strong>
      <span>{{ completedCount }} из {{ total }} модулей</span>
      <div class="progress-orbit-trophy" v-if="percent === 100">🏆</div>
    </div>
  </div>
</template>

<style scoped>
.progress-orbit { position: relative; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.progress-orbit svg { position: relative; z-index: 1; display: block; overflow: visible; }

.progress-orbit-glow {
  position: absolute; inset: -18%; border-radius: 50%; z-index: 0;
  background: conic-gradient(from 0deg, transparent 0%, var(--gold) 15%, transparent 35%, transparent 65%, var(--gold) 80%, transparent 100%);
  filter: blur(22px); opacity: .28;
  animation: orbit-spin 7s linear infinite;
}

@keyframes orbit-spin { to { transform: rotate(360deg); } }

.progress-orbit-track { stroke: var(--navy-deep); opacity: .6; }

.progress-orbit-seg {
  transition: stroke-dashoffset .7s cubic-bezier(.22,1,.36,1), filter .2s ease, opacity .2s ease;
  cursor: default;
}
.progress-orbit-seg.completed { stroke: var(--gold); filter: drop-shadow(0 0 3px var(--gold)); }
.progress-orbit-seg.current { stroke: var(--gold); opacity: .55; cursor: pointer; animation: orbit-pulse 1.8s ease-in-out infinite; }
.progress-orbit-seg.locked { stroke: var(--line); opacity: .5; }
.progress-orbit-seg.current:hover, .progress-orbit-seg.completed:hover {
  filter: drop-shadow(0 0 7px var(--gold)); opacity: 1;
}

@keyframes orbit-pulse {
  0%, 100% { opacity: .35; }
  50% { opacity: .8; }
}

.progress-orbit-center {
  position: absolute; inset: 0; z-index: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; text-align: center; line-height: 1.25;
}
.progress-orbit-center strong { font-size: 32px; color: var(--text-hi); font-family: var(--font-display); }
.progress-orbit-center span { font-size: 11.5px; color: var(--text-dim); margin-top: 3px; max-width: 120px; }
.progress-orbit-trophy {
  position: absolute; top: -6px; right: 6px; font-size: 20px;
  animation: trophy-pop .5s cubic-bezier(.34,1.56,.64,1) .6s backwards;
}
@keyframes trophy-pop {
  0% { transform: scale(0) rotate(-20deg); opacity: 0; }
  100% { transform: scale(1) rotate(0deg); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .progress-orbit-glow, .progress-orbit-seg.current, .progress-orbit-trophy { animation: none; }
}
</style>
