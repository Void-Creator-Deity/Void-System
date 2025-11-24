import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from '@/api/user'

// 路由懒加载
const Home = () => import('@/pages/Home.vue')
const AIConsole = () => import('@/pages/AIConsole.vue')
const Advisor = () => import('@/pages/Advisor.vue')
const QA = () => import('@/pages/QA.vue')
const Settings = () => import('@/pages/Settings.vue')
const Login = () => import('@/pages/Login.vue')
const Register = () => import('@/pages/Register.vue')

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: true }
  },
  {
    path: '/ai',
    name: 'AIConsole',
    component: AIConsole,
    meta: { requiresAuth: true }
  },
  {
    path: '/advisor',
    name: 'Advisor',
    component: Advisor,
    meta: { requiresAuth: true }
  },
  {
    path: '/qa',
    name: 'QA',
    component: QA,
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false }
  },
  // 404页面
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const requiresAuth = to.meta.requiresAuth !== false
  
  if (requiresAuth && !isLoggedIn()) {
    // 需要登录但未登录，重定向到登录页
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && isLoggedIn()) {
    // 已登录用户访问登录/注册页，重定向到首页
    next('/')
  } else {
    next()
  }
})

export default router
