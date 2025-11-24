<template>
  <div class="settings-container">
    <!-- 页面标题 -->
    <div class="settings-header">
      <h2><span class="glitch">系统</span> <span class="system-text">设置</span></h2>
      <p class="subtitle">配置您的虚空学习系统参数</p>
    </div>
    
    <!-- 设置面板 -->
    <div class="settings-content">
      <!-- 用户信息卡片 -->
      <div class="settings-card user-profile">
        <div class="card-header">
          <div class="header-icon">👤</div>
          <h3>用户信息</h3>
        </div>
        
        <div class="profile-content">
          <div class="avatar-container">
            <div class="avatar">
              <span class="avatar-text">U</span>
            </div>
            <div class="avatar-status online"></div>
          </div>
          
          <div class="user-details">
            <div class="detail-group">
              <label>用户名</label>
              <el-input v-model="userInfo.username" placeholder="输入用户名" class="form-input" />
            </div>
            
            <div class="detail-group">
              <label>学习目标</label>
              <el-input v-model="userInfo.learningGoal" placeholder="输入学习目标" class="form-input" />
            </div>
            
            <div class="detail-group">
              <label>专业领域</label>
              <el-select v-model="userInfo.major" placeholder="选择专业领域" class="form-select">
                <el-option v-for="option in majorOptions" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
            </div>
          </div>
        </div>
        
        <div class="card-actions">
          <el-button type="primary" @click="saveUserInfo">保存用户信息</el-button>
        </div>
      </div>
      
      <!-- 系统配置卡片 -->
      <div class="settings-card system-config">
        <div class="card-header">
          <div class="header-icon">⚙️</div>
          <h3>系统配置</h3>
        </div>
        
        <div class="config-content">
          <div class="config-group">
            <div class="config-header">
              <h4>AI 助手设置</h4>
              <el-switch v-model="systemConfig.aiAssistantEnabled" />
            </div>
            
            <div class="config-details">
              <div class="detail-group">
                <label>回复风格</label>
                <el-radio-group v-model="systemConfig.responseStyle">
                  <el-radio-button label="专业">专业</el-radio-button>
                  <el-radio-button label="友好">友好</el-radio-button>
                  <el-radio-button label="详细">详细</el-radio-button>
                </el-radio-group>
              </div>
              
              <div class="detail-group">
                <label>响应速度</label>
                <el-slider
                  v-model="systemConfig.responseSpeed"
                  :min="1"
                  :max="3"
                  :marks="{ 1: '快', 2: '中', 3: '详细' }"
                />
              </div>
            </div>
          </div>
          
          <div class="config-group">
            <div class="config-header">
              <h4>界面设置</h4>
              <el-switch v-model="systemConfig.themeEnabled" />
            </div>
            
            <div class="config-details">
              <div class="detail-group">
                <label>主题颜色</label>
                <div class="color-options">
                  <span 
                    v-for="color in colorOptions" 
                    :key="color.value"
                    class="color-option"
                    :class="{ active: systemConfig.themeColor === color.value }"
                    :style="{ backgroundColor: color.value }"
                    @click="systemConfig.themeColor = color.value"
                  ></span>
                </div>
              </div>
              
              <div class="detail-group">
                <label>动画效果</label>
                <el-checkbox-group v-model="systemConfig.animations">
                  <el-checkbox label="glow">发光效果</el-checkbox>
                  <el-checkbox label="float">浮动效果</el-checkbox>
                  <el-checkbox label="pulse">脉冲效果</el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
          </div>
        </div>
        
        <div class="card-actions">
          <el-button type="primary" @click="saveSystemConfig">应用设置</el-button>
        </div>
      </div>
      
      <!-- 学习偏好卡片 -->
      <div class="settings-card learning-prefs">
        <div class="card-header">
          <div class="header-icon">📚</div>
          <h3>学习偏好</h3>
        </div>
        
        <div class="preferences-content">
          <div class="detail-group">
            <label>学习时间偏好</label>
            <div class="time-pref">
              <el-time-select
                v-model="learningPrefs.preferredTime"
                :picker-options="{ start: '09:00', step: '00:30', end: '21:00' }"
                placeholder="选择学习时间"
              />
            </div>
          </div>
          
          <div class="detail-group">
            <label>学习资源类型</label>
            <el-checkbox-group v-model="learningPrefs.resourceTypes">
              <el-checkbox label="视频">视频</el-checkbox>
              <el-checkbox label="文档">文档</el-checkbox>
              <el-checkbox label="互动练习">互动练习</el-checkbox>
              <el-checkbox label="音频">音频</el-checkbox>
            </el-checkbox-group>
          </div>
          
          <div class="detail-group">
            <label>学习难度</label>
            <el-rate v-model="learningPrefs.difficultyLevel" show-score />
          </div>
          
          <div class="detail-group">
            <label>学习频率</label>
            <el-slider
              v-model="learningPrefs.studyFrequency"
              :min="1"
              :max="7"
              :marks="{ 1: '每周1次', 4: '每周4次', 7: '每天' }"
              show-input
            />
          </div>
        </div>
        
        <div class="card-actions">
          <el-button type="primary" @click="saveLearningPrefs">保存偏好</el-button>
        </div>
      </div>
      
      <!-- 系统信息卡片 -->
      <div class="settings-card system-info">
        <div class="card-header">
          <div class="header-icon">ℹ️</div>
          <h3>系统信息</h3>
        </div>
        
        <div class="info-content">
          <div class="info-item">
            <span class="info-label">系统版本</span>
            <span class="info-value">{{ systemInfo.version }}</span>
          </div>
          
          <div class="info-item">
            <span class="info-label">AI 模型</span>
            <span class="info-value">{{ systemInfo.aiModel }}</span>
          </div>
          
          <div class="info-item">
            <span class="info-label">向量存储</span>
            <span class="info-value">{{ systemInfo.vectorStore }}</span>
          </div>
          
          <div class="info-item">
            <span class="info-label">运行时间</span>
            <span class="info-value">{{ systemInfo.uptime }}</span>
          </div>
          
          <div class="info-item">
            <span class="info-label">后端状态</span>
            <span class="info-value status-online">在线</span>
          </div>
        </div>
        
        <div class="card-actions">
          <el-button @click="checkForUpdates">检查更新</el-button>
          <el-button type="warning" plain @click="clearCache">清除缓存</el-button>
        </div>
      </div>
    </div>
    
    <!-- 保存成功提示 -->
    <div v-if="showSuccessToast" class="success-toast">
      <div class="toast-content">
        <div class="toast-icon">✅</div>
        <div class="toast-text">{{ successMessage }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue"

// 响应式数据
const showSuccessToast = ref(false)
const successMessage = ref("")

// 用户信息
const userInfo = reactive({
  username: "学习者",
  learningGoal: "掌握AI技术",
  major: "计算机科学"
})

// 系统配置
const systemConfig = reactive({
  aiAssistantEnabled: true,
  responseStyle: "友好",
  responseSpeed: 2,
  themeEnabled: true,
  themeColor: "#00ccff",
  animations: ["glow", "float"]
})

// 学习偏好
const learningPrefs = reactive({
  preferredTime: "14:00",
  resourceTypes: ["视频", "文档"],
  difficultyLevel: 3,
  studyFrequency: 5
})

// 系统信息
const systemInfo = reactive({
  version: "1.0.0",
  aiModel: "Ollama LLM",
  vectorStore: "Chroma DB",
  uptime: "00:00:00"
})

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

// 颜色选项
const colorOptions = [
  { value: "#00ccff" },
  { value: "#00ff66" },
  { value: "#ff6b6b" },
  { value: "#ffcc00" },
  { value: "#9966ff" }
]

// 模拟系统运行时间
let startTime = new Date()

const updateUptime = () => {
  const currentTime = new Date()
  const diff = Math.floor((currentTime - startTime) / 1000)
  
  const hours = Math.floor(diff / 3600).toString().padStart(2, '0')
  const minutes = Math.floor((diff % 3600) / 60).toString().padStart(2, '0')
  const seconds = (diff % 60).toString().padStart(2, '0')
  
  systemInfo.uptime = `${hours}:${minutes}:${seconds}`
}

// 保存用户信息
const saveUserInfo = () => {
  console.log("保存用户信息:", userInfo)
  showToast("用户信息保存成功")
}

// 保存系统配置
const saveSystemConfig = () => {
  console.log("保存系统配置:", systemConfig)
  
  // 应用主题颜色
  if (systemConfig.themeEnabled) {
    document.documentElement.style.setProperty('--accent-primary', systemConfig.themeColor)
  }
  
  showToast("系统配置应用成功")
}

// 保存学习偏好
const saveLearningPrefs = () => {
  console.log("保存学习偏好:", learningPrefs)
  showToast("学习偏好保存成功")
}

// 检查更新
const checkForUpdates = () => {
  console.log("检查系统更新")
  showToast("已是最新版本")
}

// 清除缓存
const clearCache = () => {
  console.log("清除缓存")
  showToast("缓存清除成功")
}

// 显示提示
const showToast = (message) => {
  successMessage.value = message
  showSuccessToast.value = true
  
  setTimeout(() => {
    showSuccessToast.value = false
  }, 3000)
}

// 生命周期钩子
onMounted(() => {
  // 更新运行时间
  setInterval(updateUptime, 1000)
})
</script>

<style scoped>
.settings-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

/* 页面标题 */
.settings-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.settings-header h2 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.glitch {
  color: var(--accent-primary);
  text-shadow: 0 0 10px var(--accent-primary);
}

.system-text {
  color: var(--text-secondary);
}

.subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

/* 设置内容区域 */
.settings-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;
}

