<script setup>
import { onMounted, ref } from 'vue'
import Sidebar from '../../components/common/Sidebar.vue'
import { useNewsStore } from '../../store/news'
import { learnerLinks as links } from '../../nav'

const store = useNewsStore()
const openItem = ref(null)

onMounted(async () => {
  await store.fetchNews()
})

function formatDate(iso) {
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function excerpt(text) {
  if (!text) return ''
  return text.length > 140 ? text.slice(0, 140).trim() + '…' : text
}
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header"><div><h1>Новости</h1><p>Актуальные события и объявления</p></div></div>

        <div class="news-list">
          <div class="news-item" v-for="n in store.items" :key="n.id" @click="openItem = n">
            <div class="news-item-top">
              <h4>{{ n.title }}</h4>
              <span class="news-date">{{ formatDate(n.starts_at) }}</span>
            </div>
            <p class="news-excerpt" v-if="n.description">{{ excerpt(n.description) }}</p>
            <div class="news-item-bottom">
              <span class="badge" :class="n.course_title ? 'locked' : 'ok'">{{ n.course_title || 'Для всех' }}</span>
              <span v-if="n.link_url" class="badge" style="border-color:var(--gold); color:var(--gold);">Есть ссылка</span>
              <button class="news-more">Подробнее</button>
            </div>
          </div>
        </div>
        <p v-if="store.items.length === 0" style="color:var(--text-dim); margin-top:12px;">Новостей пока нет.</p>
      </div>
    </main>

    <div class="modal-overlay" :class="{ active: openItem }">
      <div class="modal" v-if="openItem">
        <h3>{{ openItem.title }}</h3>
        <p class="mod-sub">{{ formatDate(openItem.starts_at) }} · {{ openItem.course_title || 'Для всех' }}</p>
        <p class="news-full-text" v-if="openItem.description">{{ openItem.description }}</p>
        <p class="news-full-text" v-else style="color:var(--text-dim);">Без описания.</p>
        <p v-if="openItem.link_url"><a :href="openItem.link_url" target="_blank" rel="noopener" style="color:var(--gold);">{{ openItem.link_url }}</a></p>
        <div class="modal-footer">
          <button class="btn-primary" @click="openItem = null">Закрыть</button>
        </div>
      </div>
    </div>
  </div>
</template>
