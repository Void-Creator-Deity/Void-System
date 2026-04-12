<template>
  <div class="void-page-container profile-page">
    <div class="void-content">
      <header class="page-header">
        <h1 class="logo-text"><span class="void-text-gradient">个人</span> 资料</h1>
        <p class="subtitle">管理您的神经身份与学习轨迹。</p>
      </header>
      
      <div class="profile-layout">
        <!-- Identity Card -->
        <aside class="identity-section">
          <div class="void-card identity-card animate-float">
            <div class="card-status-bar">
              <span class="status-label">链路连接稳定</span>
              <span class="status-indicator online"></span>
            </div>
            
            <div class="avatar-wrapper">
              <div class="void-avatar-hex">
                <span class="avatar-char">{{ userInfo.username ? userInfo.username.charAt(0).toUpperCase() : 'V' }}</span>
              </div>
            </div>
            
            <div class="user-info">
              <h2 class="display-name">{{ userInfo.username || '虚空行者' }}</h2>
              <div class="major-pill">
                {{ majorOptions.find(o => o.value === userInfo.major)?.label || '未设定路径' }}
              </div>
            </div>
            
            <div class="goal-display">
              <span class="section-label">当前指令：</span>
              <p class="directive-text">"{{ userInfo.learningGoal || '当前周期尚未设置目标...' }}"</p>
            </div>
            
            <div class="void-divider"></div>
            
            <div class="system-stats">
              <div class="stat-item">
                <span class="stat-label">UID</span>
                <span class="stat-value mono">{{ userInfo.uid || '---' }}</span>
              </div>
            </div>
          </div>
        </aside>
        
        <!-- Form Card -->
        <main class="form-section">
          <div class="void-card profile-card animate-slide-up">
            <header class="card-header">
              <el-icon><User /></el-icon>
              <h3>神经概况配置</h3>
            </header>
            
            <div class="form-body">
              <div class="form-grid">
                <div class="void-form-group disabled">
                  <label>系统标识符符 (UID)</label>
                  <el-input v-model="userInfo.uid" disabled class="void-input" />
                </div>
                
                <div class="void-form-group disabled">
                  <label>神经链路地址 (邮箱)</label>
                  <el-input v-model="userInfo.email" disabled class="void-input" />
                </div>
                
                <div class="void-form-group">
                  <label>档案别名</label>
                  <el-input 
                    v-model="userInfo.username" 
                    placeholder="输入您的别名..." 
                    class="void-input"
                  />
                  <span v-if="errors.username" class="error-text">{{ errors.username }}</span>
                </div>
                
                <div class="void-form-group">
                  <label>专业化路径</label>
                  <el-select 
                    v-model="userInfo.major" 
                    placeholder="选择专业化..." 
                    class="void-select"
                  >
                    <el-option v-for="option in majorOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                  <span v-if="errors.major" class="error-text">{{ errors.major }}</span>
                </div>

                <div class="void-form-group full-width">
                  <label>核心指令 (学习目标)</label>
                  <el-input 
                    v-model="userInfo.learningGoal" 
                    placeholder="指定您的核心学习目标..." 
                    type="textarea"
                    :rows="4"
                    class="void-input"
                  />
                </div>
              </div>
            </div>
            
            <footer class="card-footer">
              <el-button 
                type="primary" 
                @click="saveUserInfo" 
                :loading="loading.profile" 
                class="void-btn primary big"
              >
                同步配置
              </el-button>
            </footer>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, onMounted } from "vue"
import { ElMessage } from 'element-plus'
import { User, Connection, Monitor, Management } from "@element-plus/icons-vue"
import { getCurrentUser, updateUserProfile } from '../api/user.js'

// ==================== State ====================
const loading = reactive({
  profile: false
})
const errors = reactive({
  username: '',
  major: ''
})

const userInfo = reactive({
  username: '',
  email: '',
  learningGoal: '',
  major: '',
  uid: ''
})

const majorOptions = [
  { label: "计算机科学", value: "computer_science" },
  { label: "数学", value: "mathematics" },
  { label: "物理学", value: "physics" },
  { label: "生物学", value: "biology" },
  { label: "化学", value: "chemistry" },
  { label: "经济学", value: "economics" },
  { label: "心理学", value: "psychology" },
  { label: "其他", value: "other" }
]

// ==================== Logic ====================

const validateForm = () => {
  let isValid = true
  errors.username = ''
  errors.major = ''
  
  if (!userInfo.username?.trim()) {
    errors.username = 'Alias cannot be empty'
    isValid = false
  }
  
  if (!userInfo.major) {
    errors.major = 'Paths must be defined'
    isValid = false
  }
  
  return isValid
}

