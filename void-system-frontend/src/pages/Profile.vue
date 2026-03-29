<template>
  <div class="settings-container">
    <!-- 页面标题 -->
    <div class="settings-header">
      <h2><span class="glitch">个人</span> <span class="system-text">资料</span></h2>
      <p class="subtitle">管理您的档案和学习目标</p>
    </div>
    
    <div class="profile-layout">
      <!-- 左侧身份卡 -->
      <div class="settings-card id-card">
        <div class="id-card-header">
          <span class="id-label">VOID_ID_AUTH</span>
          <span class="id-status online"></span>
        </div>
        <div class="avatar-container">
          <div class="avatar">
            <span class="avatar-text">{{ userInfo.username ? userInfo.username.charAt(0).toUpperCase() : 'U' }}</span>
          </div>
        </div>
        
        <h3 class="user-display-name">{{ userInfo.username || '未知执行者' }}</h3>
        <p class="user-major-badge">{{ majorOptions.find(o => o.value === userInfo.major)?.label || '未定专业' }}</p>
        
        <div class="user-goal-display">
          <span class="goal-label">当前运行指令:</span>
          <p class="goal-text">"{{ userInfo.learningGoal || '尚未设定目标指令...' }}"</p>
        </div>
        
        <div class="cyber-lines">
          <div class="line"></div>
          <div class="line short"></div>
          <div class="line"></div>
        </div>
      </div>
      
      <!-- 右侧设定表单 -->
      <div class="settings-card profile-main">
        <div class="card-header">
          <div class="header-icon">🛡️</div>
          <h3>实体档案设定</h3>
        </div>
        
        <div class="user-details" style="flex:1;">
          <div class="detail-row" style="display:flex; gap:1.5rem; margin-bottom:1.5rem;">
            <div class="detail-group" style="flex:1;">
              <label>系统编号(UID)</label>
              <el-input 
                v-model="userInfo.uid" 
                readonly
                disabled
                class="form-input read-only-input"
              />
            </div>
            <div class="detail-group" style="flex:1;">
              <label>接入邮箱</label>
              <el-input 
                v-model="userInfo.email" 
                readonly
                disabled
                class="form-input read-only-input"
              />
            </div>
          </div>

          <div class="detail-group">
            <label>用户名</label>
            <el-input 
              v-model="userInfo.username" 
              placeholder="输入对外显示的档案代号" 
              class="form-input"
              :validate-event="false"
            />
            <div v-if="errors.username" class="error-message">{{ errors.username }}</div>
          </div>
          
          <div class="detail-group">
            <label>目标指令 (Learning Objective)</label>
            <el-input 
              v-model="userInfo.learningGoal" 
              placeholder="输入最高优先级的学习目标..." 
              class="form-input"
              type="textarea"
              :rows="3"
            />
          </div>
          
          <div class="detail-group">
            <label>专精领域 (Expertise Area) *</label>
            <el-select 
              v-model="userInfo.major" 
              placeholder="选择你的进阶修习领域" 
              class="form-select"
              :validate-event="false"
            >
              <el-option v-for="option in majorOptions" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
            <div v-if="errors.major" class="error-message">{{ errors.major }}</div>
          </div>
        </div>
        
        <div class="card-actions" style="margin-top: 2rem; justify-content: flex-end;">
          <el-button type="primary" @click="saveUserInfo" :loading="loading.profile" class="cyber-btn" size="large">同步更新档案</el-button>
        </div>
      </div>
    </div>
    
  </div>
</template>

<script setup>
/**
 * Profile Component
 * ------------------
 * 用户资料页面
 */

import { reactive, onMounted } from "vue"
import { ElMessage } from 'element-plus'
import { getCurrentUser, updateUserProfile } from '../api/user.js'

// ==================== 响应式状态 ====================
const loading = reactive({
  profile: false
})
const errors = reactive({
  username: '',
  major: ''
})

// ==================== 数据模型 ====================

// 用户信息
const userInfo = reactive({
  username: '',
  email: '',
  learningGoal: '',
  major: '',
  uid: ''
})

