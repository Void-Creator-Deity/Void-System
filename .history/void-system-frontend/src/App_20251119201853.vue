<template>
  <div id="app" class="void-app">
    <!-- 加载遮罩 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
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
    <header class="void-header">
      <div class="logo-area">
        <div class="logo">
          <div class="logo-symbol">⟩</div>
        </div>
        <h1 class="system-title">
          <span class="title-void">VOID</span>
          <span class="title-system">SYSTEM</span>
        </h1>
        <!-- 系统状态指示器 -->
        <div class="system-status-mini">
          <div class="status-dot"></div>
          <span>系统运行中</span>
        </div>
      </div>
      
      <!-- 桌面端导航 -->
      <nav class="nav-links">
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
      
      <!-- 用户信息和功能区 -->
      <div class="user-area">
        <!-- 通知中心 -->
        <div class="notification-center">
          <button class="notification-btn" @click="handleNotificationClick">
            <span class="notification-icon">🔔</span>
            <span v-if="notificationCount > 0" class="notification-badge">{{ notificationCount }}</span>
          </button>
        </div>
        
        <!-- 用户信息 -->
        <div class="user-profile">
          <div class="user-details">
            <div class="user-name">{{ userName }}</div>
            <div class="user-level">Lv.{{ userLevel }}</div>
          </div>
          <div class="user-avatar">
            <span>{{ userAvatar }}</span>
          </div>
          <div class="user-menu">
            <button class="user-menu-btn" @click="toggleUserMenu">
              <span>▼</span>
            </button>
            <div v-if="showUserMenu" class="user-dropdown">
              <div class="dropdown-item" @click="goToProfile">个人资料</div>
              <div class="dropdown-item" @click="goToSettings">系统设置</div>
              <div class="dropdown-divider"></div>
              <div class="dropdown-item logout" @click="logout">退出登录</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 移动端导航菜单 -->
      <div v-if="showMobileMenu" class="mobile-nav-overlay">
        <div class="mobile-nav">
          <button class="mobile-close-btn" @click="toggleMobileMenu">×</button>
          <div class="mobile-nav-links">
            <NavItem to="/" icon="🏠" @click="toggleMobileMenu">首页</NavItem>
            <NavItem to="/ai" icon="⌨️" @click="toggleMobileMenu">AI控制台</NavItem>
            <NavItem to="/advisor" icon="🧠" @click="toggleMobileMenu">学习顾问</NavItem>
            <NavItem to="/qa" icon="❓" @click="toggleMobileMenu">知识问答</NavItem>
            <NavItem to="/settings" icon="⚙️" @click="toggleMobileMenu">系统设置</NavItem>
          </div>
        </div>
      </div>
    </header>

    <!-- 主界面内容区 -->
    <main class="void-main">
      <!-- 背景装饰 -->
      <div class="background-effects">
        <div class="background-grid"></div>
        <div class="background-glow"></div>
      </div>
      
      <!-- 内容容器 -->
      <div class="content-wrapper">
        <RouterView />
      </div>
    </main>

    <!-- 底部系统信息栏 -->
    <footer class="void-footer">
      <div class="system-info">
        <div class="energy-bar">
          <div class="energy-level"></div>
        </div>
        <div class="system-metrics">
          <span class="metric">核心温度: 32°C</span>
          <span class="metric">内存使用: 67%</span>
          <span class="metric">处理速度: 1.2 TFLOPS</span>
        </div>
        <div class="copyright">
          <span class="timestamp">[2025-11-20 14:30:45]</span>
          <span>© 2025 VOID CORE — Neural Intelligence Framework</span>
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
const showMobileMenu = ref(false)
const showUserMenu = ref(false)
const notificationCount = ref(3)
const userName = ref('学习者')
const userLevel = ref(1)
const userAvatar = ref('U')
const currentTheme = ref('default')

// 可用主题列表
const themes = [
  { id: 'default', name: '虚空蓝', color: '#00ffcc' },
  { id: 'light', name: '星际白', color: '#0077cc' },
  { id: 'purple', name: '科技紫', color: '#cc66ff' },
  { id: 'cyber', name: '赛博绿', color: '#00ff66' }
]

// 导航项组件增强
const NavItem = (props, { slots, emit }) => {
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
  // 播放主题切换动画
  playThemeSwitchAnimation()
}

const playThemeSwitchAnimation = () => {
  const app = document.getElementById('app')
  app.classList.add('theme-transition')
  setTimeout(() => {
    app.classList.remove('theme-transition')
  }, 500)
}