const saveUserInfo = async () => {
  if (!validateForm()) return
  
  loading.profile = true
  try {
    const response = await updateUserProfile(userInfo)
    if (response.success) {
      ElMessage.success('Neural profile synchronized')
    } else {
      ElMessage.error(response.message || 'Synchronization failed')
    }
  } catch (error) {
    ElMessage.error('Link unstable. Persist failed.')
  } finally {
    loading.profile = false
  }
}

const loadUserInfo = async () => {
  try {
    const userData = await getCurrentUser()
    userInfo.username = userData.username || 'Learner'
    userInfo.email = userData.email || ''
    userInfo.uid = userData.user_id || ''
    userInfo.learningGoal = userData.learning_goal || ''
    userInfo.major = userData.specialization || ''
  } catch (error) {
    console.error('[PROFILE_SHARD_LOAD_FAIL]', error)
    if (!userInfo.username) userInfo.username = 'Learner'
  }
}

onMounted(() => {
  loadUserInfo()
})
</script>

<style scoped>
.profile-page {
  background: var(--bg-page);
  min-height: 100vh;
}

.void-content {
  padding: var(--spacing-xxl) 0;
}

.page-header {
  margin-bottom: var(--spacing-xxl);
}

.subtitle {
  color: var(--text-muted);
  font-size: 1.1rem;
}

.profile-layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: var(--spacing-xxl);
  align-items: start;
}

/* Identity Card */
.identity-card {
  padding: var(--spacing-xl);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.card-status-bar {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  font-family: var(--font-family-mono);
  font-size: 0.75rem;
  color: var(--color-primary);
  letter-spacing: 1px;
}

.status-indicator.online {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 10px var(--color-success);
}

.avatar-wrapper {
  margin-bottom: var(--spacing-xl);
}

.void-avatar-hex {
  width: 120px;
  height: 120px;
  background: var(--void-gradient);
  clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.void-avatar-hex::after {
  content: '';
  position: absolute;
  inset: 4px;
  background: var(--bg-card);
  clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
  z-index: 0;
}

.avatar-char {
  font-size: 3rem;
  font-weight: 800;
  color: var(--color-primary);
  position: relative;
  z-index: 1;
  text-shadow: 0 0 15px var(--color-primary-transparent);
}

.user-info {
  text-align: center;
  margin-bottom: var(--spacing-xl);
}

.display-name {
  font-size: 1.75rem;
  margin-bottom: var(--spacing-xs);
  letter-spacing: -0.5px;
}

.major-pill {
  display: inline-block;
  padding: 4px 16px;
  background: var(--color-primary-transparent);
  border: 1px solid var(--color-primary);
  border-radius: 20px;
  color: var(--color-primary);
  font-size: 0.85rem;
  font-weight: 700;
}

.goal-display {
  width: 100%;
  background: var(--bg-tertiary);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-xl);
}

.section-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: var(--spacing-sm);
}

.directive-text {
  font-size: 1rem;
  color: var(--text-main);
  font-style: italic;
  line-height: 1.5;
}

.system-stats {
  width: 100%;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.stat-value.mono {
  font-family: var(--font-family-mono);
  font-size: 0.85rem;
  color: var(--color-primary-light);
}

/* Form Card */
.profile-card {
  padding: var(--spacing-xl);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xxl);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--border-color-light);
}

.card-header h3 {
  font-size: 1.5rem;
  margin: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xl);
}

.full-width {
  grid-column: span 2;
}

.card-footer {
  margin-top: var(--spacing-xxl);
  padding-top: var(--spacing-xl);
  border-top: 1px solid var(--border-color-light);
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  
  .full-width {
    grid-column: span 1;
  }
}
xt {
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  position: relative;
  z-index: 1;
}

.avatar-status {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 3px solid rgba(10, 13, 32, 0.9);
  box-shadow: 0 0 10px rgba(0, 255, 102, 0.5);
  transition: all 0.3s ease;
}

.status-online {
  background: #00ff66;
  box-shadow: 
    0 0 15px #00ff66,
    inset 0 0 10px rgba(0, 255, 102, 0.5);
  animation: statusPulse 2s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 
      0 0 15px #00ff66,
      inset 0 0 10px rgba(0, 255, 102, 0.5);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 
      0 0 20px #00ff66,
      inset 0 0 10px rgba(0, 255, 102, 0.5);
  }
}