// ==================== 配置选项 ====================

// 专业选项
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

// ==================== 业务逻辑 ====================

/**
 * 验证表单
 * @returns {boolean} 表单是否有效
 */
const validateForm = () => {
  let isValid = true
  
  // 重置错误信息
  errors.username = ''
  errors.major = ''
  
  // 验证用户名
  if (!userInfo.username || userInfo.username.trim() === '') {
    errors.username = '用户名不能为空'
    isValid = false
  }
  
  // 验证专业领域
  if (!userInfo.major) {
    errors.major = '请选择专业领域'
    isValid = false
  }
  
  return isValid
}

/**
 * 保存用户信息
 */
const saveUserInfo = async () => {
  if (!validateForm()) {
    ElMessage.warning('请修正表单中的错误后再保存')
    return
  }
  
  loading.profile = true
  try {
    const response = await updateUserProfile(userInfo)
    if (response.success) {
      ElMessage.success('用户信息保存成功')
    } else {
      ElMessage.error(response.message || '保存失败')
    }
  } catch (error) {
    console.error('保存用户信息失败:', error)
    ElMessage.error('保存失败，请检查网络或稍后重试')
  } finally {
    loading.profile = false
  }
}





/**
 * 加载用户信息
 */
const loadUserInfo = async () => {
  try {
    const userData = await getCurrentUser()
    
    // 更新用户信息 (数据已经是接口返回的 data 内容)
    userInfo.username = userData.username || '学习者'
    userInfo.email = userData.email || ''
    userInfo.uid = userData.user_id || ''
    userInfo.learningGoal = userData.learning_goal || ''
    userInfo.major = userData.specialization || ''
  } catch (error) {
    console.error('加载用户信息失败:', error)
    // 失败时保持现有的或使用默认占位
    if (!userInfo.username) userInfo.username = '学习者'
  }
}
    
// ==================== 生命周期 ====================

// 组件挂载时
onMounted(() => {
  // 加载用户信息
  loadUserInfo()
})
</script>

<style scoped>
/* 现代化设置页面样式 - 基于高端赛博朋克设计 */

/* 页面容器 */
.settings-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* 背景装饰元素 */
.settings-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: -10%;
  width: 120%;
  height: 300px;
  background: radial-gradient(circle at center, var(--accent-glow) 0%, transparent 60%);
  filter: blur(80px);
  z-index: -1;
  opacity: 0.3;
  animation: backgroundGlow 8s ease-in-out infinite;
}

@keyframes backgroundGlow {
  0%, 100% {
    transform: scale(1);
    opacity: 0.3;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.4;
  }
}

/* 页面标题 - 科技感标题 */
.settings-header {
  text-align: center;
  margin-bottom: 2rem;
  position: relative;
  animation: fadeIn 0.8s ease-out;
  background: rgba(10, 13, 32, 0.7);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid var(--border-color);
  padding: 2rem;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.15),
    0 0 20px rgba(0, 153, 255, 0.05);
  overflow: hidden;
}

.settings-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  animation: headerGlow 4s ease-in-out infinite;
}

@keyframes headerGlow {
  0%, 100% {
    background-position: -200% 0;
  }
  50% {
    background-position: 200% 0;
  }
}

.settings-header h2 {
  font-size: 3rem;
  margin-bottom: 0.8rem;
  letter-spacing: 1px;
  font-weight: 800;
  line-height: 1.2;
  position: relative;
  display: inline-block;
  text-shadow: 0 0 20px var(--accent-glow);
}

.glitch {
  color: var(--accent-primary);
  text-shadow: 
    0 0 10px var(--accent-primary),
    0 0 20px var(--accent-primary),
    0 0 40px var(--accent-glow);
  animation: glitchEffect 5s infinite;
}

.system-text {
  color: var(--text-primary);
  font-weight: 700;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
}

