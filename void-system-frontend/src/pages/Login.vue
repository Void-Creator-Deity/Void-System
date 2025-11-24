<template>
  <div class="login-container">
    <div class="login-form-wrapper">
      <div class="login-header">
        <h2><span class="glitch">VOID</span> <span class="system-text">SYSTEM</span></h2>
        <p class="subtitle">登录到虚空系统</p>
      </div>
      
      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" label-width="0px" class="login-form">
        <el-form-item prop="username">
          <div class="input-wrapper">
            <el-input
              v-model="loginForm.username"
              placeholder="用户名"
              prefix-icon="el-icon-user"
              :prefix-icon-style="{ color: '#00ccff' }"
              :disabled="isLoading"
            />
          </div>
        </el-form-item>
        
        <el-form-item prop="password">
          <div class="input-wrapper">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              prefix-icon="el-icon-lock"
              :prefix-icon-style="{ color: '#00ccff' }"
              show-password
              :disabled="isLoading"
            />
          </div>
        </el-form-item>
        
        <el-form-item>
          <div class="form-actions">
            <el-checkbox v-model="loginForm.rememberMe" :disabled="isLoading">记住我</el-checkbox>
            <router-link to="/register" class="register-link">没有账号？立即注册</router-link>
          </div>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            @click="handleLogin" 
            class="login-btn"
            :loading="isLoading"
            :disabled="isLoading"
          >
            {{ isLoading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <p class="version">版本: v1.0.0</p>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Login Component
 * ---------------
 * 用户登录页面
 */

import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { login } from '@/api/user'

const router = useRouter()
const loginFormRef = ref()
const isLoading = ref(false)

// 登录表单数据
const loginForm = reactive({
  username: '',
  password: '',
  rememberMe: false
})

// 表单验证规则
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为 6 个字符', trigger: 'blur' }
  ]
}

/**
 * 处理登录
 */
const handleLogin = async () => {
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    isLoading.value = true
    try {
      const result = await login(loginForm.username, loginForm.password)
      
      // 处理"记住我"功能
      if (loginForm.rememberMe) {
        localStorage.setItem('remembered_user', loginForm.username)
      } else {
        localStorage.removeItem('remembered_user')
      }
      
      ElMessage.success('登录成功')
      router.push('/')
    } catch (error) {
      console.error('登录失败:', error)
      const errorMessage = error.response?.data?.detail || 
                          '登录失败，请检查用户名和密码'
      ElMessage.error(errorMessage)
    } finally {
      isLoading.value = false
    }
  })
}

// 组件挂载时检查是否有记住的用户名
onMounted(() => {
  const rememberedUser = localStorage.getItem('remembered_user')
  if (rememberedUser) {
    loginForm.username = rememberedUser
    loginForm.rememberMe = true
  }
})
</script>

<style scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, 
    var(--color-bg-primary) 0%, 
    var(--color-bg-secondary) 50%,
    var(--color-bg-primary) 100%
  );
  position: relative;
  overflow: hidden;
}

.login-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: 
    radial-gradient(2px 2px at 20% 30%, rgba(67, 97, 238, 0.4), transparent),
    radial-gradient(2px 2px at 60% 70%, rgba(76, 201, 240, 0.4), transparent),
    radial-gradient(1px 1px at 50% 50%, rgba(67, 97, 238, 0.3), transparent);
  background-size: 200% 200%, 200% 200%, 300% 300%;
  animation: particleMove 15s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes particleMove {
  0%, 100% {
    background-position: 0% 0%, 100% 100%, 50% 50%;
  }
  50% {
    background-position: 100% 100%, 0% 0%, 50% 50%;
  }
}

.login-form-wrapper {
  width: 100%;
  max-width: 450px;
  background: linear-gradient(135deg, 
    rgba(31, 41, 55, 0.9), 
    rgba(55, 65, 81, 0.7)
  );
  backdrop-filter: blur(15px);
  border: 1px solid rgba(67, 97, 238, 0.3);
  border-top: 2px solid var(--color-primary);
  border-radius: var(--radius-xl);
  padding: 3rem;
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.4),
    0 0 40px rgba(67, 97, 238, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  position: relative;
  z-index: 1;
  transition: all var(--transition-normal);
  overflow: hidden;
}

.login-form-wrapper::before {
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
    var(--color-primary),
    transparent
  );
  background-size: 200% 100%;
  animation: shimmer 3s ease-in-out infinite;
}

.login-form-wrapper:hover {
  box-shadow: 
    0 25px 70px rgba(0, 0, 0, 0.5),
    0 0 50px rgba(67, 97, 238, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  border-color: rgba(67, 97, 238, 0.5);
  transform: translateY(-2px);
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h2 {
  font-size: 2.5rem;
  margin: 0 0 0.5rem 0;
  font-weight: 700;
  letter-spacing: 2px;
}

.login-header .glitch {
  color: var(--color-primary);
  text-shadow: 
    0 0 10px rgba(67, 97, 238, 0.5),
    0 0 20px rgba(67, 97, 238, 0.3),
    0 0 30px rgba(67, 97, 238, 0.2);
  animation: pulseGlow 2s ease-in-out infinite;
  display: inline-block;
}

.login-header .system-text {
  color: var(--color-text-primary);
  font-weight: 600;
}

.login-header .subtitle {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  margin-top: 0.5rem;
  letter-spacing: 1px;
}

.login-form {
  margin-top: 2rem;
}

.input-wrapper {
  position: relative;
}

.input-wrapper :deep(.el-input__wrapper) {
  background: rgba(31, 41, 55, 0.6);
  border: 1px solid rgba(67, 97, 238, 0.3);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
}

.input-wrapper :deep(.el-input__wrapper:hover) {
  border-color: rgba(67, 97, 238, 0.5);
  box-shadow: 
    inset 0 2px 4px rgba(0, 0, 0, 0.2),
    0 0 10px rgba(67, 97, 238, 0.2);
}

.input-wrapper :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 
    inset 0 2px 4px rgba(0, 0, 0, 0.2),
    0 0 0 3px rgba(67, 97, 238, 0.2),
    0 0 20px rgba(67, 97, 238, 0.3);
  animation: pulseGlow 2s ease-in-out infinite;
}

.input-wrapper :deep(.el-input__inner) {
  color: var(--color-text-primary);
  background: transparent;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
}

.register-link {
  color: var(--color-primary);
  text-decoration: none;
  transition: all var(--transition-fast);
  position: relative;
}

.register-link::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 1px;
  background: var(--color-primary);
  transition: width var(--transition-fast);
}

.register-link:hover {
  color: var(--color-primary-light);
  text-shadow: 0 0 10px rgba(67, 97, 238, 0.5);
}

.register-link:hover::after {
  width: 100%;
}

.login-btn {
  width: 100%;
  height: 45px;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 1px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border: none;
  border-radius: var(--radius-md);
  box-shadow: 
    0 4px 15px rgba(67, 97, 238, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;
}

.login-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 
    0 6px 20px rgba(67, 97, 238, 0.5),
    0 0 30px rgba(67, 97, 238, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.login-btn:hover:not(:disabled)::before {
  left: 100%;
}

.login-btn:active:not(:disabled) {
  transform: translateY(0);
}

.login-footer {
  text-align: center;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(67, 97, 238, 0.2);
}

.login-footer .version {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  margin: 0;
  letter-spacing: 0.5px;
}

/* 响应式 */
@media (max-width: 480px) {
  .login-form-wrapper {
    padding: 2rem 1.5rem;
    margin: 1rem;
  }
  
  .login-header h2 {
    font-size: 2rem;
  }
}
</style>