.user-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* 配置组样式 */
.config-group {
  margin-bottom: 2.5rem;
  padding: 2rem;
  background: rgba(10, 13, 32, 0.6);
  border-radius: 16px;
  border: 1px solid var(--border-color);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  backdrop-filter: blur(10px);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.15),
    inset 0 0 0 1px rgba(255, 255, 255, 0.03);
  overflow: hidden;
}

.config-group::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: var(--accent-primary);
  opacity: 0.6;
  transform: translateX(-100%);
  transition: transform 0.4s ease;
}

.config-group:hover {
  background: rgba(10, 13, 32, 0.7);
  border-color: var(--accent-primary);
  transform: translateX(5px);
  box-shadow: 
    0 6px 25px rgba(0, 0, 0, 0.2),
    0 0 15px var(--accent-glow),
    inset 0 0 0 1px rgba(255, 255, 255, 0.05);
}

.config-group:hover::before {
  transform: translateX(0);
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  position: relative;
}

.config-header h4 {
  margin: 0;
  color: rgba(255, 255, 255, 0.95);
  font-weight: 700;
  font-size: 1.15rem;
  letter-spacing: 0.5px;
  text-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* 开关样式增强 */
.config-header :deep(.el-switch) {
  --el-switch-on-color: var(--accent-primary);
  --el-switch-off-color: var(--border-color);
  transition: all 0.3s ease;
}

.config-header :deep(.el-switch:hover) {
  transform: scale(1.05);
}

.config-header :deep(.el-switch__core) {
  box-shadow: 0 0 10px var(--accent-glow);
  border-radius: 20px;
}

.config-header :deep(.el-switch.is-checked .el-switch__core) {
  box-shadow: 
    0 0 10px var(--accent-primary),
    inset 0 0 10px var(--accent-glow);
}

.config-details {
  padding-left: 1rem;
  border-left: 2px solid var(--border-color);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.config-group:hover .config-details {
  border-left-color: var(--accent-primary);
  padding-left: 1.5rem;
}

/* 详细组 */
.detail-group {
  margin-bottom: 2rem;
  position: relative;
  transition: all 0.3s ease;
}

.detail-group::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, rgba(0, 153, 255, 0.05), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.detail-group:hover::before {
  opacity: 1;
}

.detail-group label {
  display: block;
  margin-bottom: 0.75rem;
  color: rgba(220, 220, 240, 0.9);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  opacity: 0.9;
  transition: all 0.3s ease;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.detail-group:hover label {
  color: var(--accent-primary);
  opacity: 1;
  text-shadow: 0 0 10px var(--accent-glow);
}

/* 颜色选项 - 增强交互 */
.color-options {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.color-option {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 3px solid transparent;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
}

.color-option::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: currentColor;
  opacity: 0;
  transform: translate(-50%, -50%);
  transition: all 0.3s ease;
}

.color-option:hover {
  transform: scale(1.15);
  box-shadow: 
    0 0 20px rgba(0, 0, 0, 0.3),
    0 0 15px var(--accent-glow);
}

.color-option.active {
  border-color: var(--text-primary);
  box-shadow: 
    0 0 25px var(--accent-primary),
    0 0 15px var(--accent-glow),
    inset 0 2px 10px rgba(0, 0, 0, 0.3);
  transform: scale(1.05);
}

.color-option.active::before {
  width: 12px;
  height: 12px;
  opacity: 1;
}

/* 信息内容区域 */
.info-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-bottom: 2rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.75rem;
  background: rgba(10, 13, 32, 0.75);
  border-radius: 16px;
  border: 1px solid var(--border-color);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(10px);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.15),
    inset 0 0 0 1px rgba(255, 255, 255, 0.03);
}

.info-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--accent-primary);
  transform: translateX(-100%);
  transition: all 0.4s ease;
  box-shadow: 0 0 10px var(--accent-primary);
}

.info-item::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 100px;
  background: linear-gradient(90deg, transparent, rgba(0, 153, 255, 0.05), transparent);
  transform: translateX(100%);
  transition: transform 0.6s ease;
}

.info-item:hover {
  background: rgba(10, 13, 32, 0.9);
  border-color: var(--accent-primary);
  transform: translateX(5px);
  box-shadow: 
    0 6px 25px rgba(0, 0, 0, 0.2),
    0 0 15px var(--accent-glow),
    inset 0 0 0 1px rgba(255, 255, 255, 0.05);
}

.info-item:hover::before {
  transform: translateX(0);
}

.info-item:hover::after {
  transform: translateX(-100%);
}

.info-label {
  color: rgba(180, 180, 200, 0.8);
  font-size: 0.95rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
  position: relative;
  z-index: 1;
}

