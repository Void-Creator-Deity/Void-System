<template>
  <div class="settings-container">
    <!-- 页面标题 -->
    <div class="settings-header">
      <h2><span class="glitch">系统</span> <span class="system-text">设置</span></h2>
      <p class="subtitle">配置您的虚空学习系统参数</p>
    </div>
    
    <!-- 设置标签页导航 -->
    <el-tabs v-model="activeTab" class="settings-tabs">
      <el-tab-pane label="个人信息" name="profile">
        <!-- 用户信息卡片 -->
        <div class="settings-card user-profile">
          <div class="card-header">
            <div class="header-icon">👤</div>
            <h3>用户信息</h3>
          </div>
          
          <div class="profile-content">
            <div class="avatar-container">
              <div class="avatar">
                <span class="avatar-text">{{ userInfo.username ? userInfo.username.charAt(0).toUpperCase() : 'U' }}</span>
              </div>
              <div class="avatar-status online"></div>
            </div>
            
            <div class="user-details">
              <div class="detail-group">
                <label>用户名 *</label>
                <el-input 
                  v-model="userInfo.username" 
                  placeholder="输入用户名" 
                  class="form-input"
                  :validate-event="false"
                />
                <div v-if="errors.username" class="error-message">{{ errors.username }}</div>
              </div>
              
              <div class="detail-group">
                <label>学习目标</label>
                <el-input 
                  v-model="userInfo.learningGoal" 
                  placeholder="输入学习目标" 
                  class="form-input"
                  type="textarea"
                  :rows="2"
                />
              </div>
              
              <div class="detail-group">
                <label>专业领域 *</label>
                <el-select 
                  v-model="userInfo.major" 
                  placeholder="选择专业领域" 
                  class="form-select"
                  :validate-event="false"
                >
                  <el-option v-for="option in majorOptions" :key="option.value" :label="option.label" :value="option.value" />
                </el-select>
                <div v-if="errors.major" class="error-message">{{ errors.major }}</div>
              </div>
            </div>
          </div>
          
          <div class="card-actions">
            <el-button type="primary" @click="saveUserInfo" :loading="loading.profile">保存用户信息</el-button>
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="系统配置" name="config">
        <!-- 系统配置卡片 -->
        <div class="settings-card system-config">
          <div class="config-content">
            <div class="config-group">
              <div class="config-header">
                <h4>AI 助手设置</h4>
                <el-switch v-model="systemConfig.aiAssistantEnabled" />
              </div>
              
              <div class="config-details" v-if="systemConfig.aiAssistantEnabled">
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
              
              <div class="config-details" v-if="systemConfig.themeEnabled">
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
                      :title="color.value"
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
            <el-button type="primary" @click="saveSystemConfig" :loading="loading.config">应用设置</el-button>
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="学习偏好" name="preferences">
        <!-- 学习偏好卡片 -->
        <div class="settings-card learning-prefs">
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
            <el-button type="primary" @click="saveLearningPrefs" :loading="loading.preferences">保存偏好</el-button>
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="系统信息" name="info">
        <!-- 系统信息卡片 -->
        <div class="settings-card system-info">
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
              <span class="info-value" :class="{ 'status-online': systemInfo.status === 'online', 'status-offline': systemInfo.status === 'offline' }">
                {{ systemInfo.status === 'online' ? '在线' : '离线' }}
              </span>
            </div>
          </div>
          
          <div class="card-actions">
            <el-button @click="checkForUpdates" :loading="loading.update">检查更新</el-button>
            <el-button type="warning" plain @click="clearCache" :loading="loading.clearCache">清除缓存</el-button>
            <el-button type="danger" plain @click="confirmLogout">退出登录</el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
    
    <!-- 消息提示 -->
    <el-message-box
      v-model="confirmLogoutVisible"
      title="确认退出登录"
      type="warning"
      @confirm="logout"
      @cancel="cancelLogout"
    >
      确定要退出当前登录吗？
    </el-message-box>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from "vue"
import { useRouter } from "vue-router"
import { ElMessage } from 'element-plus'
import { getCurrentUser, logout as logoutApi } from '../api/user.js'

const router = useRouter()

// 响应式数据
const activeTab = ref('profile')
const loading = reactive({
  profile: false,
  config: false,
  preferences: false,
  update: false,
  clearCache: false
})
const errors = reactive({
  username: '',
  major: ''
})

// 用户信息
const userInfo = reactive({
  username: '',
  learningGoal: '',
  major: ''
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
  uptime: "00:00:00",
  status: 'online'
})

// 确认对话框
const confirmLogoutVisible = ref(false)

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
let uptimeInterval = null

const updateUptime = () => {
  const currentTime = new Date()
  const diff = Math.floor((currentTime - startTime) / 1000)
  
  const hours = Math.floor(diff / 3600).toString().padStart(2, '0')
  const minutes = Math.floor((diff % 3600) / 60).toString().padStart(2, '0')
  const seconds = (diff % 60).toString().padStart(2, '0')
  
  systemInfo.uptime = `${hours}:${minutes}:${seconds}`
}

