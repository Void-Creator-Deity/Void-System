<template>
  <div class="register-container">
    <div class="register-form-wrapper">
      <div class="register-header">
        <h2><span class="glitch">VOID</span> <span class="system-text">SYSTEM</span></h2>
        <p class="subtitle">创建新账号</p>
      </div>
      
      <el-form :model="registerForm" :rules="rules" ref="registerFormRef" label-width="0px" class="register-form">
        <el-form-item prop="username">
          <div class="input-wrapper">
            <el-input
              v-model="registerForm.username"
              placeholder="用户名"
              prefix-icon="el-icon-user"
              :disabled="isLoading"
            />
          </div>
        </el-form-item>
        
        <el-form-item prop="email">
          <div class="input-wrapper">
            <el-input
              v-model="registerForm.email"
              placeholder="邮箱（选填）"
              prefix-icon="el-icon-message"
              :disabled="isLoading"
            />
          </div>
        </el-form-item>
        
        <el-form-item prop="nickname">
          <div class="input-wrapper">
            <el-input
              v-model="registerForm.nickname"
              placeholder="昵称（选填）"
              prefix-icon="el-icon-user-solid"
              :disabled="isLoading"
            />
          </div>
        </el-form-item>
        
        <el-form-item prop="password">
          <div class="input-wrapper">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="密码"
              prefix-icon="el-icon-lock"
              show-password
              :disabled="isLoading"
            />
          </div>
        </el-form-item>
        
        <el-form-item>
          <div class="form-actions">
            <router-link to="/login" class="login-link">已有账号？返回登录</router-link>
          </div>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            @click="handleRegister" 
            class="register-btn"
            :loading="isLoading"
            :disabled="isLoading"
          >
            {{ isLoading ? '注册中...' : '注册' }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
/**
 * Register Component
 * -------------------
 * 用户注册页面
 */

import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { register } from '@/api/user'

const router = useRouter()
const registerFormRef = ref()
const isLoading = ref(false)

// 注册表单数据
const registerForm = reactive({
  username: '',
  email: '',
  nickname: '',
  password: ''
})

// 表单验证规则
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { 
      pattern: /^[\w-]+(\.[\w-]+)*@([\w-]+\.)+[a-zA-Z]{2,7}$/, 
      message: '请输入有效的邮箱地址', 
      trigger: 'blur' 
    }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为 6 个字符', trigger: 'blur' }
  ]
}

/**
 * 处理注册
 */
const handleRegister = async () => {
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    isLoading.value = true
    try {
      await register(registerForm)
      ElMessage.success('注册成功，请登录')
      router.push('/login')
    } catch (error) {
      console.error('注册失败:', error)
      const errorMessage = error.response?.data?.detail || 
                          '注册失败，请稍后重试'
      ElMessage.error(errorMessage)
    } finally {
      isLoading.value = false
    }
  })
}
</script>

<style scoped>
.register-container {
  width: 100%;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: 
    radial-gradient(circle at 20% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(6, 182, 212, 0.15) 0%, transparent 50%),
    radial-gradient(circle at 40% 60%, rgba(236, 72, 153, 0.12) 0%, transparent 60%),
    linear-gradient(135deg, var(--color-bg-primary) 0%, #13192e 50%, var(--color-bg-primary) 100%);
  background-attachment: fixed;
  background-size: cover;
  position: relative;
  overflow: hidden;
}

.register-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: 
    radial-gradient(2px 2px at 20% 30%, rgba(99, 102, 241, 0.35), transparent),
    radial-gradient(2px 2px at 60% 70%, rgba(6, 182, 212, 0.35), transparent),
    radial-gradient(1px 1px at 50% 50%, rgba(236, 72, 153, 0.3), transparent),
    radial-gradient(1px 1px at 80% 10%, rgba(99, 102, 241, 0.3), transparent),
    radial-gradient(2px 2px at 90% 60%, rgba(6, 182, 212, 0.35), transparent),
    radial-gradient(1px 1px at 30% 80%, rgba(236, 72, 153, 0.35), transparent);
  background-size: 200% 200%, 200% 200%, 300% 300%, 250% 250%, 180% 180%, 220% 220%;
  background-position: 0% 0%, 100% 100%, 50% 50%, 80% 20%, 90% 60%, 30% 80%;
  animation: particleMove 20s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
  opacity: 0.6;
  filter: blur(0.5px);
}

@keyframes particleMove {
  0%, 100% {
    background-position: 0% 0%, 100% 100%, 50% 50%, 80% 20%, 90% 60%, 30% 80%;
  }
  50% {
    background-position: 100% 100%, 0% 0%, 50% 50%, 20% 80%, 10% 40%, 70% 20%;
  }
}

.register-form-wrapper {
  width: 100%;
  max-width: 480px;
  background: rgba(30, 41, 59, 0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-xl);
  padding: 3.5rem 2.5rem;
  box-shadow: 
    0 24px 64px rgba(0, 0, 0, 0.45),
    0 0 60px rgba(99, 102, 241, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  position: relative;
  z-index: 1;
  transition: all var(--transition-normal);
  overflow: hidden;
  margin: 1.5rem;
}

.register-form-wrapper::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, 
    transparent, 
    var(--color-primary), 
    var(--color-secondary),
    var(--color-accent),
    var(--color-primary),
    transparent
  );
  background-size: 200% 100%;
  animation: shimmer 4s ease-in-out infinite;
  opacity: 0.8;
}