.info-item:hover .info-label {
  color: var(--accent-primary);
  text-shadow: 0 0 10px var(--accent-glow);
}

.info-value {
  color: rgba(255, 255, 255, 0.98);
  font-weight: 700;
  font-size: 1.05rem;
  text-align: right;
  min-width: 120px;
  text-shadow: 0 0 15px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  position: relative;
  z-index: 1;
}

.info-item:hover .info-value {
  text-shadow: 
    0 0 10px rgba(0, 153, 255, 0.3),
    0 0 15px rgba(0, 0, 0, 0.15);
}

.status-online {
  color: #00ff66;
  text-shadow: 
    0 0 15px #00ff66,
    0 0 25px rgba(0, 255, 102, 0.6);
  font-weight: 700;
  animation: statusTextGlow 2s ease-in-out infinite;
}

@keyframes statusTextGlow {
  0%, 100% {
    text-shadow: 
      0 0 15px #00ff66,
      0 0 25px rgba(0, 255, 102, 0.6);
  }
  50% {
    text-shadow: 
      0 0 25px #00ff66,
      0 0 35px rgba(0, 255, 102, 0.8);
  }
}

.status-offline {
  color: #ff6b6b;
  text-shadow: 
    0 0 15px #ff6b6b,
    0 0 25px rgba(255, 107, 107, 0.6);
}

/* 卡片操作按钮 - 现代按钮设计 */
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1.5rem;
  padding-top: 2.5rem;
  margin-top: 2.5rem;
  border-top: 1px solid var(--border-color);
  position: relative;
}

.card-actions::before {
  content: '';
  position: absolute;
  top: -1px;
  left: 0;
  width: 80px;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 3px;
  animation: buttonBorderGlow 3s ease-in-out infinite;
}

@keyframes buttonBorderGlow {
  0%, 100% {
    opacity: 0.7;
    width: 80px;
  }
  50% {
    opacity: 1;
    width: 120px;
    box-shadow: 0 0 10px var(--accent-primary);
  }
}

.card-actions :deep(.el-button--primary) {
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  border: none;
  color: white;
  font-weight: 700;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  padding: 0.85rem 2.25rem;
  border-radius: 10px;
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 
    0 6px 25px rgba(0, 0, 0, 0.3),
    0 0 20px var(--accent-glow),
    inset 0 1px 3px rgba(255, 255, 255, 0.2);
}

.card-actions :deep(.el-button--primary:hover) {
  box-shadow: 
    0 8px 30px rgba(0, 0, 0, 0.4),
    0 0 35px var(--accent-primary),
    inset 0 1px 3px rgba(255, 255, 255, 0.2);
  transform: translateY(-3px);
  filter: brightness(1.1);
}

.card-actions :deep(.el-button--primary:active) {
  transform: translateY(-1px);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.3),
    0 0 25px var(--accent-glow),
    inset 0 1px 3px rgba(255, 255, 255, 0.2);
}

.card-actions :deep(.el-button--primary)::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: all 0.6s ease;
}

.card-actions :deep(.el-button--primary:hover)::before {
  left: 100%;
}

.card-actions :deep(.el-button) {
  background: rgba(10, 13, 32, 0.75);
  border: 1px solid var(--border-color);
  color: rgba(255, 255, 255, 0.95);
  font-weight: 600;
  padding: 0.85rem 2.25rem;
  border-radius: 10px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(10px);
  box-shadow: inset 0 1px 3px rgba(255, 255, 255, 0.05);
}

.card-actions :deep(.el-button:hover) {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  box-shadow: 
    0 6px 25px rgba(0, 0, 0, 0.2),
    0 0 20px var(--accent-glow),
    inset 0 1px 3px rgba(255, 255, 255, 0.05);
  background: rgba(10, 13, 32, 0.9);
  transform: translateY(-2px);
}

.card-actions :deep(.el-button:active) {
  transform: translateY(0);
}

.card-actions :deep(.el-button--danger) {
  background: rgba(255, 51, 102, 0.15);
  border-color: rgba(255, 51, 102, 0.3);
  color: #ff3366;
  box-shadow: inset 0 1px 3px rgba(255, 51, 102, 0.1);
}

.card-actions :deep(.el-button--danger:hover) {
  background: rgba(255, 51, 102, 0.25);
  border-color: #ff3366;
  box-shadow: 
    0 0 25px rgba(255, 51, 102, 0.4),
    inset 0 1px 3px rgba(255, 51, 102, 0.2);
  color: white;
  transform: translateY(-2px);
}