const toggleMobileMenu = () => {
  showMobileMenu.value = !showMobileMenu.value
  // 点击外部关闭菜单
  if (showMobileMenu.value) {
    document.addEventListener('click', closeMobileMenuOnOutsideClick)
  } else {
    document.removeEventListener('click', closeMobileMenuOnOutsideClick)
  }
}

const closeMobileMenuOnOutsideClick = (event) => {
  const menu = document.querySelector('.mobile-nav')
  const btn = document.querySelector('.mobile-menu-btn')
  if (menu && btn && !menu.contains(event.target) && !btn.contains(event.target)) {
    showMobileMenu.value = false
    document.removeEventListener('click', closeMobileMenuOnOutsideClick)
  }
}

const toggleUserMenu = (event) => {
  event.stopPropagation()
  showUserMenu.value = !showUserMenu.value
  // 点击外部关闭菜单
  if (showUserMenu.value) {
    document.addEventListener('click', closeUserMenuOnOutsideClick)
  } else {
    document.removeEventListener('click', closeUserMenuOnOutsideClick)
  }
}

const closeUserMenuOnOutsideClick = (event) => {
  const menu = document.querySelector('.user-dropdown')
  const btn = document.querySelector('.user-menu-btn')
  if (menu && btn && !menu.contains(event.target) && !btn.contains(event.target)) {
    showUserMenu.value = false
    document.removeEventListener('click', closeUserMenuOnOutsideClick)
  }
}

const goToProfile = () => {
  showUserMenu.value = false
  // 由于没有专门的个人资料页面，显示提示信息
  alert('个人资料功能即将上线，敬请期待！')
  // 暂时不跳转
}

const goToSettings = () => {
  showUserMenu.value = false
  router.push('/settings')
}

const handleNotificationClick = () => {
  // 通知中心功能提示
  alert('通知中心功能即将上线，敬请期待！')
  // 暂时不实现具体功能
}

const logout = () => {
  showUserMenu.value = false
  // 调用logout API函数
  import('@/api/user').then(({ logout: logoutApi }) => {
    logoutApi()
      .then(() => {
        // 清除本地存储的用户信息
        localStorage.removeItem('userInfo')
        localStorage.removeItem('token')
        // 跳转到登录页面
        router.push('/login')
      })
      .catch((error) => {
        console.error('退出登录失败:', error)
        // 即使失败也要清理状态并跳转
        localStorage.removeItem('userInfo')
        localStorage.removeItem('token')
        router.push('/login')
      })
  })
}

// 页面加载状态处理
const startLoading = () => {
  isLoading.value = true
}

const endLoading = () => {
  isLoading.value = false
}

// 监听路由变化，处理页面切换动画
router.beforeEach((to, from, next) => {
  startLoading()
  setTimeout(() => {
    next()
  }, 300) // 添加页面切换延迟，提升体验
})

router.afterEach(() => {
  setTimeout(() => {
    endLoading()
  }, 300)
})

// 组件挂载时初始化
onMounted(() => {
  // 从localStorage加载保存的主题
  const savedTheme = localStorage.getItem('void-system-theme')
  if (savedTheme && themes.some(t => t.id === savedTheme)) {
    switchTheme(savedTheme)
  }
  
  // 这里可以添加初始化逻辑，如从后端获取用户信息等
  console.log('系统初始化完成')
  
  // 模拟从后端加载用户数据
  fetchUserData()
})

// 模拟从后端获取用户数据
const fetchUserData = async () => {
  try {
    // 在实际应用中，这里会是一个API调用
    // const response = await axios.get('/api/user/profile')
    // const userData = response.data
    
    // 模拟延迟
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 模拟数据
    userName.value = '学习者'
    userLevel.value = 1
    userAvatar.value = 'U'
    notificationCount.value = 3
    
    console.log('用户数据加载完成')
  } catch (error) {
    console.error('加载用户数据失败:', error)
    // 错误处理
  }
}
</script>

<style scoped>
.void-app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-primary), var(--bg-secondary));
  color: var(--text-primary);
  font-family: var(--body-font);
  overflow: hidden;
  position: relative;
  transition: background-color var(--transition-theme) ease;
}

/* 主题切换动画 */
.theme-transition {
  animation: themeFlash 0.5s ease-out;
}

@keyframes themeFlash {
  0% { opacity: 1; }
  50% { opacity: 0.95; }
  100% { opacity: 1; }
}

/* 主题切换器样式 */
.theme-switcher {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  display: flex;
  gap: 0.5rem;
  z-index: 999;
  flex-direction: column;
  align-items: flex-end;
}

.theme-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.85rem;
  box-shadow: 0 2px 10px var(--shadow-color);
  opacity: 0.7;
  backdrop-filter: blur(10px);
}