.register-form-wrapper:hover {
  box-shadow: 
    0 28px 72px rgba(0, 0, 0, 0.55),
    0 0 80px rgba(99, 102, 241, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  border-color: rgba(99, 102, 241, 0.5);
  transform: translateY(-3px) scale(1.01);
}

.register-header {
  text-align: center;
  margin-bottom: 2.5rem;
  position: relative;
}

.register-header h2 {
  font-size: 2.8rem;
  margin: 0 0 0.75rem 0;
  font-weight: 800;
  letter-spacing: 2.5px;
  background: linear-gradient(135deg, 
    var(--color-primary-light), 
    var(--color-secondary),
    var(--color-accent),
    var(--color-primary-dark)
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  display: inline-block;
}

.register-header .glitch {
  color: var(--color-primary);
  text-shadow: 
    0 0 15px rgba(99, 102, 241, 0.6),
    0 0 30px rgba(99, 102, 241, 0.4),
    0 0 45px rgba(99, 102, 241, 0.2);
  animation: pulseGlow 2.5s ease-in-out infinite;
  display: inline-block;
}

.register-header .system-text {
  color: var(--color-text-primary);
  font-weight: 600;
}

.register-header .subtitle {
  color: var(--color-text-secondary);
  font-size: 1rem;
  margin-top: 0.75rem;
  letter-spacing: 1.2px;
  opacity: 0.8;
}

.register-form {
  margin-top: 2.5rem;
}

.input-wrapper {
  position: relative;
  margin-bottom: 1.5rem;
}

.input-wrapper :deep(.el-input__wrapper) {
  background: rgba(51, 65, 85, 0.85);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  transition: all var(--transition-normal);
  box-shadow: 
    0 2px 12px rgba(0, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  padding: 0.5rem 1rem;
}

.input-wrapper :deep(.el-input__wrapper:hover) {
  border-color: rgba(99, 102, 241, 0.4);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.2),
    0 0 0 1px rgba(99, 102, 241, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.input-wrapper :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 
    0 0 0 3px rgba(99, 102, 241, 0.2),
    0 6px 24px rgba(99, 102, 241, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
  animation: pulseGlow 2.5s ease-in-out infinite;
}

.input-wrapper :deep(.el-input__inner) {
  color: var(--color-text-primary);
  background: transparent;
  font-size: 1rem;
  padding: 0.625rem 0;
}

.input-wrapper :deep(.el-input__prefix-icon) {
  color: var(--color-primary);
  font-size: 1.125rem;
  opacity: 0.8;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  font-size: 0.95rem;
  margin-bottom: 1.75rem;
}

.login-link {
  color: var(--color-primary);
  text-decoration: none;
  transition: all var(--transition-normal);
  position: relative;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.login-link::after {
  content: '';
  position: absolute;
  bottom: -3px;
  left: 0;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  transition: width var(--transition-normal);
  border-radius: var(--radius-full);
}

.login-link:hover {
  color: var(--color-primary-light);
  text-shadow: 0 0 15px rgba(99, 102, 241, 0.5);
  transform: translateY(-1px);
}

.login-link:hover::after {
  width: 100%;
}

.register-btn {
  width: 100%;
  height: 52px;
  font-size: 1.05rem;
  font-weight: 600;
  letter-spacing: 1.5px;
  background: linear-gradient(135deg, 
    var(--color-primary), 
    var(--color-primary-dark)
  );
  border: none;
  border-radius: var(--radius-lg);
  box-shadow: 
    0 6px 24px rgba(99, 102, 241, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
  color: white;
  text-transform: uppercase;
}

.register-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.35), transparent);
  transition: left var(--transition-slow, 0.6s ease);
  z-index: 1;
}

.register-btn:hover:not(:disabled) {
  transform: translateY(-3px) scale(1.02);
  box-shadow: 
    0 10px 36px rgba(99, 102, 241, 0.55),
    0 0 50px rgba(99, 102, 241, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  background: linear-gradient(135deg, 
    var(--color-primary-dark), 
    var(--color-primary)
  );
}

.register-btn:hover:not(:disabled)::before {
  left: 100%;
}

.register-btn:active:not(:disabled) {
  transform: translateY(-1px) scale(0.99);
  box-shadow: 
    0 4px 16px rgba(99, 102, 241, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.register-btn > * {
  position: relative;
  z-index: 2;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .register-form-wrapper {
    padding: 2.5rem 2rem;
    margin: 1.5rem;
    max-width: calc(100% - 3rem);
  }
  
  .register-header h2 {
    font-size: 2.25rem;
    letter-spacing: 2px;
  }
  
  .register-header .subtitle {
    font-size: 0.95rem;
  }
}

@media (max-width: 480px) {
  .register-form-wrapper {
    padding: 2rem 1.5rem;
    margin: 1rem;
    max-width: calc(100% - 2rem);
  }
  
  .register-header h2 {
    font-size: 2rem;
    letter-spacing: 1.5px;
  }
  
  .register-header .subtitle {
    font-size: 0.9rem;
  }
  
  .register-form {
    margin-top: 2rem;
  }
  
  .input-wrapper :deep(.el-input__wrapper) {
    padding: 0.375rem 0.75rem;
  }
  
  .register-btn {
    height: 48px;
    font-size: 1rem;
    letter-spacing: 1.2px;
  }
}
</style>