<template>
  <div class="auth-page register-page">
    <div class="auth-layout">
      <section class="auth-intro" aria-labelledby="register-title">
        <p class="auth-eyebrow">开始建立你的工作区</p>
        <h1 id="register-title">把想法留在一个能继续的地方。</h1>
        <p class="subtitle">创建账号后，目标、资料、行动记录和成长轨迹会一起保存下来。</p>
        <div class="auth-note"><span class="auth-note__mark">V</span><span>先从一个正在关心的方向开始，之后随时可以调整。</span></div>
      </section>

      <section class="auth-form-panel" aria-label="创建账号表单">
        <div class="register-header">
          <h2>创建账号</h2>
          <p>只需要一个称呼、邮箱和登录密码。</p>
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
      
        <div class="register-footer"><span>已经有账号？</span><router-link to="/login" class="link-text">返回登录</router-link></div>
      </section>
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
.auth-page { min-height: calc(100vh - 72px); padding: clamp(32px, 7vw, 88px) clamp(20px, 6vw, 88px); background: var(--bg-page); }
.auth-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(360px, 430px); align-items: center; gap: clamp(48px, 9vw, 150px); width: min(100%, 1060px); margin: 0 auto; }
.auth-intro { max-width: 560px; padding-bottom: 8px; }
.auth-intro h1 { max-width: 520px; margin: 10px 0 16px; color: var(--text-primary); font-size: clamp(32px, 4vw, 52px); line-height: 1.12; letter-spacing: 0; }
.auth-intro .subtitle { max-width: 480px; margin: 0; }
.auth-note { display: flex; align-items: center; gap: 10px; margin-top: 34px; color: var(--text-muted); font-size: 13px; }
.auth-note__mark { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 7px; color: #fff; background: var(--color-primary); font-size: 11px; font-weight: 800; }
.auth-form-panel { padding: 30px; border: 1px solid var(--border-color); border-radius: 10px; background: var(--bg-card); box-shadow: var(--shadow-md); }
.register-header { margin-bottom: 24px; }
.register-header h2 { margin: 0; color: var(--text-primary); font-size: 22px; }
.register-header p { margin: 8px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.5; }

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

.register-footer {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 22px;
  color: var(--text-muted);
  font-size: 13px;
}
@media (max-width: 760px) { .auth-page { min-height: calc(100vh - 64px); padding: 36px 18px 52px; }.auth-layout { grid-template-columns: 1fr; gap: 30px; }.auth-intro { max-width: 520px; }.auth-intro h1 { font-size: 34px; }.auth-note { margin-top: 22px; }.auth-form-panel { padding: 24px 20px; } }
</style>
