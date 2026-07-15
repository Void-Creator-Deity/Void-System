<template>
  <div class="void-page-container register-page">
    <div class="register-card void-card animate-float">
      <div class="register-header">
        <p class="auth-eyebrow">Get Started</p>
        <h1 class="logo-text">创建账号</h1>
        <p class="subtitle">用一个账号保存你的目标、资料和成长记录。</p>
      </div>
      
      <el-form :model="registerForm" :rules="rules" ref="registerFormRef" class="void-form">
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="昵称"
            prefix-icon="User"
            class="void-input"
            :disabled="isLoading"
          />
        </el-form-item>
        
        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="邮箱"
            prefix-icon="Message"
            class="void-input"
            :disabled="isLoading"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="设置密码"
            prefix-icon="Lock"
            class="void-input"
            show-password
            :disabled="isLoading"
          />
        </el-form-item>
        
        <div class="form-options">
          <router-link to="/login" class="link-text">已有账号，去登录</router-link>
        </div>
        
        <div class="form-actions">
          <el-button 
            type="primary" 
            @click="handleRegister" 
            class="void-btn primary w-full"
            :loading="isLoading"
          >
            创建账号
          </el-button>
        </div>
      </el-form>
      
      <div class="register-footer">
        <span class="version-tag">Void System</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { register } from '@/api/user'
import { getApiErrorMessage } from '@/api/index.js'

const router = useRouter()
const registerFormRef = ref()
const isLoading = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  password: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { 
      pattern: /^[\w-]+(\.[\w-]+)*@([\w-]+\.)+[a-zA-Z]{2,7}$/, 
      message: '邮箱格式不正确',
      trigger: 'blur' 
    }
  ],
  username: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 1, max: 20, message: '昵称长度需在 1-20 字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    isLoading.value = true
    try {
      await register(registerForm)
      ElMessage.success('账号已创建，请登录')
      router.push('/login')
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '注册失败，请稍后重试'))
    } finally {
      isLoading.value = false
    }
  })
}
</script>

<style scoped>
.register-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: clamp(24px, 5vw, 48px);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--bg-secondary) 55%, transparent), transparent 320px),
    var(--bg-page);
}

.register-card {
  width: 100%;
  max-width: 420px;
  padding: var(--spacing-xxl) var(--spacing-xl);
  text-align: center;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.register-header {
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
  justify-content: flex-end;
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

.register-footer {
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
