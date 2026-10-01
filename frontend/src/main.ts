import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { registerSW } from 'virtual:pwa-register'
import App from './App.vue'
import AppShell from './views/AppShell.vue'
import './styles/base.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/list/pending' },
    { path: '/list/:id', component: AppShell },
    { path: '/:rest(.*)*', redirect: '/list/pending' },
  ],
})

registerSW({ immediate: true })

createApp(App).use(createPinia()).use(router).mount('#app')
