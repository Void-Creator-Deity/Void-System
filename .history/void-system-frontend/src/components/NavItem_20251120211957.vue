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
      @click="handleClick"
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
const handleClick = () => {
  emit('click')
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
  <router-link :to="to" class="nav-item">
    <span class="nav-icon">{{ icon }}</span>
    <span class="nav-text">{{ $slots.default }}</span>
  </router-link>

<script setup>
import { defineProps } from 'vue'

defineProps({
  to: {
    type: String,
    required: true
  },
  icon: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  color: var(--color-text-primary);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-normal);
}

.nav-item:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-primary);
}

.nav-item.router-link-active {
  background-color: var(--color-bg-tertiary);
  color: var(--color-primary);
  font-weight: 500;
}

.nav-icon {
  font-size: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
}

.nav-text {
  font-size: 0.9375rem;
}
</style>
