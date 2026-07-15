<template>
  <div class="void-page-container login-page">
    <div class="login-card void-card animate-float">
      <div class="login-header">
        <p class="auth-eyebrow">Welcome Back</p>
        <h1 class="logo-text">登录账号</h1>
        <p class="subtitle">继续推进你的目标、行动和学习计划。</p>
      </div>
      
      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" class="void-form">
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名或邮箱"
            prefix-icon="User"
            class="void-input"
            :disabled="isLoading"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            class="void-input"
            show-password
            :disabled="isLoading"
          />
        </el-form-item>
        
        <div class="form-options">
          <el-checkbox v-model="loginForm.rememberMe" class="void-checkbox" :disabled="isLoading">记住账号</el-checkbox>
          <router-link to="/register" class="link-text">创建账号</router-link>
        </div>
        
        <div class="form-actions">
          <el-button 
            type="primary" 
            @click="handleLogin" 
            class="void-btn primary w-full"
            :loading="isLoading"
          >
            登录
          </el-button>
        </div>
      </el-form>
      
      <div class="login-footer">
        <span class="version-tag">Void System</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { login } from '@/api/user'
import { getApiErrorMessage } from '@/api/index.js'

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
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
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
      
      ElMessage.success('登录成功')
      router.push('/')
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '登录失败，请检查账号和密码'))
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
  padding: clamp(24px, 5vw, 48px);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--bg-secondary) 55%, transparent), transparent 320px),
    var(--bg-page);
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: var(--spacing-xxl) var(--spacing-xl);
  text-align: center;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.login-header {
  margin-bottom: var(--spacing-xl);
}

.auth-eyebrow {
  margin: 0 0 8px;
  color: var(--color-primary);
  font-family: var(--font-family-mono);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.logo-text {
  font-size: 2.6rem;
  font-weight: 800;
  letter-spacing: 0;
  margin-bottom: var(--spacing-xs);
}

.subtitle {
  color: var(--text-secondary);
  font-size: 0.95rem;
  letter-spacing: 0;
  line-height: 1.6;
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
</style>
