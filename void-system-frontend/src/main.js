/**
 * Void System Frontend - Main Entry
 * -----------------------------------
 * Vue 3 应用入口文件
 */

import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import ElementPlus from "element-plus"
import "element-plus/dist/index.css"
import "./style.css"
import { setupAuthInterceptor } from "./api/user.js"

// 初始化认证拦截器（自动添加 token 到请求头）
setupAuthInterceptor()

// 添加系统初始化效果
document.addEventListener('DOMContentLoaded', () => {
  document.body.classList.add('system-loaded')
})

// 创建并挂载 Vue 应用
const app = createApp(App)

// 注册 Element Plus 图标
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

import { createPinia } from 'pinia'

// 创建 Pinia 实例
const pinia = createPinia()

app.use(pinia)   // 使用 Pinia
app.use(router)  // 使用路由
app.use(ElementPlus)  // 使用 Element Plus UI 组件库
app.mount("#app")
