<script setup>
defineProps({ percent: { type: Number, default: 0 }, label: { type: String, default: '' } })
</script>

<template>
  <div>
    <div class="progress-bar"><span :style="{ width: percent + '%' }"></span></div>
    <div class="progress-label">{{ label }}</div>
  </div>
</template>
