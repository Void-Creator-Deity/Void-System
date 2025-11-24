<template>
  <div id="app" class="void-app">
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
      </div>
      
      <nav class="nav-links">
        <NavItem to="/" icon="⌨️">控制台</NavItem>
        <NavItem to="/advisor" icon="🧠">学习顾问</NavItem>
        <NavItem to="/qa" icon="❓">知识问答</NavItem>
        <NavItem to="/settings" icon="⚙️">系统设置</NavItem>
      </nav>
      
      <!-- 用户信息区域 -->
      <div class="user-area">
        <div class="user-profile">
          <div class="user-avatar">
            <span>U</span>
          </div>
          <div class="system-status">
            <div class="status-indicator">
              <div class="status-dot"></div>
              <span>在线</span>
            </div>
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
import { RouterLink, RouterView } from 'vue-router'

// 导航项组件
import { h } from 'vue'

const NavItem = (props, { slots }) => {
  return h(RouterLink,
    {
      to: props.to,
      class: 'nav-item',
      custom: true,
      vSlots: {
        default: ({ isActive }) => h('div',
          { class: ['nav-link', isActive ? 'active' : ''] },
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
NavItem.props = ['to', 'icon']
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

/* 导航链接 */
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

/* 用户区域 */
.user-area {
  display: flex;
  align-items: center;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 1rem;
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
}

.system-status {
  display: flex;
  align-items: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  background-color: #00ff66;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
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
