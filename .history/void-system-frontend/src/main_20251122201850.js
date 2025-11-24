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
import { setupAuthInterceptor } from "./api/user.js"

// 初始化认证拦截器（自动添加 token 到请求头）
setupAuthInterceptor()

// 添加系统初始化效果
document.addEventListener('DOMContentLoaded', () => {
  document.body.classList.add('system-loaded')
})

// 创建并挂载 Vue 应用
const app = createApp(App)
app.use(router)  // 使用路由
app.use(ElementPlus)  // 使用 Element Plus UI 组件库
app.mount("#app")