// 验证表单
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

// 保存用户信息
const saveUserInfo = async () => {
  if (!validateForm()) {
    ElMessage.warning('请修正表单中的错误后再保存')
    return
  }
  
  loading.profile = true
  try {
    // 这里应该调用实际的API
    // await api.updateUserProfile(userInfo)
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('用户信息保存成功')
  } catch (error) {
    console.error('保存用户信息失败:', error)
    ElMessage.error('保存失败，请稍后重试')
  } finally {
    loading.profile = false
  }
}

// 保存系统配置
const saveSystemConfig = async () => {
  loading.config = true
  try {
    // 这里应该调用实际的API
    // await api.updateSystemConfig(systemConfig)
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 应用主题颜色
    if (systemConfig.themeEnabled) {
      document.documentElement.style.setProperty('--accent-primary', systemConfig.themeColor)
    }
    
    ElMessage.success('系统配置应用成功')
  } catch (error) {
    console.error('保存系统配置失败:', error)
    ElMessage.error('保存失败，请稍后重试')
  } finally {
    loading.config = false
  }
}

// 保存学习偏好
const saveLearningPrefs = async () => {
  loading.preferences = true
  try {
    // 这里应该调用实际的API
    // await api.updateLearningPreferences(learningPrefs)
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('学习偏好保存成功')
  } catch (error) {
    console.error('保存学习偏好失败:', error)
    ElMessage.error('保存失败，请稍后重试')
  } finally {
    loading.preferences = false
  }
}

// 检查更新
const checkForUpdates = async () => {
  loading.update = true
  try {
    // 这里应该调用实际的API
    // const response = await api.checkUpdates()
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('已是最新版本')
  } catch (error) {
    console.error('检查更新失败:', error)
    ElMessage.error('检查更新失败，请稍后重试')
  } finally {
    loading.update = false
  }
}

// 清除缓存
const clearCache = async () => {
  loading.clearCache = true
  try {
    // 清除本地缓存
    localStorage.removeItem('settings_cache')
    sessionStorage.clear()
    
    // 这里应该调用实际的API（如果需要）
    // await api.clearServerCache()
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('缓存清除成功')
  } catch (error) {
    console.error('清除缓存失败:', error)
    ElMessage.error('清除缓存失败，请稍后重试')
  } finally {
    loading.clearCache = false
  }
}

// 确认退出登录
const confirmLogout = () => {
  confirmLogoutVisible.value = true
}

// 取消退出
const cancelLogout = () => {
  confirmLogoutVisible.value = false
}

// 退出登录
const logout = async () => {
  try {
    // 调用后端logout API
    await logoutApi()
    
    // 清除本地存储
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
    
    // 跳转到登录页
    router.push('/login')
    
    ElMessage.success('已成功退出登录')
  } catch (error) {
    console.error('退出登录失败:', error)
    // 即使API调用失败，仍然清除本地信息并跳转
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
    router.push('/login')
  }
}

// 加载用户信息
const loadUserInfo = async () => {
  try {
    const response = await getCurrentUser()
    const userData = response.data
    
    // 更新用户信息
    userInfo.username = userData.username || '学习者'
    userInfo.learningGoal = userData.learningGoal || '掌握AI技术'
    userInfo.major = userData.major || 'computer_science'
    
    // 可以从本地存储加载之前保存的设置
    const savedSettings = localStorage.getItem('settings_cache')
    if (savedSettings) {
      try {
        const parsedSettings = JSON.parse(savedSettings)
        Object.assign(systemConfig, parsedSettings.systemConfig)
        Object.assign(learningPrefs, parsedSettings.learningPrefs)
      } catch (e) {
        console.error('解析保存的设置失败:', e)
      }
    }
  } catch (error) {
    console.error('加载用户信息失败:', error)
    // 使用默认值
    userInfo.username = '学习者'
    userInfo.learningGoal = '掌握AI技术'
    userInfo.major = 'computer_science'
  }
}

// 生命周期钩子
onMounted(() => {
  // 加载用户信息
  loadUserInfo()
  
  // 更新运行时间
  updateUptime()
  uptimeInterval = setInterval(updateUptime, 1000)
})

// 组件卸载时清除定时器
const cleanup = () => {
  if (uptimeInterval) {
    clearInterval(uptimeInterval)
  }
}

