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
  display: inline-block;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs, 0.5rem);
  padding: var(--spacing-sm, 0.5rem) var(--spacing-lg, 1.25rem);
  color: var(--color-text-secondary, #cbd5e1);
  text-decoration: none;
  border-radius: var(--radius-lg, 12px);
  transition: all var(--transition-normal, 0.3s ease);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  font-weight: 500;
  font-size: 0.95rem;
  border: 1px solid transparent;
  background: rgba(30, 41, 59, 0.3);
  backdrop-filter: blur(8px);
}

.nav-link::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.15), transparent);
  transition: left var(--transition-slow, 0.5s ease);
  z-index: 0;
}

.nav-link:hover {
  background: rgba(51, 65, 85, 0.6);
  color: var(--color-text-primary, #f8fafc);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25),
              0 0 0 1px rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.3);
}

.nav-link:hover::before {
  left: 100%;
}

.nav-link.active {
  color: var(--color-primary, #6366f1);
  background: linear-gradient(135deg, 
    rgba(99, 102, 241, 0.2), 
    rgba(6, 182, 212, 0.15)
  );
  box-shadow: 
    0 6px 20px rgba(99, 102, 241, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  text-shadow: 0 0 15px rgba(99, 102, 241, 0.5);
  border: 1px solid rgba(99, 102, 241, 0.4);
  transform: translateY(-1px);
}

.nav-link.active::before {
  left: 100%;
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
  transition: all var(--transition-normal, 0.3s ease);
  filter: drop-shadow(0 0 5px rgba(99, 102, 241, 0.3));
  position: relative;
  z-index: 1;
}

.nav-link:hover .nav-icon {
  transform: scale(1.15);
  filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.5));
}

.nav-link.active .nav-icon {
  filter: drop-shadow(0 0 12px rgba(99, 102, 241, 0.8));
  animation: iconPulse 2s ease-in-out infinite;
}

@keyframes iconPulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
  }
}

.nav-text {
  font-weight: 500;
  letter-spacing: 0.3px;
  position: relative;
  z-index: 1;
  transition: all var(--transition-normal, 0.3s ease);
}

.nav-link.active .nav-text {
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
</style>
