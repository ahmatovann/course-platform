<script setup>
import { useUiStore } from '../../store/ui'
const ui = useUiStore()
</script>

<template>
  <div class="toast-container">
    <div v-for="t in ui.toasts" :key="t.id" :class="['toast', t.type]">{{ t.message }}</div>
  </div>
</template>