.card-actions :deep(.el-button--warning) {
  background: rgba(255, 204, 0, 0.15);
  border-color: rgba(255, 204, 0, 0.3);
  color: #ffcc00;
  box-shadow: inset 0 1px 3px rgba(255, 204, 0, 0.1);
}

.card-actions :deep(.el-button--warning:hover) {
  background: rgba(255, 204, 0, 0.25);
  border-color: #ffcc00;
  box-shadow: 
    0 0 25px rgba(255, 204, 0, 0.4),
    inset 0 1px 3px rgba(255, 204, 0, 0.2);
  color: white;
  transform: translateY(-2px);
}

/* 错误信息样式 */
.error-message {
  color: #ff6b6b;
  font-size: 0.9rem;
  margin-top: 0.5rem;
  min-height: 1.5rem;
  position: relative;
  padding-left: 1.5rem;
  text-shadow: 0 0 10px rgba(255, 107, 107, 0.3);
}

.error-message::before {
  content: '⚠';
  position: absolute;
  left: 0;
  top: 0;
  font-size: 0.9rem;
}

/* 自定义开关样式 */
:deep(.el-switch.is-checked .el-switch__core) {
  background-color: var(--accent-primary);
  box-shadow: 0 0 15px var(--accent-glow);
}

:deep(.el-switch__core) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 自定义滑块样式 */
:deep(.el-slider__runway) {
  background-color: var(--border-color);
  height: 8px;
  border-radius: 4px;
}

:deep(.el-slider__bar) {
  background-color: var(--accent-primary);
  height: 8px;
  border-radius: 4px;
  box-shadow: 0 0 10px var(--accent-glow);
}

:deep(.el-slider__button) {
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  border: none;
  box-shadow: 
    0 0 20px var(--accent-primary),
    0 2px 10px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

:deep(.el-slider__button:hover) {
  transform: scale(1.2);
  box-shadow: 
    0 0 30px var(--accent-primary),
    0 2px 10px rgba(0, 0, 0, 0.3);
}

/* 自定义单选按钮样式 */
:deep(.el-radio__inner) {
  border-color: var(--border-color);
  transition: all 0.3s ease;
}

:deep(.el-radio__input.is-checked .el-radio__inner) {
  background-color: var(--accent-primary);
  border-color: var(--accent-primary);
  box-shadow: 0 0 10px var(--accent-glow);
}

:deep(.el-radio__label) {
  color: var(--text-secondary);
  transition: color 0.3s ease;
}

:deep(.el-radio__input.is-checked .el-radio__label) {
  color: var(--accent-primary);
  font-weight: 500;
}

/* 自定义复选框样式 */
:deep(.el-checkbox__inner) {
  border-color: var(--border-color);
  background-color: var(--bg-input);
  transition: all 0.3s ease;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--accent-primary);
  border-color: var(--accent-primary);
  box-shadow: 0 0 10px var(--accent-glow);
}

:deep(.el-checkbox__label) {
  color: var(--text-secondary);
  transition: color 0.3s ease;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__label) {
  color: var(--accent-primary);
  font-weight: 500;
}

/* 动画效果 */
@keyframes glitchEffect {
  0%, 90%, 100% {
    text-shadow: 
      0 0 10px var(--accent-primary),
      0 0 20px var(--accent-primary),
      0 0 40px var(--accent-glow);
    transform: translate(0);
  }
  91% {
    text-shadow: 
      -2px 0 5px rgba(255, 0, 0, 0.5),
      2px 0 5px rgba(0, 255, 255, 0.5);
    transform: translate(-2px, 2px);
  }
  92% {
    text-shadow: 
      2px 0 5px rgba(0, 255, 255, 0.5),
      -2px 0 5px rgba(255, 0, 0, 0.5);
    transform: translate(2px, -2px);
  }
  93% {
    text-shadow: 
      0 0 10px var(--accent-primary),
      0 0 20px var(--accent-primary),
      0 0 40px var(--accent-glow);
    transform: translate(0);
  }
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%) skewX(-20deg);
  }
  100% {
    transform: translateX(100%) skewX(-20deg);
  }
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 
      0 0 25px var(--accent-glow),
      inset 0 2px 10px rgba(255, 255, 255, 0.3);
  }
  50% {
    box-shadow: 
      0 0 40px var(--accent-primary),
      inset 0 2px 10px rgba(255, 255, 255, 0.3);
  }
}

@keyframes statusPulse {
  0%, 100% {
    box-shadow: 0 0 15px #00ff66;
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 25px #00ff66, 0 0 35px rgba(0, 255, 102, 0.5);
    transform: scale(1.1);
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

</style>