.subtitle {
  color: rgba(220, 220, 240, 0.8);
  font-size: 1.2rem;
  font-weight: 400;
  max-width: 700px;
  margin: 0 auto;
  opacity: 0.9;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

/* 标签页样式 - 现代化导航 */
.settings-tabs {
  background: transparent;
  margin-bottom: 2rem;
  position: relative;
}

.settings-tabs :deep(.el-tabs__header) {
  margin-bottom: 2rem;
  display: flex;
  justify-content: center;
}

.settings-tabs :deep(.el-tabs__nav) {
  background: rgba(16, 25, 54, 0.75);
  padding: 0.5rem;
  border-radius: 16px;
  border: 1px solid var(--border-color);
  backdrop-filter: blur(15px);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.2),
    0 0 15px var(--accent-glow),
    inset 0 0 0 1px rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
  animation: navGlow 3s ease-in-out infinite alternate;
}

@keyframes navGlow {
  0% {
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.2),
      0 0 15px var(--accent-glow),
      inset 0 0 0 1px rgba(255, 255, 255, 0.05);
  }
  100% {
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.25),
      0 0 20px var(--accent-primary),
      inset 0 0 0 1px rgba(255, 255, 255, 0.08);
  }
}

.settings-tabs :deep(.el-tabs__nav)::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0.7;
  animation: tabHeaderGlow 3s ease-in-out infinite;
}

@keyframes tabHeaderGlow {
  0%, 100% {
    background-position: -200% 0;
  }
  50% {
    background-position: 200% 0;
  }
}

.settings-tabs :deep(.el-tabs__item) {
  color: rgba(200, 200, 220, 0.7);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 0.85rem 2.25rem;
  margin: 0;
  font-weight: 500;
  font-size: 1rem;
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  backdrop-filter: blur(5px);
}

.settings-tabs :deep(.el-tabs__item)::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.05);
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: -1;
}

.settings-tabs :deep(.el-tabs__item::after) {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background: var(--accent-primary);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  transform: translateX(-50%);
  box-shadow: 0 0 10px var(--accent-primary);
}

.settings-tabs :deep(.el-tabs__item:hover) {
  color: var(--accent-primary);
  background: rgba(255, 255, 255, 0.08);
  opacity: 1;
  transform: translateY(-1px);
}

.settings-tabs :deep(.el-tabs__item:hover::before) {
  opacity: 1;
}

.settings-tabs :deep(.el-tabs__item:hover::after) {
  width: 80%;
}

.settings-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent-primary);
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 
    0 4px 15px rgba(0, 0, 0, 0.3),
    0 0 15px var(--accent-glow),
    inset 0 0 0 1px rgba(255, 255, 255, 0.05);
  font-weight: 600;
  transform: translateY(-1px);
}

.settings-tabs :deep(.el-tabs__item.is-active::after) {
  width: 80%;
}

.settings-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

/* 设置卡片 - 玻璃态设计 */
.settings-card {
  background: rgba(16, 25, 54, 0.75);
  border: 1px solid var(--border-color);
  border-radius: 18px;
  padding: 2.5rem;
  margin-bottom: 2rem;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(20px);
  box-shadow: 
    0 12px 40px rgba(0, 0, 0, 0.25),
    0 0 20px rgba(0, 153, 255, 0.08),
    inset 0 0 0 1px rgba(255, 255, 255, 0.05);
}

.settings-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  animation: cardHeaderGlow 4s ease-in-out infinite;
  opacity: 0.8;
}

@keyframes cardHeaderGlow {
  0%, 100% {
    background-position: -200% 0;
  }
  50% {
    background-position: 200% 0;
  }
}

.settings-card:hover {
  transform: translateY(-5px);
  box-shadow: 
    0 15px 45px rgba(0, 0, 0, 0.3),
    0 0 30px var(--accent-glow),
    inset 0 0 0 1px rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
}

.settings-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 50% -20%, rgba(0, 153, 255, 0.15), transparent 70%);
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.settings-card:hover::after {
  opacity: 1;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  position: relative;
}

