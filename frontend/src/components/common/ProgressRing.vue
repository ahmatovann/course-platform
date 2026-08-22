<script setup>
import { computed } from 'vue'

// Круговая диаграмма прогресса (кольцо) — наглядное дополнение к линейным
// полоскам (.chart-bar-*): для сводной статистики ученика и аналитики по
// модулю. Чистый SVG, без сторонних библиотек — гарантированно видна.
const props = defineProps({
  percent: { type: Number, required: true },
  size: { type: Number, default: 120 },
  strokeWidth: { type: Number, default: 10 },
  label: { type: String, default: '' },
})

const clamped = computed(() => Math.max(0, Math.min(100, props.percent || 0)))
const radius = computed(() => 60 - props.strokeWidth)
const circumference = computed(() => 2 * Math.PI * radius.value)
const dashOffset = computed(() => circumference.value * (1 - clamped.value / 100))
</script>

<template>
  <div class="progress-ring" :style="{ width: size + 'px', height: size + 'px' }">
    <svg viewBox="0 0 120 120" :width="size" :height="size">
      <circle class="progress-ring-track" cx="60" cy="60" :r="radius" :stroke-width="strokeWidth" fill="none" />
      <circle
        class="progress-ring-fill" cx="60" cy="60" :r="radius" :stroke-width="strokeWidth" fill="none"
        stroke-linecap="round" :stroke-dasharray="circumference" :stroke-dashoffset="dashOffset"
        transform="rotate(-90 60 60)"
      />
    </svg>
    <div class="progress-ring-center">
      <strong>{{ Math.round(clamped) }}%</strong>
      <span v-if="label">{{ label }}</span>
    </div>
  </div>
</template>

<style scoped>
.progress-ring { position: relative; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.progress-ring svg { display: block; }
.progress-ring-track { stroke: var(--navy-deep); }
.progress-ring-fill { stroke: var(--gold); transition: stroke-dashoffset .6s ease; }
.progress-ring-center {
  position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; line-height: 1.25;
}
.progress-ring-center strong { font-size: 20px; color: var(--text-hi); font-family: var(--font-display); }
.progress-ring-center span { font-size: 10.5px; color: var(--text-dim); max-width: 74px; }
</style>
