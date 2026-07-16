<template>
  <div class="auth-page login-page">
    <div class="auth-layout">
      <section class="auth-intro" aria-labelledby="login-title">
        <p class="auth-eyebrow">个人工作区</p>
        <h1 id="login-title">从上次停下的地方继续。</h1>
        <p class="subtitle">目标、资料和行动都在这里保持连续。登录后，先看一眼今天最值得推进的事。</p>
        <div class="auth-note"><span class="auth-note__mark">V</span><span>你的工作区只展示与你有关的内容。</span></div>
      </section>

      <section class="auth-form-panel" aria-label="登录表单">
        <div class="login-header">
          <h2>登录账号</h2>
          <p>使用用户名或邮箱进入工作区。</p>
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
      
        <div class="login-footer"><span>还没有账号？</span><router-link to="/register" class="link-text">创建一个</router-link></div>
      </section>
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
.auth-page { min-height: calc(100vh - 72px); padding: clamp(32px, 7vw, 88px) clamp(20px, 6vw, 88px); background: var(--bg-page); }
.auth-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(360px, 430px); align-items: center; gap: clamp(48px, 9vw, 150px); width: min(100%, 1060px); margin: 0 auto; }
.auth-intro { max-width: 560px; padding-bottom: 8px; }
.auth-intro h1 { max-width: 520px; margin: 10px 0 16px; color: var(--text-primary); font-size: clamp(32px, 4vw, 52px); line-height: 1.12; letter-spacing: 0; }
.auth-intro .subtitle { max-width: 480px; margin: 0; }
.auth-note { display: flex; align-items: center; gap: 10px; margin-top: 34px; color: var(--text-muted); font-size: 13px; }
.auth-note__mark { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 7px; color: #fff; background: var(--color-primary); font-size: 11px; font-weight: 800; }
.auth-form-panel { padding: 30px; border: 1px solid var(--border-color); border-radius: 10px; background: var(--bg-card); box-shadow: var(--shadow-md); }
.login-header { margin-bottom: 24px; }
.login-header h2 { margin: 0; color: var(--text-primary); font-size: 22px; }
.login-header p { margin: 8px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.5; }

.auth-eyebrow {
  margin: 0 0 8px;
  color: var(--color-primary);
  font-family: var(--font-family-mono);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0;
  letter-spacing: .08em;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 0.95rem;
  letter-spacing: 0;
  line-height: 1.6;
}

.void-form { margin-top: 0; }

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

.form-actions { margin-top: 22px; }

.w-full {
  width: 100%;
}

.login-footer {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 22px;
  color: var(--text-muted);
  font-size: 13px;
}
@media (max-width: 760px) { .auth-page { min-height: calc(100vh - 64px); padding: 36px 18px 52px; }.auth-layout { grid-template-columns: 1fr; gap: 30px; }.auth-intro { max-width: 520px; }.auth-intro h1 { font-size: 34px; }.auth-note { margin-top: 22px; }.auth-form-panel { padding: 24px 20px; } }
</style>