.theme-btn:hover {
  opacity: 1;
  transform: translateY(-2px);
  box-shadow: 0 4px 15px var(--shadow-color);
  border-color: var(--border-hover);
}

.theme-btn.active {
  opacity: 1;
  border-color: var(--theme-color);
  background: rgba(0, 0, 0, 0.2);
  box-shadow: 0 0 15px var(--theme-color);
}

.theme-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: var(--theme-color);
  border: 2px solid var(--bg-tertiary);
  box-shadow: 0 0 8px var(--theme-color);
}

.theme-name {
  font-family: var(--main-font);
  font-size: 0.8rem;
  letter-spacing: 0.5px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .theme-switcher {
    bottom: 1rem;
    right: 1rem;
  }
  
  .theme-name {
    display: none;
  }
  
  .theme-btn {
    padding: 0.5rem;
  }
}

/* 加载遮罩 */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(5, 7, 20, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  backdrop-filter: blur(5px);
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 3px solid rgba(0, 136, 255, 0.3);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  box-shadow: 0 0 20px var(--accent-glow);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 1rem;
  font-family: var(--main-font);
  color: var(--accent-primary);
  font-size: 1.1rem;
  animation: pulse 2s ease-in-out infinite;
}

/* 顶部导航 */
.void-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: linear-gradient(180deg, rgba(5, 7, 20, 0.95), rgba(5, 7, 20, 0.7));
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(10px);
  position: relative;
  z-index: 100;
}

/* Logo区域 */
.logo-area {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 20px var(--accent-glow), inset 0 0 10px rgba(255, 255, 255, 0.2);
  animation: float 4s ease-in-out infinite;
  transition: transform 0.5s ease;
}

.logo:hover {
  transform: rotate(12deg) scale(1.15);
}

.logo-symbol {
  font-size: 2rem;
  font-weight: bold;
  color: var(--bg-primary);
  font-family: var(--main-font);
}

.system-title {
  display: flex;
  gap: 0.5rem;
  font-size: 1.6rem;
  margin: 0;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
  background: linear-gradient(90deg, #ffffff, #e0e0ff);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  animation: glowText 3s infinite alternate;
}

@keyframes glowText {
  0% { text-shadow: 0 0 6px rgba(255, 255, 255, 0.3); }
  100% { text-shadow: 0 0 15px rgba(255, 255, 255, 0.6); }
}

/* 迷你系统状态指示器 */
.system-status-mini {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  background: rgba(0, 136, 255, 0.1);
  padding: 0.25rem 0.75rem;
  border-radius: 15px;
  border: 1px solid rgba(0, 136, 255, 0.2);
}

.status-dot {
  width: 8px;
  height: 8px;
  background-color: #00ff66;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

/* 桌面端导航链接 */
.nav-links {
  display: flex;
  gap: 0.5rem;
}

.nav-item {
  text-decoration: none;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border: 1px solid transparent;
  border-radius: 4px;
  transition: all var(--transition-fast) ease;
  position: relative;
  overflow: hidden;
  background: rgba(10, 13, 32, 0.7);
  color: var(--text-secondary);
  cursor: pointer;
}

.nav-link:hover {
  background: rgba(16, 21, 48, 0.9);
  border-color: var(--accent-primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  color: var(--text-primary);
}

.nav-link.active {
  background: linear-gradient(135deg, rgba(0, 136, 255, 0.2), rgba(0, 204, 255, 0.1));
  border-color: var(--accent-primary);
  box-shadow: 0 0 15px var(--accent-glow);
  color: var(--accent-primary);
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--accent-primary);
  animation: pulse 2s ease-in-out infinite;
}

.nav-icon {
  font-size: 1.1rem;
}

.nav-text {
  font-family: var(--main-font);
  font-size: 0.95rem;
  letter-spacing: 0.5px;
}

/* 移动端菜单按钮 */
.mobile-menu-btn {
  display: none;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  transition: all 0.3s ease;
}

.mobile-menu-btn:hover {
  color: var(--accent-primary);
  transform: scale(1.1);
}

/* 用户区域 */
.user-area {
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* 通知中心 */
.notification-center {
  position: relative;
}

.notification-btn {
  background: rgba(10, 13, 32, 0.7);
  border: 1px solid transparent;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.notification-btn:hover {
  background: rgba(16, 21, 48, 0.9);
  border-color: var(--accent-primary);
  color: var(--text-primary);
  transform: scale(1.1);
}

.notification-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: var(--accent-primary);
  color: white;
  font-size: 0.7rem;
  font-weight: bold;
  border-radius: 50%;
  min-width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
}

/* 用户资料 */
.user-profile {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  position: relative;
}

.user-details {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.user-name {
  font-family: var(--main-font);
  font-size: 0.9rem;
  color: var(--text-primary);
  font-weight: 500;
}

.user-level {
  font-size: 0.7rem;
  color: var(--accent-primary);
  background: rgba(0, 136, 255, 0.1);
  padding: 0.1rem 0.5rem;
  border-radius: 10px;
  border: 1px solid rgba(0, 136, 255, 0.2);
}

.user-avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary));
  border: 1px solid var(--border-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--main-font);
  font-weight: bold;
  color: var(--text-primary);
  transition: all 0.3s ease;
}

.user-avatar:hover {
  border-color: var(--accent-primary);
  transform: scale(1.05);
}

/* 用户菜单 */
.user-menu {
  position: relative;
}

.user-menu-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
  transition: all 0.3s ease;
}

