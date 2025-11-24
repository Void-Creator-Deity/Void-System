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
/* 样式类似于Login.vue */
</style>