/* 设置卡片 */
.settings-card {
  background: linear-gradient(135deg, rgba(10, 13, 32, 0.8), rgba(5, 7, 20, 0.9));
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1.5rem;
  transition: all var(--transition-fast) ease;
  position: relative;
  overflow: hidden;
}

.settings-card:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 0 20px var(--accent-glow);
  transform: translateY(-5px);
}

.settings-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.header-icon {
  font-size: 1.5rem;
}

.card-header h3 {
  font-family: var(--main-font);
  font-weight: 600;
  /* 修改为高对比度文本颜色，确保在深色背景上的可读性 */
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
}

/* 表单样式 */
.form-input :deep(.el-input__wrapper) {
  background: rgba(5, 7, 20, 0.8);
  border: 1px solid var(--border-color);
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5);
}

.form-input :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary);
}

.form-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5), 0 0 15px var(--accent-primary);
}

.form-input :deep(.el-input__inner) {
    background: transparent;
    /* 确保在深色背景上的高对比度 */
    color: rgba(255, 255, 255, 0.9);
  }

.form-select :deep(.el-input__wrapper) {
  background: rgba(5, 7, 20, 0.8);
  border: 1px solid var(--border-color);
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5);
}

.form-select :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary);
}

.form-select :deep(.el-input__inner) {
    background: transparent;
    /* 确保在深色背景上的高对比度 */
    color: rgba(255, 255, 255, 0.9);
  }

