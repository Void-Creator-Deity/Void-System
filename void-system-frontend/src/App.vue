<template>
  <div id="app" class="void-app">
    <!-- 系统顶栏 -->
    <header class="void-header">
      <div class="logo-area">
        <img src="/vite.svg" class="logo" alt="Void Logo" />
        <h1>VOID SYSTEM</h1>
      </div>
      <nav class="nav-links">
        <RouterLink to="/">控制台</RouterLink>
        <RouterLink to="/advisor">学习顾问</RouterLink>
        <RouterLink to="/qa">知识问答</RouterLink>
        <RouterLink to="/settings">系统设置</RouterLink>
      </nav>
    </header>

    <!-- 主界面内容区 -->
    <main class="void-main">
      <RouterView />
    </main>

    <!-- 底部系统能量条 -->
    <footer class="void-footer">
      <div class="energy-bar"></div>
      <p>© 2025 VOID STUDIO — Learning Intelligence Framework</p>
    </footer>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&display=swap');

.void-app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: radial-gradient(circle at center, #0b0b10, #000);
  color: #f5f5f5;
  font-family: 'Orbitron', sans-serif;
  overflow: hidden;
}

/* 顶部导航 */
.void-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.2rem 2.4rem;
  background: rgba(15, 15, 25, 0.7);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 20px rgba(255, 215, 0, 0.05);
}

.logo-area {
  display: flex;
  align-items: center;
}
.logo-area h1 {
  font-size: 1.6rem;
  margin-left: 0.8rem;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
  background: linear-gradient(90deg, #f5d46f, #c9b670);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  animation: glowText 3s infinite alternate;
}

@keyframes glowText {
  0% { text-shadow: 0 0 6px rgba(255, 220, 100, 0.3); }
  100% { text-shadow: 0 0 15px rgba(255, 230, 120, 0.6); }
}

.logo {
  width: 50px;
  transition: transform 0.5s ease;
  filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.4));
}
.logo:hover {
  transform: rotate(12deg) scale(1.15);
}

.nav-links a {
  color: #ccc;
  text-decoration: none;
  margin: 0 1.2rem;
  font-size: 0.95rem;
  position: relative;
  transition: color 0.3s ease;
}
.nav-links a::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 50%;
  width: 0;
  height: 2px;
  background: #f2cb67;
  transition: all 0.3s ease;
}
.nav-links a:hover {
  color: #f2cb67;
}
.nav-links a:hover::after {
  left: 0;
  width: 100%;
}

/* 主体区域 */
.void-main {
  flex: 1;
  padding: 2rem;
  position: relative;
}

/* 炼金能量网格背景 */
.void-main::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle at center, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 50px 50px;
  opacity: 0.3;
  z-index: 0;
  animation: gridPulse 8s infinite alternate;
}
@keyframes gridPulse {
  0% { opacity: 0.2; transform: scale(1); }
  100% { opacity: 0.4; transform: scale(1.05); }
}

/* 底部能量条 */
.void-footer {
  text-align: center;
  position: relative;
  padding: 1rem 0;
  font-size: 0.85rem;
  color: #999;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(15, 15, 20, 0.8);
  backdrop-filter: blur(8px);
}

.energy-bar {
  width: 60%;
  height: 4px;
  margin: 0.3rem auto 0.8rem;
  background: linear-gradient(90deg, #f0d77a, #a98f3f, #f0d77a);
  background-size: 200% 100%;
  border-radius: 4px;
  animation: energyFlow 4s infinite linear;
}
@keyframes energyFlow {
  0% { background-position: 0% 0%; }
  100% { background-position: 200% 0%; }
}
</style>
