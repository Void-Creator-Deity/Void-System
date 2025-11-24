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
  padding: var(--spacing-sm, 0.5rem) var(--spacing-md, 1rem);
  color: var(--color-text-secondary, #9ca3af);
  text-decoration: none;
  border-radius: var(--radius-md, 8px);
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  font-weight: 500;
  font-size: 0.95rem;
}

.nav-link::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(67, 97, 238, 0.1), transparent);
  transition: left 0.5s ease;
}

.nav-link:hover {
  background: linear-gradient(135deg, 
    rgba(31, 41, 55, 0.6), 
    rgba(55, 65, 81, 0.4)
  );
  color: var(--color-text-primary, #f3f4f6);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.nav-link:hover::before {
  left: 100%;
}

.nav-link.active {
  color: var(--color-primary, #4361ee);
  background: linear-gradient(135deg, 
    rgba(67, 97, 238, 0.15), 
    rgba(76, 201, 240, 0.1)
  );
  box-shadow: 
    0 0 15px rgba(67, 97, 238, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  text-shadow: 0 0 10px rgba(67, 97, 238, 0.5);
  border: 1px solid rgba(67, 97, 238, 0.3);
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
    var(--color-primary, #4361ee), 
    var(--color-secondary, #4cc9f0)
  );
  border-radius: var(--radius-full, 9999px);
  box-shadow: 0 0 10px rgba(67, 97, 238, 0.6);
  animation: indicatorGlow 2s ease-in-out infinite;
}

@keyframes indicatorGlow {
  0%, 100% {
    opacity: 0.8;
    box-shadow: 0 0 10px rgba(67, 97, 238, 0.6);
  }
  50% {
    opacity: 1;
    box-shadow: 0 0 20px rgba(67, 97, 238, 0.9);
  }
}

.nav-icon {
  font-size: 1.25rem;
  transition: transform 0.3s ease;
  filter: drop-shadow(0 0 3px rgba(67, 97, 238, 0.3));
}

.nav-link:hover .nav-icon {
  transform: scale(1.1);
}

.nav-link.active .nav-icon {
  filter: drop-shadow(0 0 8px rgba(67, 97, 238, 0.6));
  animation: iconPulse 2s ease-in-out infinite;
}

@keyframes iconPulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.15);
  }
}

.nav-text {
  font-weight: 500;
  letter-spacing: 0.3px;
  position: relative;
  z-index: 1;
}
</style>
