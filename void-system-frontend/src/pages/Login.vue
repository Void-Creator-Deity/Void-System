<template>
  <div class="void-page-container login-page">
    <div class="login-card void-card animate-float">
      <div class="login-header">
        <h1 class="logo-text"><span class="void-text-gradient">虚空</span> 系统</h1>
        <p class="subtitle">正在接入意识矩阵...</p>
      </div>
      
      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" class="void-form">
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名 / 标识符"
            prefix-icon="User"
            class="void-input"
            :disabled="isLoading"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="接入密钥"
            prefix-icon="Lock"
            class="void-input"
            show-password
            :disabled="isLoading"
          />
        </el-form-item>
        
        <div class="form-options">
          <el-checkbox v-model="loginForm.rememberMe" class="void-checkbox" :disabled="isLoading">保持在线会话</el-checkbox>
          <router-link to="/register" class="link-text">初始化新档案</router-link>
        </div>
        
        <div class="form-actions">
          <el-button 
            type="primary" 
            @click="handleLogin" 
            class="void-btn primary w-full"
            :loading="isLoading"
          >
            授权进入
          </el-button>
        </div>
      </el-form>
      
      <div class="login-footer">
        <span class="version-tag">Core v1.0.0</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { login } from '@/api/user'

const router = useRouter()
const loginFormRef = ref()
const isLoading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
  rememberMe: false
})

const rules = {
  username: [
    { required: true, message: '需要身份认证', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '需要接入密钥', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    isLoading.value = true
    try {
      await login(loginForm.username, loginForm.password)
      
      if (loginForm.rememberMe) {
        localStorage.setItem('remembered_user', loginForm.username)
      } else {
        localStorage.removeItem('remembered_user')
      }
      
      ElMessage.success('神经链路已建立')
      router.push('/')
    } catch (error) {
      const msg = error.response?.data?.detail || '授权失败'
      ElMessage.error(msg)
    } finally {
      isLoading.value = false
    }
  })
}

onMounted(() => {
  const user = localStorage.getItem('remembered_user')
  if (user) {
    loginForm.username = user
    loginForm.rememberMe = true
  }
})
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: var(--bg-page);
  background-image: 
    radial-gradient(circle at 50% 50%, var(--color-primary-transparent) 0%, transparent 70%);
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: var(--spacing-xxl) var(--spacing-xl);
  text-align: center;
}

.login-header {
  margin-bottom: var(--spacing-xl);
}

.logo-text {
  font-size: 2.5rem;
  font-weight: 800;
  letter-spacing: -1px;
  margin-bottom: var(--spacing-xs);
}

.subtitle {
  color: var(--text-muted);
  font-size: 0.9rem;
  letter-spacing: 1px;
}

.void-form {
  margin-top: var(--spacing-xl);
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  font-size: 0.85rem;
}

.link-text {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
  transition: color var(--transition-fast);
}

.link-text:hover {
  color: var(--color-primary-light);
  text-decoration: underline;
}

.form-actions {
  margin-top: var(--spacing-lg);
}

.w-full {
  width: 100%;
}

.login-footer {
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--border-color-light);
}

.version-tag {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-family-mono);
}

@keyframes voidFadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-float {
  animation: voidFadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
</style>