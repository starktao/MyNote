import { createRouter, createWebHashHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import SettingsPage from '../pages/SettingsPage.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/settings', name: 'settings', component: SettingsPage },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

export default router
