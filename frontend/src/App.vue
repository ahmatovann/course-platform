<script setup>
import ToastContainer from './components/common/ToastContainer.vue'
</script>

<template>
  <ToastContainer />
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>
