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
  cursor: pointer;
}

.nav-link:hover {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
}

.nav-link.active {
  color: var(--color-primary);
  background-color: rgba(67, 97, 238, 0.08);
}

.nav-indicator {
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
</style>