.card-header::after {
  content: '';
  position: absolute;
  bottom: -1rem;
  left: 0;
  width: 60px;
  height: 2px;
  background: var(--accent-primary);
  opacity: 0.7;
}

.settings-card:hover::before {
  opacity: 0.2;
}

.settings-card:hover {
  border-color: var(--accent-primary);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.3),
    0 0 20px var(--accent-glow),
    inset 0 0 0 1px rgba(255, 255, 255, 0.1);
  transform: translateY(-4px);
}

/* 卡片头部 - 增强视觉层次 */
.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border-color);
  position: relative;
}

.card-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 60px;
  height: 3px;
  background: var(--accent-primary);
  border-radius: 3px;
}

.header-icon {
  font-size: 1.8rem;
  color: var(--accent-primary);
  filter: drop-shadow(0 0 8px var(--accent-glow));
  animation: float 4s ease-in-out infinite;
}

.card-header h3 {
  font-family: var(--main-font);
  font-weight: 700;
  color: rgba(255, 255, 255, 0.98);
  margin: 0;
  text-shadow: 
    0 1px 3px rgba(0, 0, 0, 0.3),
    0 0 10px var(--accent-glow);
  font-size: 1.5rem;
  letter-spacing: 0.5px;
}

/* 表单样式 - 玻璃态输入控件 */
.form-input :deep(.el-input__wrapper) {
  background: rgba(10, 13, 32, 0.75);
  border: 1px solid var(--border-color);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 
    inset 0 1px 3px rgba(0, 0, 0, 0.3),
    0 1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
}

.form-input :deep(.el-input__wrapper)::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  opacity: 0.5;
}

.form-input :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary);
  background: rgba(10, 13, 32, 0.85);
  box-shadow: 
    inset 0 1px 3px rgba(0, 0, 0, 0.3),
    0 0 15px var(--accent-glow),
    0 1px 0 rgba(255, 255, 255, 0.05);
  transform: translateY(-1px);
}

.form-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: 
    inset 0 1px 3px rgba(0, 0, 0, 0.3),
    0 0 25px var(--accent-primary),
    0 0 15px var(--accent-glow),
    0 1px 0 rgba(255, 255, 255, 0.05);
  background: rgba(10, 13, 32, 0.95);
  transform: translateY(-2px);
  animation: inputGlow 2s ease-in-out infinite alternate;
}

@keyframes inputGlow {
  0% {
    box-shadow: 
      inset 0 1px 3px rgba(0, 0, 0, 0.3),
      0 0 25px var(--accent-primary),
      0 0 15px var(--accent-glow),
      0 1px 0 rgba(255, 255, 255, 0.05);
  }
  100% {
    box-shadow: 
      inset 0 1px 3px rgba(0, 0, 0, 0.3),
      0 0 30px var(--accent-primary),
      0 0 20px var(--accent-glow),
      0 1px 0 rgba(255, 255, 255, 0.05);
  }
}

.form-input :deep(.el-input__inner) {
  background: transparent;
  color: rgba(255, 255, 255, 0.98);
  font-weight: 500;
  font-size: 1rem;
  letter-spacing: 0.5px;
  padding: 12px 16px;
  transition: all 0.3s ease;
}

.form-input :deep(.el-input__inner:focus) {
  color: var(--accent-primary);
  text-shadow: 0 0 5px var(--accent-glow);
}

/* 占位符文本颜色 */
.form-input :deep(.el-input__placeholder) {
  color: rgba(150, 150, 170, 0.5) !important;
  font-style: italic;
  letter-spacing: 0.5px;
  transition: color 0.3s ease;
}

.form-input :deep(.el-input__wrapper:hover .el-input__placeholder) {
  color: rgba(180, 180, 200, 0.7) !important;
}

/* 选择器样式 */
.form-select :deep(.el-input__wrapper) {
  background: rgba(10, 13, 32, 0.75);
  border: 1px solid var(--border-color);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 
    inset 0 1px 3px rgba(0, 0, 0, 0.3),
    0 1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
}

.form-select :deep(.el-input__wrapper)::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  opacity: 0.5;
}

