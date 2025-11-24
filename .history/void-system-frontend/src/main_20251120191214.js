import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import ElementPlus from "element-plus"
import "element-plus/dist/index.css"
import { setupAuthInterceptor } from "./api/user.js"
import "./assets/global.css"

// 初始化认证拦截器
setupAuthInterceptor()

// 添加系统初始化效果
document.addEventListener('DOMContentLoaded', () => {
  document.body.classList.add('system-loaded')
})

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount("#app")
