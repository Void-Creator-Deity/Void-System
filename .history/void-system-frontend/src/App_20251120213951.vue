<template>
  <div id="app">
    <!-- 加载遮罩 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading"></div>
      <div class="loading-text">系统初始化中...</div>
    </div>
    
    <!-- 主题切换按钮 -->
    <div class="theme-switcher">
      <button 
        v-for="theme in themes" 
        :key="theme.id"
        class="theme-btn"
        :class="{ active: currentTheme === theme.id }"
        :style="{ '--theme-color': theme.color }"
        @click="switchTheme(theme.id)"
        :title="theme.name"
      >
        <span class="theme-dot"></span>
        <span class="theme-name">{{ theme.name }}</span>
      </button>
    </div>
    
    <!-- 系统顶栏 -->
    <header class="header">
      <div class="container header-container">
        <div class="logo-area flex items-center gap-md">
          <div class="logo">
            <span class="logo-symbol">⟩</span>
          </div>
          <h1 class="system-title">
            <span class="title-void">VOID</span>
            <span class="title-system">SYSTEM</span>
          </h1>
        </div>
        <!-- 桌面端导航 -->
        <nav class="nav-links flex gap-md">
          <NavItem to="/" icon="🏠">首页</NavItem>
          <NavItem to="/ai" icon="⌨️">AI控制台</NavItem>
          <NavItem to="/advisor" icon="🧠">学习顾问</NavItem>
          <NavItem to="/qa" icon="❓">知识问答</NavItem>
          <NavItem to="/settings" icon="⚙️">系统设置</NavItem>
        </nav>
        
        <!-- 移动端菜单按钮 -->
        <button class="mobile-menu-btn" @click="toggleMobileMenu">
          <span class="menu-icon">☰</span>
        </button>
        
        <!-- 用户信息 -->
        <div class="user-area flex items-center gap-md">
          <!-- 通知中心 -->
          <div class="notification-center">
            <button class="notification-btn" @click="handleNotificationClick">
              <span class="notification-icon">🔔</span>
              <span v-if="notificationCount > 0" class="notification-badge">{{ notificationCount }}</span>
            </button>
          </div>
          
          <!-- 用户信息 -->
          <div class="user-profile flex items-center gap-sm">
            <div class="user-details">
              <div class="user-name">{{ userName }}</div>
              <div class="user-level">Lv.{{ userLevel }}</div>
            </div>
            <div class="user-avatar">
              <span>{{ userAvatar }}</span>
            </div>
            <button class="user-menu-btn" @click="toggleUserMenu">
              <span>▼</span>
            </button>
          </div>
          
          <!-- 用户下拉菜单 -->
          <div v-if="showUserMenu" class="user-dropdown">
            <div class="dropdown-item" @click="goToProfile">个人资料</div>
            <div class="dropdown-item" @click="goToSettings">系统设置</div>
            <div class="dropdown-divider"></div>
            <div class="dropdown-item logout" @click="logout">退出登录</div>
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
            © {{ new Date().getFullYear() }} VOID SYSTEM — Neural Intelligence Framework
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { ref, onMounted } from 'vue'

// 导航项组件
import { h } from 'vue'
const router = useRouter()

// 状态管理
const isLoading = ref(false)
const showUserMenu = ref(false)
const notificationCount = ref(3)
const userName = ref('学习者')
const userLevel = ref(1)
const userAvatar = ref('U')
const currentTheme = ref('default')

// 可用主题列表
const themes = [
  { id: 'default', name: '默认主题', color: '#4361ee' },
  { id: 'dark', name: '暗色主题', color: '#1e3a8a' }
]

// 导航项组件增强
const NavItem = (props, { slots }) => {
  return h(RouterLink,
    {
      to: props.to,
      class: 'nav-item',
      custom: true,
      vSlots: {
        default: ({ isActive }) => h('div',
          { 
            class: ['nav-link', isActive ? 'active' : ''],
            onClick: () => props.onClick && props.onClick()
          },
          [
            h('span', { class: 'nav-icon' }, props.icon),
            h('span', { class: 'nav-text' }, slots.default()),
            isActive ? h('div', { class: 'nav-indicator' }) : null
          ]
        )
      }
    }
  )
}
NavItem.props = ['to', 'icon', 'onClick']

// 方法定义
const switchTheme = (themeId) => {
  currentTheme.value = themeId
  // 更新body的data-theme属性
  if (themeId === 'default') {
    document.body.removeAttribute('data-theme')
  } else {
    document.body.setAttribute('data-theme', themeId)
  }
  // 保存到localStorage以便下次加载时使用
  localStorage.setItem('void-system-theme', themeId)
}

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

