import { createRouter, createWebHistory } from "vue-router"
import AIConsole from "@/pages/AIConsole.vue"
import Advisor from "@/pages/Advisor.vue"
import QA from "@/pages/QA.vue"

const routes = [
  { path: "/", redirect: "/console" },
  { path: "/console", component: AIConsole },
  { path: "/advisor", component: Advisor },
  { path: "/qa", component: QA }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