.form-select :deep(.el-scrollbar__view) {
  background: rgba(5, 7, 20, 0.8);
  color: var(--text-primary);
}

.form-select :deep(.el-select-dropdown__item) {
  /* 修改为高对比度文本颜色，确保在深色背景上的可读性 */
  color: rgba(255, 255, 255, 0.9);
}

.form-select :deep(.el-select-dropdown__item:hover) {
  background: var(--bg-tertiary);
  color: var(--accent-primary);
}

/* 用户资料 */
.profile-content {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.avatar-container {
  position: relative;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: 700;
  color: var(--bg-primary);
  box-shadow: 0 0 20px var(--accent-glow);
}

.avatar-status {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--bg-primary);
}

.status-online {
  background: #00ff66;
  box-shadow: 0 0 10px #00ff66;
}

.user-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* 配置组 */
.config-group {
  margin-bottom: 1.5rem;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.config-header h4 {
  margin: 0;
  /* 修改为高对比度文本颜色，确保在深色背景上的可读性 */
  color: rgba(255, 255, 255, 0.9);
}

.config-details {
  padding-left: 1rem;
}

/* 详细组 */
.detail-group {
  margin-bottom: 1.25rem;
}

.detail-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* 颜色选项 */
.color-options {
  display: flex;
  gap: 0.75rem;
}

.color-option {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast) ease;
}

.color-option:hover {
  transform: scale(1.1);
  box-shadow: 0 0 10px var(--accent-glow);
}

.color-option.active {
  border-color: var(--text-primary);
  box-shadow: 0 0 15px var(--accent-primary);
}

/* 信息内容 */
.info-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: rgba(5, 7, 20, 0.5);
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.info-label {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.info-value {
  /* 修改为高对比度文本颜色，确保在深色背景上的可读性 */
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
}

.status-online {
  color: #00ff66;
  text-shadow: 0 0 5px #00ff66;
}

/* 卡片操作按钮 */
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.card-actions :deep(.el-button--primary) {
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  border: none;
}

.card-actions :deep(.el-button--primary:hover) {
  box-shadow: 0 0 20px var(--accent-primary);
  transform: translateY(-1px);
}

.card-actions :deep(.el-button) {
  background: transparent;
  border: 1px solid var(--border-color);
  /* 修改为高对比度文本颜色，确保在深色背景上的可读性 */
  color: rgba(255, 255, 255, 0.9);
}

.card-actions :deep(.el-button:hover) {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  box-shadow: 0 0 10px var(--accent-glow);
}

/* 成功提示 */
.success-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: rgba(5, 7, 20, 0.95);
  border: 1px solid #00ff66;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 0 20px rgba(0, 255, 102, 0.3);
  z-index: 1000;
  animation: slideIn 0.3s ease;
}

.toast-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toast-icon {
  font-size: 1.2rem;
}

.toast-text {
  color: #00ff66;
  font-weight: 500;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .settings-container {
    padding: 1rem;
  }
  
  .settings-content {
    grid-template-columns: 1fr;
  }
  
  .profile-content {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  
  .user-details {
    width: 100%;
  }
}
</style>