const handleNotificationClick = () => {
  // 处理通知点击逻辑
  notificationCount.value = 0
}

const goToProfile = () => {
  showUserMenu.value = false
  // 跳转到个人资料页面
}

const goToSettings = () => {
  showUserMenu.value = false
  router.push('/settings')
}

const logout = () => {
  showUserMenu.value = false
  // 处理退出登录逻辑
  router.push('/login')
}

// 生命周期钩子
onMounted(() => {
  // 从localStorage加载主题设置
  const savedTheme = localStorage.getItem('void-system-theme')
  if (savedTheme) {
    switchTheme(savedTheme)
  }
  
  // 模拟加载完成
  setTimeout(() => {
    isLoading.value = false
  }, 500)
})
</script>

<style scoped>
/* 加载遮罩 */
  .loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--color-bg-primary);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-lg);
    z-index: 9999;
  }

  .loading {
    width: 60px;
    height: 60px;
    border: 4px solid var(--color-bg-tertiary);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .loading-text {
    color: var(--color-text-primary);
    font-weight: 600;
    font-size: 1.125rem;
    color: var(--color-primary);
  }
/* 主题切换器 */
  .theme-switcher {
    position: fixed;
    top: var(--spacing-lg);
    right: var(--spacing-lg);
    z-index: 100;
    display: flex;
    gap: var(--spacing-sm);
    background-color: var(--color-bg-secondary);
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-lg);
    padding: var(--spacing-xs);
  }

  .theme-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-xs) var(--spacing-sm);
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--color-text-primary);
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .theme-btn:hover {
    background-color: var(--color-bg-tertiary);
  }

  .theme-btn.active {
    background-color: var(--color-bg-tertiary);
    border-color: var(--color-primary);
  }

.theme-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background-color: var(--theme-color);
  box-shadow: 0 0 8px var(--theme-color);
}

.theme-name {
  font-size: 0.875rem;
  font-weight: 500;
}

/* 顶栏样式 - 游戏化界面 */
.header {
  /* 顶栏容器布局 */
  .header-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  background-color: var(--color-bg-primary);
  background-image: linear-gradient(to right, transparent, rgba(67, 97, 238, 0.05), transparent);
  border-bottom: 1px solid var(--color-border-light);
  padding: var(--spacing-md) 0;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}

/* 顶栏样式 */
  .header {
    background-color: var(--color-bg-primary);
    border-bottom: 1px solid var(--color-border-light);
    padding: var(--spacing-md) 0;
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .logo-area {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .logo {
    width: 44px;
    height: 44px;
    border-radius: var(--radius-md);
    background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1.625rem;
    font-weight: bold;
  }

  .system-title {
    font-size: 1.375rem;
    font-weight: 700;
    display: flex;
    gap: var(--spacing-xs);
    margin: 0;
  }

  .title-void {
    color: var(--color-primary);
  }

  .title-system {
    color: var(--color-text-secondary);
    font-weight: 600;
  }

/* 导航样式 */
  .nav-links {
    display: flex;
    gap: var(--spacing-sm);
  }

  .nav-link {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-md);
    color: var(--color-text-secondary);
    text-decoration: none;
    border-radius: var(--radius-md);
    transition: all var(--transition-fast);
  }

  .nav-link:hover {
    background-color: var(--color-bg-secondary);
    color: var(--color-text-primary);
  }

  .nav-link.active {
    color: var(--color-primary);
    background-color: rgba(67, 97, 238, 0.08);
  }

  .nav-link.active .nav-indicator {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 2px;
    background: var(--color-primary);
    border-radius: var(--radius-full);
  }

  .nav-icon {
    font-size: 1.25rem;
  }

.nav-text {
  font-weight: 500;
}

/* 用户区域 */
  .user-area {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .notification-btn {
    position: relative;
    background: transparent;
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    padding: var(--spacing-sm);
    border-radius: var(--radius-md);
    transition: all var(--transition-fast);
  }

  .notification-btn:hover {
    background-color: var(--color-bg-secondary);
  }

.notification-badge {
    position: absolute;
    top: 2px;
    right: 2px;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    background: var(--color-error);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

.user-profile {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-xs);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .user-profile:hover {
    background-color: var(--color-bg-secondary);
  }

  .user-details {
    display: flex;
    flex-direction: column;
  }

  .user-name {
    font-weight: 500;
    color: var(--color-text-primary);
    font-size: 0.875rem;
  }

  .user-level {
    font-size: 0.75rem;
    color: var(--color-primary);
    font-weight: 600;
  }

  .user-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 1rem;
  }

.user-menu-btn {
  background: transparent;
  border: none;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: var(--spacing-xs);
  transition: all var(--transition-fast);
}

.user-menu-btn:hover {
  color: var(--color-text-primary);
  transform: translateY(1px);
}

/* 用户下拉菜单 */
  .user-dropdown {
    position: absolute;
    top: calc(100% + var(--spacing-sm));
    right: var(--spacing-md);
    background-color: var(--color-bg-secondary);
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    padding: var(--spacing-xs) 0;
    min-width: 180px;
    z-index: 101;
  }

  .user-dropdown::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--color-primary);
  }

  .dropdown-item {
    padding: var(--spacing-sm) var(--spacing-md);
    color: var(--color-text-primary);
    cursor: pointer;
    transition: all var(--transition-fast);
    font-size: 0.875rem;
  }

  .dropdown-item:hover {
    background-color: var(--color-bg-tertiary);
  }

