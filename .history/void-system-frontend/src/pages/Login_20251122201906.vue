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
  background: linear-gradient(135deg, #0a0d20 0%, #1a1d3a 100%);
  position: relative;
  overflow: hidden;
}

.login-form-wrapper {
  width: 100%;
  max-width: 400px;
  background: rgba(19, 21, 36, 0.85);
  border: 1px solid rgba(0, 204, 255, 0.2);
  border-radius: 12px;
  padding: 2.5rem;
  box-shadow: 0 0 60px rgba(0, 204, 255, 0.15);
  backdrop-filter: blur(10px);
}

/* 其他样式省略... */
</style>