// 监听组件卸载
import { onBeforeUnmount } from 'vue'
onBeforeUnmount(() => {
  cleanup()
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
  left: 0;
  right: 0;
  height: 100%;
  background: linear-gradient(135deg, transparent 0%, var(--accent-glow) 50%, transparent 100%);
  opacity: 0;
  animation: shimmer 3s infinite;
  animation-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
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
}

.form-select :deep(.el-select-dropdown) {
  background: rgba(10, 13, 32, 0.98) !important;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 
    0 10px 30px rgba(0, 0, 0, 0.4),
    0 0 20px var(--accent-glow);
  margin-top: 8px;
  backdrop-filter: blur(10px);
}

.form-select :deep(.el-select-dropdown__item) {
  color: rgba(255, 255, 255, 0.95);
  padding: 10px 20px;
  transition: all 0.2s ease;
  border-radius: 6px;
  margin: 2px 8px;
}

.form-select :deep(.el-select-dropdown__item:hover) {
  background: rgba(255, 255, 255, 0.1);
  color: var(--accent-primary);
  font-weight: 500;
  transform: translateX(4px);
}

/* 用户资料区域 */
.profile-content {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
  align-items: center;
}

.avatar-container {
  position: relative;
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
    0 0 25px var(--accent-glow),
    inset 0 2px 10px rgba(255, 255, 255, 0.3);
  animation: pulse-glow 3s ease-in-out infinite;
  transition: all 0.3s ease;
}

.avatar:hover {
  transform: scale(1.05);
  box-shadow: 
    0 0 35px var(--accent-primary),
    inset 0 2px 10px rgba(255, 255, 255, 0.3);
}

.avatar-status {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 3px solid rgba(10, 13, 32, 0.9);
  box-shadow: 0 0 10px rgba(0, 255, 102, 0.5);
}

.status-online {
  background: #00ff66;
  box-shadow: 0 0 15px #00ff66;
  animation: statusPulse 2s ease-in-out infinite;
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
  padding: 1rem 1.5rem;
  background: rgba(10, 13, 32, 0.7);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.info-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--accent-primary);
  transform: translateX(-100%);
  transition: all 0.3s ease;
}

.info-item:hover {
  background: rgba(10, 13, 32, 0.9);
  border-color: var(--accent-primary);
  transform: translateX(5px);
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
}

.info-item:hover::before {
  transform: translateX(0);
}

.info-label {
  color: rgba(180, 180, 200, 0.8);
  font-size: 0.95rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  color: rgba(255, 255, 255, 0.98);
  font-weight: 700;
  font-size: 1rem;
  text-align: right;
  min-width: 120px;
  text-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

.status-online {
  color: #00ff66;
  text-shadow: 
    0 0 10px #00ff66,
    0 0 20px rgba(0, 255, 102, 0.5);
  font-weight: 700;
}

.status-offline {
  color: #ff6b6b;
  text-shadow: 
    0 0 10px #ff6b6b,
    0 0 20px rgba(255, 107, 107, 0.5);
}

/* 卡片操作按钮 - 现代按钮设计 */
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1.25rem;
  padding-top: 2rem;
  margin-top: 2rem;
  border-top: 1px solid var(--border-color);
  position: relative;
}

.card-actions::before {
  content: '';
  position: absolute;
  top: -1px;
  left: 0;
  width: 60px;
  height: 3px;
  background: var(--accent-primary);
  border-radius: 3px;
}

.card-actions :deep(.el-button--primary) {
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  border: none;
  color: white;
  font-weight: 700;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  padding: 0.75rem 2rem;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.3),
    0 0 15px var(--accent-glow);
}

.card-actions :deep(.el-button--primary:hover) {
  box-shadow: 
    0 6px 25px rgba(0, 0, 0, 0.4),
    0 0 30px var(--accent-primary);
  transform: translateY(-2px);
  filter: brightness(1.1);
}

.card-actions :deep(.el-button--primary:active) {
  transform: translateY(0);
}

.card-actions :deep(.el-button--primary)::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: all 0.5s ease;
}

.card-actions :deep(.el-button--primary:hover)::before {
  left: 100%;
}

.card-actions :deep(.el-button) {
  background: rgba(10, 13, 32, 0.7);
  border: 1px solid var(--border-color);
  color: rgba(255, 255, 255, 0.95);
  font-weight: 600;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(5px);
}

.card-actions :deep(.el-button:hover) {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.2),
    0 0 15px var(--accent-glow);
  background: rgba(10, 13, 32, 0.9);
  transform: translateY(-1px);
}

.card-actions :deep(.el-button--danger) {
  background: rgba(255, 51, 102, 0.1);
  border-color: rgba(255, 51, 102, 0.3);
  color: #ff3366;
}

.card-actions :deep(.el-button--danger:hover) {
  background: rgba(255, 51, 102, 0.2);
  border-color: #ff3366;
  box-shadow: 0 0 20px rgba(255, 51, 102, 0.3);
  color: white;
}

.card-actions :deep(.el-button--warning) {
  background: rgba(255, 204, 0, 0.1);
  border-color: rgba(255, 204, 0, 0.3);
  color: #ffcc00;
}

.card-actions :deep(.el-button--warning:hover) {
  background: rgba(255, 204, 0, 0.2);
  border-color: #ffcc00;
  box-shadow: 0 0 20px rgba(255, 204, 0, 0.3);
  color: white;
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

