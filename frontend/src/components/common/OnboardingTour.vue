<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useAuthStore } from '../../store/auth'
import WaveMascot from './WaveMascot.vue'

const props = defineProps({
  links: { type: Array, required: true }, // [{to, label, icon}]
  descriptions: { type: Object, default: () => ({}) }, // { [to]: text }
})

// Тур — инструкция для тех, кто в первый раз: показывается один раз на
// пользователя (флаг сохраняется в localStorage), дальше не всплывает.
const DEV_ALWAYS_SHOW = false

const auth = useAuthStore()
const storageKey = computed(() => `onboarding_seen_${auth.user?.id ?? 'anon'}`)

const visible = ref(false)
const step = ref(0) // 0 = приветствие, 1..N = пункты меню
const targetRect = ref(null)

const steps = computed(() => [
  { type: 'welcome' },
  ...props.links.map((l) => ({
    type: 'point',
    label: l.label,
    icon: l.icon,
    text: props.descriptions[l.to] || `Раздел «${l.label}».`,
  })),
])

const isLast = computed(() => step.value === steps.value.length - 1)
const current = computed(() => steps.value[step.value])

function measureTarget() {
  if (current.value.type !== 'point') {
    targetRect.value = null
    return
  }
  const idx = step.value - 1
  const el = document.querySelectorAll('.sidebar .side-link')[idx]
  if (!el) {
    targetRect.value = null
    return
  }
  const r = el.getBoundingClientRect()
  targetRect.value = { top: r.top, left: r.left, right: r.right, width: r.width, height: r.height }
}

function next() {
  if (isLast.value) {
    finish()
    return
  }
  step.value += 1
  nextTick(measureTarget)
}

function finish() {
  visible.value = false
  localStorage.setItem(storageKey.value, '1')
}

function handleResize() {
  measureTarget()
}

onMounted(() => {
  if (!auth.user) return
  if (!DEV_ALWAYS_SHOW && localStorage.getItem(storageKey.value)) return
  visible.value = true
  nextTick(measureTarget)
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
})

const bubbleStyle = computed(() => {
  if (!targetRect.value) return {}
  const r = targetRect.value
  const top = Math.max(16, Math.min(r.top - 6, window.innerHeight - 220))
  return { top: `${top}px`, left: `${r.right + 18}px` }
})

const highlightStyle = computed(() => {
  if (!targetRect.value) return { opacity: 0 }
  const r = targetRect.value
  return {
    top: `${r.top - 6}px`,
    left: `${r.left - 6}px`,
    width: `${r.width + 12}px`,
    height: `${r.height + 12}px`,
    opacity: 1,
  }
})
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="tour-root">
      <div class="tour-backdrop"></div>
      <div class="tour-highlight" :style="highlightStyle"></div>

      <Transition name="tour-fade" mode="out-in">
        <div v-if="current.type === 'welcome'" key="welcome" class="tour-card tour-card--center">
          <WaveMascot :size="150" class="tour-wave" />
          <h3>Привет! Рады видеть вас в COURSE</h3>
          <p>
            Слева — ваше меню: тренинги, тесты, чаты и новости. Быстро покажем,
            что где находится, — это займёт полминуты.
          </p>
          <p class="tour-once-note">
            Это приветствие показывается только один раз — при первом входе.
          </p>
          <button class="tour-next" @click="next">Далее →</button>
        </div>

        <div v-else :key="step" class="tour-card tour-card--point" :style="bubbleStyle">
          <span class="tour-step-count">Шаг {{ step }} из {{ steps.length - 1 }}</span>
          <h4><span class="tour-icon">{{ current.icon }}</span>{{ current.label }}</h4>
          <p>{{ current.text }}</p>
          <div class="tour-actions">
            <button class="tour-skip" @click="finish">Пропустить</button>
            <button class="tour-next" @click="next">{{ isLast ? 'Готово' : 'Далее →' }}</button>
          </div>
        </div>
      </Transition>
    </div>
  </Teleport>
</template>

<style scoped>
.tour-root {
  position: fixed;
  inset: 0;
  z-index: 9999;
}

.tour-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(11, 17, 32, 0.72);
}

:root[data-theme='light'] .tour-backdrop {
  background: rgba(30, 34, 51, 0.55);
}

.tour-highlight {
  position: fixed;
  border: 2px solid var(--gold);
  border-radius: 12px;
  box-shadow: 0 0 0 4px rgba(201, 166, 107, 0.18), 0 0 24px rgba(201, 166, 107, 0.35);
  pointer-events: none;
  transition: top 0.4s cubic-bezier(0.16, 1, 0.3, 1), left 0.4s cubic-bezier(0.16, 1, 0.3, 1),
    width 0.4s cubic-bezier(0.16, 1, 0.3, 1), height 0.4s cubic-bezier(0.16, 1, 0.3, 1),
    opacity 0.3s ease;
}

.tour-card {
  position: fixed;
  width: 300px;
  background: var(--navy);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 22px;
  box-shadow: 0 24px 60px -16px rgba(0, 0, 0, 0.55);
}

.tour-card--center {
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 340px;
  text-align: center;
}

.tour-wave {
  margin: 0 auto 6px;
}

.tour-once-note {
  margin-top: 10px;
  font-size: 11.5px;
  color: var(--text-dim);
}

.tour-card h3 {
  font-size: 18px;
  color: var(--text-hi);
  margin-bottom: 10px;
}

.tour-card--point h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  color: var(--text-hi);
  margin: 6px 0 8px;
}

.tour-icon {
  color: var(--gold);
  font-size: 16px;
}

.tour-step-count {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-dim);
}

.tour-card p {
  font-size: 13.5px;
  color: var(--text-mid);
  line-height: 1.6;
}

.tour-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}

.tour-next {
  padding: 10px 18px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--gold), #b08d53);
  color: #1a1406;
  font-weight: 600;
  font-size: 13px;
  border: none;
}

.tour-card--center .tour-next {
  width: 100%;
  padding: 12px;
  margin-top: 18px;
}

.tour-skip {
  background: transparent;
  border: none;
  color: var(--text-dim);
  font-size: 12.5px;
}

.tour-skip:hover {
  color: var(--text-mid);
}

.tour-fade-enter-active,
.tour-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.tour-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.tour-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 720px) {
  .tour-card--point {
    left: 16px !important;
    right: 16px;
    width: auto;
    top: auto !important;
    bottom: 16px;
  }
}
</style>
