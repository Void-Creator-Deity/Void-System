<template>
  <router-link :to="to" class="nav-item">
    <span class="nav-icon">{{ icon }}</span>
    <span class="nav-text">{{ $slots.default }}</span>
  </router-link>
</template>

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
