<template>
  <RouterLink 
    :to="to" 
    class="nav-item"
    custom
    v-slot="{ isActive, navigate }"
  >
    <div 
      class="nav-link"
      :class="{ active: isActive }"
      @click="handleClick(navigate, $event)"
    >
      <span class="nav-icon">{{ icon }}</span>
      <span class="nav-text"><slot /></span>
      <div v-if="isActive" class="nav-indicator"></div>
    </div>
  </RouterLink>
</template>

<script setup>
/**
 * NavItem Component
 * -----------------
 * 导航项组件，用于应用顶部导航栏
 */

import { RouterLink } from 'vue-router'

/**
 * 组件属性定义
 */
const props = defineProps({
  /** 路由路径 */
  to: {
    type: String,
    required: true
  },
  /** 图标（emoji 或文本） */
  icon: {
    type: String,
    default: ''
  }
})

/**
 * 组件事件定义
 */
const emit = defineEmits(['click'])

/**
 * 处理点击事件
 * @param {Function} navigate - RouterLink 提供的导航函数
 * @param {Event} event - 点击事件对象
 */
const handleClick = (navigate, event) => {
  // 发出点击事件
  emit('click', event)
  // 执行路由导航
  navigate(event)
}
</script>

<style scoped>
.nav-item {
  position: relative;
  display: inline-flex;
  align-items: center;
  /* 扩大 hover 命中缓冲区，避免边缘抖动触发 */
  padding: 2px 0;
  margin: -2px 0;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs, 0.5rem);
  padding: var(--spacing-sm, 0.5rem) var(--spacing-md, 0.75rem);
  color: var(--color-text-secondary, #cbd5e1);
  text-decoration: none;
  border-radius: var(--radius-lg, 12px);
  transition:
    transform var(--transition-normal, 0.3s ease),
    color var(--transition-normal, 0.3s ease),
    background var(--transition-normal, 0.3s ease),
    box-shadow var(--transition-normal, 0.3s ease),
    border-color var(--transition-normal, 0.3s ease);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  font-weight: 500;
  font-size: 0.875rem;
  line-height: 1.25;
  border: 1px solid transparent;
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.34), rgba(30, 41, 59, 0.22));
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  flex-shrink: 0;
  max-width: 11rem;
  transform-origin: center center;
}

.nav-link::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 25%, rgba(99, 102, 241, 0.12) 50%, transparent 75%);
  opacity: 0;
  transition: opacity var(--transition-normal, 0.3s ease);
  z-index: 0;
  pointer-events: none;
}

.nav-link:hover {
  background: linear-gradient(135deg, rgba(51, 65, 85, 0.62), rgba(51, 65, 85, 0.5));
  color: var(--color-text-primary, #f8fafc);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25),
              0 0 0 1px rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.3);
}

.nav-link:hover::before,
.nav-link.active::before {
  opacity: 1;
}

.nav-link.active {
  color: var(--color-primary-light, #93c5fd);
  background: linear-gradient(135deg, 
    rgba(99, 102, 241, 0.2), 
    rgba(6, 182, 212, 0.15)
  );
  box-shadow: 
    0 6px 20px rgba(99, 102, 241, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  text-shadow: 0 0 12px rgba(99, 102, 241, 0.35);
  border: 1px solid rgba(99, 102, 241, 0.4);
}

.nav-indicator {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, 
    var(--color-primary, #6366f1), 
    var(--color-secondary, #06b6d4),
    var(--color-accent, #ec4899)
  );
  background-size: 200% 100%;
  border-radius: var(--radius-full, 9999px);
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.7);
  animation: indicatorGlow 3s ease-in-out infinite;
}

@keyframes indicatorGlow {
  0%, 100% {
    opacity: 0.8;
    box-shadow: 0 0 15px rgba(99, 102, 241, 0.7);
    background-position: 0% 50%;
  }
  50% {
    opacity: 1;
    box-shadow: 0 0 25px rgba(99, 102, 241, 1);
    background-position: 100% 50%;
  }
}

.nav-icon {
  font-size: 1.35rem;
  transition: color var(--transition-normal, 0.3s ease);
  filter: drop-shadow(0 0 4px rgba(99, 102, 241, 0.28));
  position: relative;
  z-index: 1;
}

.nav-link:hover .nav-icon {
  color: var(--color-text-primary, #f8fafc);
}

.nav-link.active .nav-icon {
  color: var(--color-primary-light, #93c5fd);
}

.nav-text {
  font-weight: 500;
  letter-spacing: 0.02em;
  position: relative;
  z-index: 1;
  transition: color var(--transition-normal, 0.3s ease);
  word-break: keep-all;
  white-space: nowrap;
  text-align: left;
}

/* 勿用 background-clip:text + transparent 填充：深色主题下常导致选中态文字「消失」 */
.nav-link.active .nav-text {
  color: var(--text-primary, #e8eaed);
  text-shadow: 0 0 20px rgba(147, 197, 253, 0.45);
}
</style>
