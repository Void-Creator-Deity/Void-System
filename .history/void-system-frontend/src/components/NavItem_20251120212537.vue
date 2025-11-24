<template>
  <RouterLink 
    :to="to" 
    class="nav-item"
    custom
    v-slot="{ isActive }"
  >
    <div 
      class="nav-link"
      :class="{ active: isActive }"
      @click="(event) => handleClick(event)"
    >
      <span class="nav-icon">{{ icon }}</span>
      <span class="nav-text"><slot /></span>
      <div v-if="isActive" class="nav-indicator"></div>
    </div>
  </RouterLink>
</template>

<script setup>
import { RouterLink } from 'vue-router'

// 定义组件属性
const props = defineProps({
  to: {
    type: String,
    required: true
  },
  icon: {
    type: String,
    default: ''
  }
})

// 定义组件事件
const emit = defineEmits(['click'])

// 处理点击事件
const handleClick = (event) => {
  // 先发出点击事件
  emit('click')
  // 不需要阻止默认行为，因为RouterLink的导航行为应该正常工作
  // 但确保事件冒泡正常
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
