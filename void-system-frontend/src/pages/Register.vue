<template>
  <div class="void-page-container register-page">
    <div class="register-card void-card animate-float">
      <div class="register-header">
        <h1 class="logo-text"><span class="void-text-gradient">虚空</span> 系统</h1>
        <p class="subtitle">正在初始化新神经档案...</p>
      </div>
      
      <el-form :model="registerForm" :rules="rules" ref="registerFormRef" class="void-form">
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="唯一身份标识"
            prefix-icon="User"
            class="void-input"
            :disabled="isLoading"
          />
        </el-form-item>
        
        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="神经同步地址 (邮箱)"
            prefix-icon="Message"
            class="void-input"
            :disabled="isLoading"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="设置接入密钥"
            prefix-icon="Lock"
            class="void-input"
            show-password
            :disabled="isLoading"
          />
        </el-form-item>
        
        <div class="form-options">
          <router-link to="/login" class="link-text">返回授权页面</router-link>
        </div>
        
        <div class="form-actions">
          <el-button 
            type="primary" 
            @click="handleRegister" 
            class="void-btn primary w-full"
            :loading="isLoading"
          >
            凝聚档案
          </el-button>
        </div>
      </el-form>
      
      <div class="register-footer">
        <span class="version-tag">Core v1.0.0</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { register } from '@/api/user'

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
    { required: true, message: '需要神经同步地址', trigger: 'blur' },
    { 
      pattern: /^[\w-]+(\.[\w-]+)*@([\w-]+\.)+[a-zA-Z]{2,7}$/, 
      message: '地址格式无效', 
      trigger: 'blur' 
    }
  ],
  username: [
    { required: true, message: '需要身份标识', trigger: 'blur' },
    { min: 1, max: 20, message: '标识长度需在 1-20 字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '需要接入密钥', trigger: 'blur' },
    { min: 6, message: '密钥长度至少为 6 位', trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    isLoading.value = true
    try {
      await register(registerForm)
      ElMessage.success('神经档案已同步')
      router.push('/login')
    } catch (error) {
      const msg = error.response?.data?.detail || '档案凝聚失败'
      ElMessage.error(msg)
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
  background: var(--bg-page);
  background-image: 
    radial-gradient(circle at 50% 50%, var(--color-primary-transparent) 0%, transparent 70%);
}

.register-card {
  width: 100%;
  max-width: 420px;
  padding: var(--spacing-xxl) var(--spacing-xl);
  text-align: center;
}

.register-header {
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

@keyframes voidFadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-float {
  animation: voidFadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
</style>