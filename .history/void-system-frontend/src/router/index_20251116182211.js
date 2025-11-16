import { createRouter, createWebHistory } from 'vue-router'
import AIConsole from '@/pages/AIConsole.vue'
import Advisor from '@/pages/Advisor.vue'
import QA from '@/pages/QA.vue'

const routes = [
  { path: '/', component: AIConsole },
  { path: '/advisor', component: Advisor },
  { path: '/qa', component: QA },
  { path: '/settings', component: Settings },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
