<template>
  <div id="app">
    <!-- 系统初始化遮罩 (虚空觉醒) -->
    <div v-if="isLoading" class="system-initializer">
      <div class="initializer-core">
        <div class="core-orbit"></div>
        <div class="core-glow"></div>
      </div>
      <div class="initializer-text">
        <span class="glitch-text" data-text="INITIALIZING_VOID_CORE...">INITIALIZING_VOID_CORE...</span>
      </div>
    </div>
    
    <!-- 系统顶栏 -->
    <header class="system-header">
      <div class="header-glass-backdrop"></div>
      <div class="container header-content">
        <div class="brand-area" @click="router.push('/')">
          <div class="brand-v-icon">
            <div class="v-inner"></div>
          </div>
          <div class="brand-label">
            <span class="brand-name">VOID</span>
            <span class="brand-suffix">CORE 2.0</span>
          </div>
        </div>
        <!-- 桌面端导航 -->
        <nav class="nav-links flex gap-md">
          <NavItem to="/" icon="🏠">系统终端</NavItem>
          <NavItem to="/ai" icon="⌨️">系统精灵</NavItem>
          <NavItem to="/advisor" icon="🧠">任务系统</NavItem>
          <NavItem to="/qa" icon="❓">虚空知识库</NavItem>
          <NavItem to="/documents" icon="📄">文档管理</NavItem>
          <!-- 仅管理员可见 -->
          <NavItem v-if="isAdmin" to="/admin/rag" icon="🔧">RAG管理</NavItem>
        </nav>
        
        <!-- 操作中枢 (用户交互区) -->
        <div class="central-ops">
          <div v-if="isAuthenticated" class="user-node card-glass" @click="toggleUserMenu">
            <div class="user-info-text">
              <span class="user-label">{{ userName }}</span>
              <span class="user-rank">等级: {{ userLevel }}</span>
            </div>
            <div class="user-hex-avatar">
              <span class="avatar-char">{{ userAvatar }}</span>
            </div>
            
            <transition name="dropdown">
              <div v-if="showUserMenu" class="user-ops-menu card-glass">
                <div class="menu-item" @click="goToProfile">
                  <el-icon><User /></el-icon> 个人资料
                </div>
                <div class="menu-item" @click="goToSettings">
                  <el-icon><Setting /></el-icon> 系统设置
                </div>
                <div class="menu-divider"></div>
                <div class="menu-item logout" @click="logout">
                  <el-icon><SwitchButton /></el-icon> 断开连接
                </div>
              </div>
            </transition>
          </div>
          
          <div v-else-if="!isLoading" class="auth-gate flex gap-sm">
            <el-button class="void-btn" @click="router.push('/login')">接入连接</el-button>
            <el-button class="void-btn primary" @click="router.push('/register')">创建序列</el-button>
          </div>
        </div>
      </div>
    </header>

    <!-- 主界面内容区 -->
    <main class="main">
      <div class="container">
        <RouterView />
      </div>
    </main>

    <!-- 底部系统信息栏 -->
    <footer class="footer">
      <div class="container">
        <div class="system-info">
          <div class="copyright text-center text-sm text-muted">
            © {{ new Date().getFullYear() }} VOID SYSTEM — 虚空系统架构
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
/**
 * App Component - Main Application Container
 * ------------------------------------------
 * 主应用组件，包含导航栏、用户认证状态管理和全局布局
 */

import { RouterLink, RouterView, useRouter, useRoute } from 'vue-router'
import { ref, onMounted, computed, watch } from 'vue'
import { User, Setting, SwitchButton } from '@element-plus/icons-vue'
import { authState, logout as logoutApi } from '@/api/user'
import NavItem from '@/components/NavItem.vue'

const router = useRouter()
const route = useRoute()

// ==================== 响应式状态 ====================
const isLoading = ref(false)
const showUserMenu = ref(false)

