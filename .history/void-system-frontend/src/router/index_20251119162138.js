import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/pages/Home.vue'
import AIConsole from '@/pages/AIConsole.vue'
import Advisor from '@/pages/Advisor.vue'
import QA from '@/pages/QA.vue'
import Settings from '@/pages/Settings.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/console', component: AIConsole },
  { path: '/advisor', component: Advisor },
  { path: '/qa', component: QA },
  { path: '/settings', component: Settings },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