.form-select :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary);
  background: rgba(10, 13, 32, 0.85);
  box-shadow: 
    inset 0 1px 3px rgba(0, 0, 0, 0.3),
    0 0 15px var(--accent-glow),
    0 1px 0 rgba(255, 255, 255, 0.05);
  transform: translateY(-1px);
}

.form-select :deep(.el-input__inner) {
  background: transparent;
  color: rgba(255, 255, 255, 0.98);
  font-weight: 500;
  font-size: 1rem;
  letter-spacing: 0.5px;
  padding: 12px 16px;
  transition: all 0.3s ease;
}

.form-select :deep(.el-input__inner:focus) {
  color: var(--accent-primary);
  text-shadow: 0 0 5px var(--accent-glow);
}

.form-select :deep(.el-scrollbar__view) {
  background: rgba(10, 13, 32, 1);
  color: rgba(255, 255, 255, 0.9);
  padding: 0 8px;
}

.form-select :deep(.el-select-dropdown) {
  background: rgba(10, 13, 32, 0.9);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  box-shadow: 
    0 15px 40px rgba(0, 0, 0, 0.4),
    0 0 20px rgba(0, 153, 255, 0.1);
  margin-top: 8px;
  backdrop-filter: blur(15px);
  animation: dropdownAppear 0.3s ease-out;
  position: relative;
  overflow: hidden;
}

@keyframes dropdownAppear {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.form-select :deep(.el-select-dropdown)::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0.7;
}

.form-select :deep(.el-select-dropdown__item) {
  color: rgba(255, 255, 255, 0.85);
  font-weight: 500;
  padding: 12px 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 8px;
  margin: 6px 8px;
  position: relative;
  overflow: hidden;
}

.form-select :deep(.el-select-dropdown__item)::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: var(--accent-primary);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.form-select :deep(.el-select-dropdown__item:hover) {
  background: rgba(0, 153, 255, 0.2);
  color: var(--accent-primary);
  box-shadow: 0 4px 15px rgba(0, 153, 255, 0.3);
  transform: translateX(5px);
}

.form-select :deep(.el-select-dropdown__item:hover)::before {
  opacity: 1;
}

.form-select :deep(.el-select-dropdown__item.selected) {
  background: rgba(0, 153, 255, 0.3);
  color: var(--accent-primary);
  font-weight: 600;
  box-shadow: 0 0 15px rgba(0, 153, 255, 0.4);
}

.form-select :deep(.el-select-dropdown__item.selected)::before {
  opacity: 1;
}

.profile-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 2.5rem;
  align-items: stretch;
}

@media (max-width: 900px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }
}

.id-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2.5rem 2rem;
}

.id-card-header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  font-family: monospace;
  color: var(--accent-primary);
  font-size: 0.9rem;
  letter-spacing: 2px;
}

.id-status.online {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #00ff66;
  box-shadow: 0 0 10px #00ff66;
  animation: pulse 2s infinite;
}
@keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; box-shadow: 0 0 20px #00ff66; } 100% { opacity: 0.6; } }

.user-display-name {
  font-size: 2rem;
  font-weight: 800;
  margin-top: 2rem;
  color: #fff;
  text-shadow: 0 0 10px var(--accent-glow);
  letter-spacing: 2px;
}

.user-major-badge {
  margin-top: 0.75rem;
  padding: 0.4rem 1.25rem;
  border-radius: 20px;
  background: rgba(0, 153, 255, 0.15);
  border: 1px solid var(--accent-primary);
  color: var(--accent-primary);
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 1px;
}

.user-goal-display {
  margin-top: 3rem;
  width: 100%;
  background: rgba(10, 13, 32, 0.5);
  padding: 1.5rem;
  border-radius: 10px;
  border-left: 3px solid var(--accent-primary);
}

