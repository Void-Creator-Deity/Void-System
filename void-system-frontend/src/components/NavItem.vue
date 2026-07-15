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
      <span class="nav-icon">
        <component v-if="typeof icon !== 'string'" :is="icon" />
        <span v-else>{{ icon }}</span>
      </span>
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
    type: [String, Object, Function],
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
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 36px;
  padding: 7px 11px;
  color: var(--text-secondary, #4d5b54);
  text-decoration: none;
  border-radius: var(--radius-md, 8px);
  transition:
    color var(--transition-normal, 0.3s ease),
    background var(--transition-normal, 0.3s ease),
    border-color var(--transition-normal, 0.3s ease);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  font-weight: 700;
  font-size: 0.84rem;
  line-height: 1.25;
  border: 1px solid transparent;
  background: transparent;
  flex-shrink: 0;
  max-width: 10.5rem;
}

.nav-link::before {
  content: '';
  position: absolute;
  inset: auto 10px 5px 10px;
  height: 2px;
  border-radius: 999px;
  background: var(--color-primary);
  opacity: 0;
  transition: opacity var(--transition-normal, 0.3s ease);
  pointer-events: none;
}

.nav-link:hover {
  background: color-mix(in srgb, var(--bg-card) 84%, transparent);
  color: var(--text-primary, #17201c);
  border-color: var(--border-color-light);
}

.nav-link:hover::before,
.nav-link.active::before {
  opacity: 1;
}

.nav-link.active {
  color: var(--color-primary-dark, #164d49);
  background: var(--bg-card);
  border-color: color-mix(in srgb, var(--color-primary) 24%, var(--border-color));
  box-shadow: var(--shadow-sm);
}

.nav-indicator {
  display: none;
}

.nav-icon {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.98rem;
  line-height: 1;
  position: relative;
  z-index: 1;
  filter: grayscale(0.2);
}

.nav-text {
  font-weight: 700;
  letter-spacing: 0;
  position: relative;
  z-index: 1;
  transition: color var(--transition-normal, 0.3s ease);
  word-break: keep-all;
  white-space: nowrap;
  text-align: left;
}

.nav-link.active .nav-text {
  color: var(--text-primary, #17201c);
}
@media (max-width: 900px) {
  .nav-item { display: block; min-width: 0; }

  .nav-link {
    width: 100%;
    min-height: 52px;
    padding: 5px 2px;
    flex-direction: column;
    justify-content: center;
    gap: 3px;
    border-radius: var(--radius-md, 8px);
    font-size: 0.68rem;
    max-width: none;
  }

  .nav-link::before {
    inset: 3px auto auto 50%;
    width: 18px;
    transform: translateX(-50%);
  }

  .nav-icon { width: 20px; height: 20px; font-size: 1.05rem; }
  .nav-icon :deep(svg) { width: 18px; height: 18px; }
  .nav-text { max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
}
</style>
