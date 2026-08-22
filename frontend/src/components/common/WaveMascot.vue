<script setup>
// Персонаж-приветствие (используется на экране входа и в первом шаге
// обучающего тура).
defineProps({
  src: { type: String, default: '/wave-hello-transparent.webp' },
  size: { type: Number, default: 180 },
  // Когда true — картинка «отпускается»: плавно уезжает и растворяется
  // (используется при успешном входе, когда экран логина уходит).
  released: { type: Boolean, default: false },
})
</script>

<template>
  <div class="wave-mascot" :class="{ released }" :style="{ width: size + 'px' }">
    <img :src="src" alt="Здравствуйте!">
  </div>
</template>

<style scoped>
.wave-mascot { display: block; margin: 0 auto; }
.wave-mascot img {
  width: 100%; height: auto; display: block;
  transition: transform .15s ease-out, opacity .4s ease, margin-top .4s ease;
  will-change: transform;
  filter: drop-shadow(0 10px 22px rgba(0, 0, 0, .35));
}
.wave-mascot.released img { opacity: 0; margin-top: -18px; }
</style>