// 使用计算属性连接全局状态
const isAuthenticated = computed(() => authState.isLoggedIn)
const userName = computed(() => {
  const info = authState.userInfo
  if (!info) return '用户'
  // 优先显示昵称 (档案代号)
  return info.username || info.user?.username || info.username || info.userName || info.user?.username || '用户'
})
const userLevel = computed(() => {
  const info = authState.userInfo
  if (!info) return 1
  return info.level || info.userLevel || info.user?.level || 1
})
const userAvatar = computed(() => userName.value.charAt(0).toUpperCase())
const isAdmin = computed(() => {
  const info = authState.userInfo
  return info?.user?.role === 'admin' || info?.role === 'admin'
})

// ==================== 业务逻辑 ====================

/**
 * 加载用户信息（初次挂载）
 */
const loadUserInfo = async () => {
  // 如果已经通过 reactive 初始化了，这里主要是为了处理可能的 loading 状态
  isLoading.value = true
  try {
    // 可以在这里调用 getCurrentUser 同步最新的用户信息
  } catch (error) {
    console.error('获取用户信息失败:', error)
  } finally {
    isLoading.value = false
  }
}

/**
 * 切换用户下拉菜单
 */
const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

/**
 * 跳转到个人资料页面
 */
const goToProfile = () => {
  showUserMenu.value = false
  router.push('/profile')
}

/**
 * 跳转到系统设置页面
 */
const goToSettings = () => {
  showUserMenu.value = false
  router.push('/settings')
}

/**
 * 用户登出
 */
const logout = async () => {
  showUserMenu.value = false
  try {
    // 调用登出 API（内部会处理状态更新）
    await logoutApi()
    
    // 跳转到登录页
    router.push('/login')
  } catch (error) {
    console.error('退出登录失败:', error)
    router.push('/login')
  }
}

// ==================== 生命周期 ====================

// 组件挂载时加载用户信息及本地主题配置
onMounted(() => {
  loadUserInfo()

  // 读取本地缓存的系统设置，应用主题模式
  try {
    const savedSettings = localStorage.getItem('settings_cache')
    if (savedSettings) {
      const parsed = JSON.parse(savedSettings)
      const themeMode = parsed?.systemConfig?.themeMode || 'dark'
      document.documentElement.setAttribute('data-theme', themeMode)
    } else {
      // 默认主题
      document.documentElement.setAttribute('data-theme', 'dark')
    }
  } catch(e) {
    console.warn('Failed to load local theme settings', e)
    document.documentElement.setAttribute('data-theme', 'dark')
  }
})
</script>

<style scoped>
/* Initializer Overlay */
.system-initializer {
  position: fixed;
  inset: 0;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.initializer-core {
  position: relative;
  width: 80px;
  height: 80px;
  margin-bottom: var(--spacing-xl);
}

.core-orbit {
  position: absolute;
  inset: -10px;
  border: 2px solid var(--color-primary);
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 2s linear infinite;
}

.core-glow {
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, var(--color-primary), transparent 70%);
  border-radius: 50%;
  opacity: 0.3;
  animation: pulse 2s ease-in-out infinite;
}

.initializer-text {
  font-family: var(--font-family-mono);
  color: var(--color-primary);
  letter-spacing: 4px;
}

/* Header */
.system-header {
  height: 64px;
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--bg-glass);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
}

.header-content {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand-area {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.brand-name {
  font-weight: 800;
  font-size: 1.2rem;
  letter-spacing: 1px;
}

/* Nav */
.nav-links {
  display: flex;
  gap: var(--spacing-md);
}

.central-ops {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

/* User Menu */
.user-node {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 6px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.user-node:hover {
  border-color: var(--color-primary);
}

.avatar-char {
  width: 32px;
  height: 32px;
  background: var(--color-primary);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.user-ops-menu {
  position: absolute;
  top: 50px;
  right: 0;
  width: 180px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-xs);
  z-index: 1001;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.menu-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.menu-divider {
  height: 1px;
  background: var(--border-color-light);
  margin: 4px 0;
}

/* Main & Footer */
.main {
  min-height: calc(100vh - 120px);
  padding: var(--spacing-xl) 0;
}

.footer {
  height: 56px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.copyright {
  font-size: 0.8rem;
  color: var(--text-muted);
}

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 0.6; } }

@media (max-width: 900px) {
  .nav-links { display: none; }
}
</style>
