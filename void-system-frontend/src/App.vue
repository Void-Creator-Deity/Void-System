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
          <NavItem to="/settings" icon="⚙️">系统设置</NavItem>
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
            <el-button class="cyber-btn-outline" @click="router.push('/login')">接入连接</el-button>
            <el-button class="cyber-btn-solid" @click="router.push('/register')">创建序列</el-button>
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

import { RouterLink, RouterView, useRouter } from 'vue-router'
import { ref, onMounted, computed, watch } from 'vue'
import { User, Setting, SwitchButton } from '@element-plus/icons-vue'
import { authState, logout as logoutApi } from '@/api/user'
import NavItem from '@/components/NavItem.vue'

const router = useRouter()

// ==================== 响应式状态 ====================
const isLoading = ref(false)
const showUserMenu = ref(false)

// 使用计算属性连接全局状态
const isAuthenticated = computed(() => authState.isLoggedIn)
const userName = computed(() => {
  const info = authState.userInfo
  if (!info) return '用户'
  return info.username || info.userName || info.user?.username || '用户'
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
  router.push('/settings')
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

// 组件挂载时加载用户信息
onMounted(() => {
  loadUserInfo()
})
</script>

<style scoped>
/* 系统初始化遮罩 */
.system-initializer {
  position: fixed;
  inset: 0;
  background: var(--color-bg-primary);
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
  margin-bottom: 2rem;
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
  background: var(--grad-cyber);
  border-radius: 50%;
  filter: blur(15px);
  opacity: 0.6;
  animation: pulse 2s ease-in-out infinite;
}

.initializer-text {
  font-family: var(--font-family-mono);
  color: var(--color-primary-light);
  letter-spacing: 4px;
}

/* 神经网络顶栏 (Neural Nexus) */
.system-header {
  height: 70px;
  position: sticky;
  top: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
}

.header-glass-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--color-border);
}

.header-content {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 品牌区域 */
.brand-area {
  display: flex;
  align-items: center;
  gap: 1rem;
  cursor: pointer;
  transition: transform 0.3s ease;
}

.brand-area:hover {
  transform: scale(1.02);
}

.brand-v-icon {
  width: 32px;
  height: 32px;
  background: var(--grad-cyber);
  clip-path: polygon(50% 0%, 100% 100%, 0% 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-glow);
}

.v-inner {
  width: 16px;
  height: 16px;
  background: var(--color-bg-primary);
  clip-path: polygon(50% 0%, 100% 100%, 0% 100%);
}

.brand-label {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: 1.2rem;
  font-weight: 900;
  letter-spacing: 2px;
  background: linear-gradient(to right, #fff, var(--color-primary-light));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-suffix {
  font-size: 0.6rem;
  font-weight: 300;
  color: var(--color-text-muted);
  letter-spacing: 4px;
}

/* 导航链接 */
.nav-links {
  display: flex;
  gap: 0.5rem;
}

/* 操作中枢 */
.central-ops {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.user-node {
  position: relative;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.4rem 0.4rem 0.4rem 1.2rem;
  border-radius: 2rem;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid var(--color-border-light);
}

.user-node:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--color-primary);
  box-shadow: 0 0 20px rgba(67, 97, 238, 0.2);
}

.user-info-text {
  display: flex;
  flex-direction: column;
  text-align: right;
}

.user-label {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--color-text-primary);
}

.user-rank {
  font-size: 0.7rem;
  color: var(--color-primary);
  font-family: var(--font-family-mono);
  font-weight: 700;
}

.user-hex-avatar {
  width: 38px;
  height: 38px;
  background: var(--grad-cyber);
  display: flex;
  align-items: center;
  justify-content: center;
  clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
  color: #fff;
  font-weight: 900;
}

/* 用户详情菜单 */
.user-ops-menu {
  position: absolute;
  top: calc(100% + 1rem);
  right: 0;
  width: 200px;
  padding: 0.5rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xl);
  z-index: 1001;
  transform-origin: top right;
  animation: slideDown 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition: all 0.2s ease;
  font-size: 0.9rem;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--color-text-primary);
  transform: translateX(4px);
}

.menu-item.logout {
  color: #ff4757;
}

.menu-item.logout:hover {
  background: rgba(255, 71, 87, 0.1);
}

.menu-divider {
  height: 1px;
  background: var(--color-border-light);
  margin: 0.4rem 0;
}

/* 主内容区域 */
.main {
  padding-top: 2rem;
  min-height: calc(100vh - 70px - 60px);
}

/* 全局动画 */
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.glitch-text {
  position: relative;
  display: inline-block;
}

/* 移动端适配 */
@media (max-width: 992px) {
  .nav-links {
    display: none;
  }
}

/* 按钮组件重载 */
.cyber-btn-outline {
  border: 1px solid var(--color-primary-light);
  background: transparent;
  color: var(--color-primary-light);
  border-radius: 2rem;
  font-weight: 700;
  padding: 0.5rem 1.5rem;
}

.cyber-btn-solid {
  background: var(--grad-cyber);
  border: none;
  color: #fff;
  border-radius: 2rem;
  font-weight: 700;
  padding: 0.5rem 1.5rem;
  box-shadow: var(--shadow-glow);
}

/* 统一底部 */
.footer {
  height: 60px;
  display: flex;
  align-items: center;
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-primary);
}

.copyright {
  font-family: var(--font-family-mono);
  font-size: 0.7rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  opacity: 0.5;
}
</style>