.goal-label {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.goal-text {
  margin-top: 0.8rem;
  font-size: 1.1rem;
  color: rgba(200, 200, 220, 0.9);
  font-style: italic;
  line-height: 1.6;
}

.cyber-lines {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 4rem;
  opacity: 0.4;
}

.cyber-lines .line {
  height: 2px;
  background: var(--accent-primary);
  box-shadow: 0 0 5px var(--accent-glow);
}

.cyber-lines .line.short {
  width: 60%;
}

.profile-main {
  display: flex;
  flex-direction: column;
}

.cyber-btn {
  font-weight: bold;
  letter-spacing: 2px;
  padding: 1.5rem 3rem !important;
  text-transform: uppercase;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(0,153,255,0.8), rgba(0,255,102,0.8));
  border: none;
  box-shadow: 0 0 20px rgba(0,153,255,0.4);
}
.cyber-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 0 30px rgba(0,153,255,0.6);
}

.avatar-container {
  position: relative;
  transition: transform 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.avatar-container:hover {
  transform: scale(1.05);
}

.avatar {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--bg-primary);
  box-shadow: 
    0 0 30px var(--accent-glow),
    inset 0 2px 10px rgba(255, 255, 255, 0.3),
    0 5px 15px rgba(0, 0, 0, 0.2);
  animation: avatarGlow 4s ease-in-out infinite;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

@keyframes avatarGlow {
  0%, 100% {
    box-shadow: 
      0 0 30px var(--accent-glow),
      inset 0 2px 10px rgba(255, 255, 255, 0.3),
      0 5px 15px rgba(0, 0, 0, 0.2);
  }
  50% {
    box-shadow: 
      0 0 40px var(--accent-primary),
      inset 0 2px 10px rgba(255, 255, 255, 0.3),
      0 5px 15px rgba(0, 0, 0, 0.2);
  }
}

.avatar::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
  animation: avatarShimmer 3s ease-in-out infinite;
}

@keyframes avatarShimmer {
  0%, 100% {
    transform: rotate(0deg) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: rotate(45deg) scale(1.2);
    opacity: 0.5;
  }
}

.avatar:hover {
  transform: scale(1.05);
  box-shadow: 
    0 0 45px var(--accent-primary),
    inset 0 2px 10px rgba(255, 255, 255, 0.3),
    0 5px 15px rgba(0, 0, 0, 0.2);
}

.avatar-text {
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

/* 响应式设计 - 全面优化移动体验 */
@media (max-width: 768px) {
  .settings-container {
    padding: 1.5rem 1rem;
  }
  
  .settings-header h2 {
    font-size: 2rem;
  }
  
  .subtitle {
    font-size: 1rem;
  }
  
  .settings-tabs :deep(.el-tabs__nav) {
    padding: 0.25rem;
    width: 100%;
    overflow-x: auto;
    justify-content: flex-start;
  }
  
  .settings-tabs :deep(.el-tabs__item) {
    padding: 0.6rem 1.2rem;
    font-size: 0.9rem;
  }
  
  .settings-card {
    padding: 1.5rem 1rem;
    border-radius: 12px;
  }
  
  .profile-content {
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 1.5rem;
  }
  
  .user-details {
    width: 100%;
  }
  
  .avatar {
    width: 80px;
    height: 80px;
    font-size: 2rem;
  }
  
  .card-actions {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .card-actions :deep(.el-button) {
    width: 100%;
  }
  
  .config-details {
    padding-left: 0.5rem;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
    gap: 0.5rem;
  }
  
  .info-value {
    min-width: auto;
    width: 100%;
  }
  
  .color-options {
    justify-content: center;
  }
  
  .color-option {
    width: 35px;
    height: 35px;
  }
}

/* 平板设备响应式调整 */
@media (min-width: 769px) and (max-width: 1024px) {
  .settings-container {
    padding: 2rem 1.5rem;
  }
  
  .settings-header h2 {
    font-size: 2.5rem;
  }
  
  .settings-tabs :deep(.el-tabs__nav) {
    flex-wrap: wrap;
  }
  
  .profile-content {
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 1.5rem;
  }
  
  .user-details {
    width: 100%;
  }
}
</style>