.dropdown-divider {
  height: 1px;
  background-color: var(--color-border);
  margin: var(--spacing-xs) 0;
}

.dropdown-item.logout {
  color: var(--color-error);
  font-weight: 500;
}

.dropdown-item.logout:hover {
  background-color: rgba(239, 68, 68, 0.1);
}

/* 移动端菜单按钮 */
.mobile-menu-btn {
  display: none;
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: background-color var(--transition-fast);
}

.mobile-menu-btn:hover {
  background-color: var(--color-bg-secondary);
}

/* 主内容区 */
  .main {
    flex: 1;
    padding: var(--spacing-xl) 0;
    background-color: var(--color-bg-primary);
  }

/* 底部样式 */
  .footer {
    background-color: var(--color-bg-primary);
    border-top: 1px solid var(--color-border-light);
    padding: var(--spacing-lg) 0;
  }

.system-info {
  text-align: center;
}

/* 数据卡片样式 */
  .stat-card {
    background-color: var(--color-bg-secondary);
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    transition: all var(--transition-normal);
    box-shadow: var(--shadow-md);
  }

  .stat-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--color-primary);
  }

  .stat-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
  }

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: white;
  box-shadow: 0 0 15px rgba(67, 97, 238, 0.2);
  margin-bottom: var(--spacing-md);
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.stat-change {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.stat-change.positive {
  background-color: rgba(34, 197, 94, 0.1);
  color: var(--color-success);
}

.stat-change.negative {
  background-color: rgba(239, 68, 68, 0.1);
  color: var(--color-error);
}

/* 移动端导航覆盖 */
  .mobile-nav-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 200;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .mobile-nav {
    background-color: var(--color-bg-primary);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    width: 90%;
    max-width: 400px;
    max-height: 80vh;
    overflow-y: auto;
  }

.mobile-close-btn {
  position: absolute;
  top: var(--spacing-md);
  right: var(--spacing-md);
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-md);
  transition: background-color var(--transition-fast);
}

.mobile-close-btn:hover {
  background-color: var(--color-bg-secondary);
}

.mobile-nav-links {
  margin-top: var(--spacing-lg);
}

.mobile-nav-links .nav-link {
  padding: var(--spacing-md);
  font-size: 1.125rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .nav-links {
    display: none;
  }
  
  .mobile-menu-btn {
    display: block;
  }
  
  .logo {
    width: 40px;
    height: 40px;
    font-size: 1.5rem;
  }
  
  .system-title {
    font-size: 1.25rem;
  }
}

@media (max-width: 480px) {
  .logo-area {
    gap: var(--spacing-sm);
  }
  
  .system-title {
    font-size: 0.875rem;
  }
  
  .user-details {
    display: none;
  }
  
  .theme-switcher {
    top: var(--spacing-md);
    right: var(--spacing-md);
  }
  
  .theme-name {
    display: none;
  }
  
  .main {
    padding: var(--spacing-md) 0;
  }
  
  .stat-card {
    padding: var(--spacing-md);
  }
  
  .stat-icon {
    width: 40px;
    height: 40px;
    font-size: 1.25rem;
  }
  
  .stat-value {
    font-size: 1.5rem;
  }
  
  .header {
    padding: var(--spacing-sm) 0;
  }
  
  .logo {
    width: 32px;
    height: 32px;
    font-size: 1.25rem;
  }
  
  .notification-btn, .user-menu-btn {
    padding: var(--spacing-xs);
  }
}


/* 基础样式优化 */
  html {
    scroll-behavior: smooth;
  }

  ::selection {
    background-color: rgba(67, 97, 238, 0.2);
    color: var(--color-primary);
  }

  button:focus, 
  a:focus, 
  input:focus, 
  textarea:focus, 
  select:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
</style>