.user-menu-btn:hover {
  color: var(--accent-primary);
  transform: scale(1.1);
}

.user-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.5rem;
  background: rgba(5, 7, 20, 0.95);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  min-width: 150px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
  z-index: 1000;
  animation: fadeIn 0.3s ease-out;
}

.dropdown-item {
  padding: 0.75rem 1rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
}

.dropdown-item:hover {
  background: rgba(16, 21, 48, 0.9);
  color: var(--text-primary);
  padding-left: 1.25rem;
}

.dropdown-item.logout:hover {
  background: rgba(255, 0, 68, 0.1);
  color: #ff3366;
}

.dropdown-divider {
  height: 1px;
  background: var(--border-color);
  margin: 0.25rem 0;
}

/* 移动端导航 */
.mobile-nav-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(5, 7, 20, 0.9);
  display: flex;
  justify-content: flex-end;
  z-index: 999;
  animation: fadeIn 0.3s ease-out;
}

.mobile-nav {
  width: 280px;
  max-width: 80vw;
  height: 100%;
  background: rgba(10, 13, 32, 0.95);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.mobile-close-btn {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 1rem;
  align-self: flex-end;
  transition: all 0.3s ease;
}

.mobile-close-btn:hover {
  color: var(--accent-primary);
  transform: scale(1.1);
}

.mobile-nav-links {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 1rem 1rem;
}

.mobile-nav-links .nav-link {
  justify-content: center;
  padding: 1rem 1.5rem;
}

.mobile-nav-links .nav-text {
  display: inline;
  font-size: 1rem;
}

/* 主内容区域 */
.void-main {
  flex: 1;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

/* 背景效果 */
.background-effects {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 0;
  pointer-events: none;
}

.background-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at center, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 40px 40px;
  animation: gridPulse 8s infinite alternate;
}

@keyframes gridPulse {
  0% { opacity: 0.2; transform: scale(1); }
  100% { opacity: 0.4; transform: scale(1.05); }
}

.background-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 800px;
  height: 800px;
  background: radial-gradient(circle, var(--accent-glow), transparent 70%);
  filter: blur(80px);
  transform: translate(-50%, -50%);
  animation: pulse 10s ease-in-out infinite;
}

/* 内容包装器 */
.content-wrapper {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  animation: fadeIn 0.8s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 底部信息栏 */
.void-footer {
  background: linear-gradient(0deg, rgba(45, 64, 184, 0.95), rgba(45, 64, 184, 0.7));
  border-top: 1px solid var(--border-color);
  padding: 1rem 2rem;
  backdrop-filter: blur(10px);
  text-align: center;
  position: relative;
}

.system-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  flex-wrap: wrap;
}

.energy-bar {
  flex: 1;
  min-width: 200px;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary), var(--accent-primary));
  background-size: 200% 100%;
  animation: energyFlow 4s infinite linear;
}

@keyframes energyFlow {
  0% { background-position: 0% 0%; }
  100% { background-position: 200% 0%; }
}

.system-metrics {
  display: flex;
  gap: 1.5rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  flex-wrap: wrap;
  justify-content: center;
}

.copyright {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.timestamp {
  font-family: var(--main-font);
  color: var(--accent-primary);
  opacity: 0.8;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .system-metrics {
    gap: 1rem;
  }
  
  .copyright {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-end;
  }
}

@media (max-width: 768px) {
  .void-header {
    padding: 1rem;
  }
  
  .nav-text {
    display: none;
  }
  
  .nav-link {
    padding: 0.75rem;
  }
  
  .system-info {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }
  
  .system-metrics {
    justify-content: space-around;
  }
  
  .copyright {
    align-items: center;
    text-align: center;
  }
}


</style>
