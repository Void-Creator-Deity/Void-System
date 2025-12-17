/**
 * Void System Frontend - Router Configuration
 * --------------------------------------------
 * Vue Router 路由配置，包含路由守卫和权限控制
 */

import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from '@/api/user'

// 路由懒加载（按需加载组件，优化首屏加载速度）
const Home = () => import('@/pages/Home.vue')
const AIConsole = () => import('@/pages/AIConsole.vue')
const Advisor = () => import('@/pages/Advisor.vue')
const QA = () => import('@/pages/QA.vue')
const DocumentManager = () => import('@/pages/DocumentManager.vue')
const Settings = () => import('@/pages/Settings.vue')
const Login = () => import('@/pages/Login.vue')
const Register = () => import('@/pages/Register.vue')
const RAGManagement = () => import('@/pages/RAGManagement.vue')

// 获取存储的用户信息
const getUserInfo = () => {
  const userInfo = localStorage.getItem('user_info')
  return userInfo ? JSON.parse(userInfo) : null
}

// 检查用户是否是管理员
const isAdmin = () => {
  const userInfo = getUserInfo()
  return userInfo?.user?.role === 'admin'
}

/**
 * 路由配置
 */
const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { 
      requiresAuth: true,
      title: '系统终端'
    }
  },
  {
    path: '/ai',
    name: 'AIConsole',
    component: AIConsole,
    meta: { 
      requiresAuth: true,
      title: '系统精灵'
    }
  },
  {
    path: '/advisor',
    name: 'Advisor',
    component: Advisor,
    meta: { 
      requiresAuth: true,
      title: '任务系统'
    }
  },
  {
    path: '/qa',
    name: 'QA',
    component: QA,
    meta: {
      requiresAuth: true,
      title: '虚空知识库'
    }
  },
  {
    path: '/documents',
    name: 'DocumentManager',
    component: DocumentManager,
    meta: {
      requiresAuth: true,
      title: '文档管理'
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    meta: { 
      requiresAuth: true,
      title: '系统设置'
    }
  },
  {
    path: '/admin/rag',
    name: 'RAGManagement',
    component: RAGManagement,
    meta: { 
      requiresAuth: true,
      requiresAdmin: true,
      title: 'RAG文档管理'
    }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { 
      requiresAuth: false,
      title: '登录'
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { 
      requiresAuth: false,
      title: '注册'
    }
  },
  // 404 页面重定向
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

/**
 * 创建路由实例
 */
const router = createRouter({
  history: createWebHistory(),
  routes
})

/**
 * 路由守卫
 * 处理认证和权限控制
 */
router.beforeEach((to, from, next) => {
  const requiresAuth = to.meta.requiresAuth !== false
  const requiresAdmin = to.meta.requiresAdmin === true
  
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - Void System`
  }
  
  if (requiresAuth && !isLoggedIn()) {
    // 需要登录但未登录，重定向到登录页
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && isLoggedIn()) {
    // 已登录用户访问登录/注册页，重定向到首页
    next('/')
  } else if (requiresAdmin && !isAdmin()) {
    // 需要管理员权限但不是管理员，重定向到首页
    next('/')
  } else {
    next()
  }
})

export default router
