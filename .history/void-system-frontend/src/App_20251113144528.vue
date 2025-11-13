<template>
  <div id="app" class="void-app">
    <!-- 顶部导航栏 -->
    <header class="void-header">
      <div class="logo-area">
        <img src="/vite.svg" class="logo" alt="Void Logo" />
        <h1>Void System</h1>
      </div>
      <nav class="nav-links">
        <RouterLink to="/">控制台</RouterLink>
        <RouterLink to="/advisor">学习顾问</RouterLink>
        <RouterLink to="/qa">知识问答</RouterLink>
        <RouterLink to="/settings">系统设置</RouterLink>
      </nav>
    </header>

    <!-- 动态页面渲染区 -->
    <main class="void-main">
      <RouterView />
    </main>

    <!-- 底部状态栏 -->
    <footer class="void-footer">
      <p>© 2025 Void Studio — Learning Intelligence Framework</p>
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
  background: radial-gradient(circle at center, #0a0a0f, #000);
  color: #f5f5f5;
  font-family: 'Orbitron', sans-serif;
}

.void-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.2rem 2rem;
  background: rgba(12, 12, 20, 0.6);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.logo-area {
  display: flex;
  align-items: center;
}
.logo-area h1 {
  font-size: 1.5rem;
  margin-left: 0.8rem;
  background: linear-gradient(90deg, #f5d46f, #c9b670);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.logo {
  width: 48px;
  transition: transform 0.3s ease;
}
.logo:hover {
  transform: rotate(10deg) scale(1.1);
}

.nav-links a {
  color: #ddd;
  text-decoration: none;
  margin: 0 1.2rem;
  transition: color 0.3s;
}
.nav-links a:hover {
  color: #f2cb67;
}

.void-main {
  flex: 1;
  padding: 2rem;
}

.void-footer {
  text-align: center;
  padding: 1rem;
  font-size: 0.9rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(10, 10, 15, 0.6);
}
</style>
