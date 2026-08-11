<script setup>
import Sidebar from '../../components/common/Sidebar.vue'
import { useUiStore } from '../../store/ui'
import { adminLinks as links } from '../../nav'

const ui = useUiStore()
</script>

<template>
  <div class="app active">
    <Sidebar :links="links" />
    <main class="main">
      <div class="view active">
        <div class="main-header"><div><h1>Настройки</h1><p>Оформление и параметры кабинета</p></div></div>
        <div class="mini-card" style="max-width:460px;">
          <h4>Настройки</h4>
          <div class="settings-row">
            <div class="lbl">Оформление<small>Тёмная или светлая тема интерфейса</small></div>
            <div class="settings-switch">
              <button type="button" :class="{ active: ui.theme === 'dark' }" @click="ui.setTheme('dark')">Тёмная</button>
              <button type="button" :class="{ active: ui.theme === 'light' }" @click="ui.setTheme('light')">Светлая</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
