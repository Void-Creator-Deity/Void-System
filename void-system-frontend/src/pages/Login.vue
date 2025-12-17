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

      console.log('登录响应数据:', result)
      console.log('检查token存储:', localStorage.getItem('access_token'))
      console.log('检查用户信息存储:', localStorage.getItem('user_info'))

      // 处理"记住我"功能
      if (loginForm.rememberMe) {
        localStorage.setItem('remembered_user', loginForm.username)
      } else {
        localStorage.removeItem('remembered_user')
      }

      // 验证数据是否正确存储
      const storedToken = localStorage.getItem('access_token')
      const storedUserInfo = localStorage.getItem('user_info')

      if (!storedToken) {
        throw new Error('Token存储失败')
      }

      ElMessage.success('登录成功')

      // 短暂延迟确保数据持久化
      await new Promise(resolve => setTimeout(resolve, 50))
      router.push('/')
    } catch (error) {
      console.error('登录失败:', error)
      // 处理后端返回的错误格式
      const errorData = error.response?.data
      let errorMessage = '登录失败，请检查用户名和密码'

      if (errorData) {
        if (typeof errorData === 'string') {
          errorMessage = errorData
        } else if (errorData.message) {
          errorMessage = errorData.message
        } else if (errorData.detail) {
          errorMessage = errorData.detail
        }
      }

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

.login-container::before {
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

.login-form-wrapper {
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
    var(--color-accent),
    var(--color-primary),
    transparent
  );
  background-size: 200% 100%;
  animation: shimmer 4s ease-in-out infinite;
  opacity: 0.8;
}

.login-form-wrapper:hover {
  box-shadow: 
    0 28px 72px rgba(0, 0, 0, 0.55),
    0 0 80px rgba(99, 102, 241, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  border-color: rgba(99, 102, 241, 0.5);
  transform: translateY(-3px) scale(1.01);
}

.login-header {
  text-align: center;
  margin-bottom: 2.5rem;
  position: relative;
}

.login-header h2 {
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

.login-header .glitch {
  color: var(--color-primary);
  text-shadow: 
    0 0 15px rgba(99, 102, 241, 0.6),
    0 0 30px rgba(99, 102, 241, 0.4),
    0 0 45px rgba(99, 102, 241, 0.2);
  animation: pulseGlow 2.5s ease-in-out infinite;
  display: inline-block;
}

.login-header .system-text {
  color: var(--color-text-primary);
  font-weight: 600;
}

.login-header .subtitle {
  color: var(--color-text-secondary);
  font-size: 1rem;
  margin-top: 0.75rem;
  letter-spacing: 1.2px;
  opacity: 0.8;
}

.login-form {
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
  justify-content: space-between;
  align-items: center;
  font-size: 0.95rem;
  margin-bottom: 1.75rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.form-actions :deep(.el-checkbox) {
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.form-actions :deep(.el-checkbox:hover) {
  color: var(--color-text-primary);
}

.form-actions :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
}

.register-link {
  color: var(--color-primary);
  text-decoration: none;
  transition: all var(--transition-normal);
  position: relative;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.register-link::after {
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

.register-link:hover {
  color: var(--color-primary-light);
  text-shadow: 0 0 15px rgba(99, 102, 241, 0.5);
  transform: translateY(-1px);
}

.register-link:hover::after {
  width: 100%;
}

.login-btn {
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

.login-btn::before {
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

.login-btn:hover:not(:disabled) {
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

.login-btn:hover:not(:disabled)::before {
  left: 100%;
}

.login-btn:active:not(:disabled) {
  transform: translateY(-1px) scale(0.99);
  box-shadow: 
    0 4px 16px rgba(99, 102, 241, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.login-btn > * {
  position: relative;
  z-index: 2;
}

.login-footer {
  text-align: center;
  margin-top: 2.5rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(99, 102, 241, 0.2);
}

.login-footer .version {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  margin: 0;
  letter-spacing: 0.8px;
  opacity: 0.7;
  transition: all var(--transition-fast);
}

.login-footer .version:hover {
  opacity: 1;
  color: var(--color-text-secondary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-form-wrapper {
    padding: 2.5rem 2rem;
    margin: 1.5rem;
    max-width: calc(100% - 3rem);
  }
  
  .login-header h2 {
    font-size: 2.25rem;
    letter-spacing: 2px;
  }
  
  .login-header .subtitle {
    font-size: 0.95rem;
  }
  
  .form-actions {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }
  
  .form-actions :deep(.el-checkbox) {
    align-self: flex-start;
  }
  
  .register-link {
    align-self: flex-end;
  }
}

@media (max-width: 480px) {
  .login-form-wrapper {
    padding: 2rem 1.5rem;
    margin: 1rem;
    max-width: calc(100% - 2rem);
  }
  
  .login-header h2 {
    font-size: 2rem;
    letter-spacing: 1.5px;
  }
  
  .login-header .subtitle {
    font-size: 0.9rem;
  }
  
  .login-form {
    margin-top: 2rem;
  }
  
  .input-wrapper :deep(.el-input__wrapper) {
    padding: 0.375rem 0.75rem;
  }
  
  .login-btn {
    height: 48px;
    font-size: 1rem;
    letter-spacing: 1.2px;
  }
}
</style>