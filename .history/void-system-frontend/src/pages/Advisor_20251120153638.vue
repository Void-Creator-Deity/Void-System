<template>
  <div class="advisor-container">
    <!-- 页面标题 -->
    <div class="advisor-header">
      <h2><span class="glitch">学习</span> <span class="system-text">顾问</span></h2>
      <p class="subtitle">输入学习主题，获取个性化学习任务建议</p>
    </div>
    
    <!-- 输入区域 -->
    <div class="input-section">
      <div class="input-wrapper">
        <div class="input-prefix">🧠</div>
        <el-input 
          v-model="topic" 
          placeholder="输入学习主题，例如：高等数学、Python编程"
          @keyup.enter="generate"
          :disabled="isLoading"
        />
      </div>
      <el-button 
        type="primary" 
        @click="generate"
        :loading="isLoading"
        :disabled="isLoading || !topic.trim()"
      >
        <span v-if="!isLoading">生成任务</span>
        <span v-else>生成中...</span>
      </el-button>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-section">
      <div class="loading-animation">
        <div class="loading-ring"></div>
        <p>{{ loadingMessage }}</p>
        <div class="progress-container">
          <div class="progress-bar-large">
            <div class="progress-fill-large" :style="{ width: loadingProgress + '%' }"></div>
          </div>
          <span class="progress-text-large">{{ loadingProgress }}%</span>
        </div>
        <el-button type="text" @click="cancelGeneration" class="cancel-btn">取消</el-button>
      </div>
    </div>
    
    <!-- 结果展示 -->
    <div v-else-if="result" class="results-section fade-in">
      <div class="result-header">
        <h3>🎯 系统任务建议</h3>
        <div class="timestamp">{{ formatTime(generationTime) }}</div>
      </div>
      
      <div class="task-cards">
        <!-- 如果API返回的是对象，尝试解析 -->
        <div v-if="parsedResult" class="task-card">
          <div class="task-header">
            <div class="task-title">{{ parsedResult.title || '学习任务' }}</div>
            <div class="task-priority">优先级: 高</div>
          </div>
          
          <div class="task-body">
            <div class="task-attribute">
              <div class="attribute-label">学习目标</div>
              <div class="attribute-value">{{ parsedResult.objective || '掌握相关知识点' }}</div>
            </div>
            
            <div class="task-attribute">
              <div class="attribute-label">建议时长</div>
              <div class="attribute-value">{{ parsedResult.duration || '60分钟' }}</div>
            </div>
            
            <div class="task-attribute">
              <div class="attribute-label">预期成果</div>
              <div class="attribute-value">{{ parsedResult.reward || '完成相关练习并巩固知识' }}</div>
            </div>
          </div>
          
          <div class="task-footer">
            <div class="task-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: '0%' }"></div>
              </div>
              <span class="progress-text">0%</span>
            </div>
            <el-button size="small" class="start-task-btn">开始任务</el-button>
          </div>
        </div>
        
        <!-- 原始结果展示 -->
        <div v-else class="raw-result">
          <pre>{{ result }}</pre>
        </div>
      </div>
      
      <div class="action-buttons">
        <el-button type="info" @click="saveTask" class="action-btn">
          💾 保存任务
        </el-button>
        <el-button type="success" @click="generateNewTask" class="action-btn">
          🔄 生成新任务
        </el-button>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="empty-state">
      <div class="empty-icon">🧠</div>
      <h3>准备就绪</h3>
      <p>输入学习主题，获取个性化任务建议</p>
      <div class="examples">
        <span class="example-tag" v-for="example in examples" :key="example" @click="setExample(example)">{{ example }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import { getAdvisor } from "@/api/ai"
import axios from "axios"

const topic = ref("")
const result = ref("")
const isLoading = ref(false)
const generationTime = ref(null)
const requestCanceler = ref(null)
const loadingMessage = ref("正在分析学习主题...")
const loadingProgress = ref(0)

// 示例主题
const examples = ['高等数学', 'Python编程', '英语听力', '数据结构', '人工智能']

// 解析结果（尝试将文本结果解析为结构化数据）
const parsedResult = computed(() => {
  if (!result.value) return null
  
  try {
    // 尝试解析JSON格式
    if (result.value.startsWith('{') && result.value.endsWith('}')) {
      return JSON.parse(result.value)
    }
    
    // 尝试从文本中提取结构化信息
    const parsed = {}
    
    // 提取任务标题
    const titleMatch = result.value.match(/任务标题[：:](.*?)(\n|$)/i)
    if (titleMatch) parsed.title = titleMatch[1].trim()
    
    // 提取学习目标
    const objectiveMatch = result.value.match(/学习目标[：:](.*?)(\n|$)/i)
    if (objectiveMatch) parsed.objective = objectiveMatch[1].trim()
    
    // 提取建议时长
    const durationMatch = result.value.match(/建议时长[：:](.*?)(\n|$)/i)
    if (durationMatch) parsed.duration = durationMatch[1].trim()
    
    // 提取奖励提示
    const rewardMatch = result.value.match(/奖励提示[：:](.*?)(\n|$)/i)
    if (rewardMatch) parsed.reward = rewardMatch[1].trim()
    
    // 如果至少提取了一项，返回解析结果
    return Object.keys(parsed).length > 0 ? parsed : null
  } catch (e) {
    console.log('无法解析结果为结构化数据:', e)
    return null
  }
})

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

// 设置示例主题
const setExample = (example) => {
  topic.value = example
}

// 生成新任务
const generateNewTask = () => {
  result.value = ''
  generationTime.value = null
}

// 保存任务
const saveTask = () => {
  // 这里可以实现保存任务的逻辑
  alert('任务已保存到您的学习计划中')
}

// 取消生成
const cancelGeneration = () => {
  if (requestCanceler.value) {
    requestCanceler.value.cancel('用户取消了请求')
  }
}

// 生成任务
async function generate() {
  // 添加输入验证
  if (!topic.value.trim() || isLoading.value) return
  
  isLoading.value = true
  result.value = ''
  loadingMessage.value = "正在分析学习主题..."
  loadingProgress.value = 0
  
  // 创建取消令牌
  requestCanceler.value = axios.CancelToken.source()
  
  // 模拟进度条更新
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 5
      if (loadingProgress.value > 30) {
        loadingMessage.value = "正在生成学习计划..."
      }
      if (loadingProgress.value > 60) {
        loadingMessage.value = "正在优化任务建议..."
      }
    }
  }, 1000)
  
  try {
    // 传递取消令牌
    result.value = await getAdvisor(topic.value, requestCanceler.value.token)
    generationTime.value = new Date().toISOString()
    loadingProgress.value = 100
  } catch (error) {
    console.error('API调用失败：', error)
    
    // 区分错误类型
    if (axios.isCancel(error)) {
      result.value = '任务已取消'
    } else if (error.code === 'ECONNABORTED') {
      result.value = '请求超时，AI处理时间可能较长\n建议：简化主题或稍后重试'
    } else if (error.response) {
      // 服务器返回错误
      result.value = `服务器错误 (${error.response.status})\n${error.response.data?.detail || '请稍后重试'}`
    } else if (error.request) {
      // 网络错误
      result.value = '网络连接失败\n请检查后端服务是否正常运行'
    } else {
      result.value = `生成失败，请重试\n错误信息：${error.message || '未知错误'}`
    }
  } finally {
    clearInterval(progressInterval)
    isLoading.value = false
    requestCanceler.value = null
  }
}
</script>

<style scoped>
.advisor-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

/* 页面标题 */
.advisor-header {
  text-align: center;
  margin-bottom: 2.5rem;
  position: relative;
  padding: 1rem;
  background: rgba(10, 13, 32, 0.75);
  border-radius: 16px;
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), 0 0 20px rgba(0, 204, 255, 0.1);
  overflow: hidden;
}

.advisor-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  animation: headerGlow 3s ease-in-out infinite;
}

@keyframes headerGlow {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; box-shadow: 0 0 10px var(--accent-primary); }
}

.advisor-header h2 {
  font-size: 2.2rem;
  margin-bottom: 0.5rem;
  background: linear-gradient(90deg, var(--text-primary), var(--accent-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  position: relative;
  z-index: 1;
}

.glitch {
  color: var(--accent-primary);
  text-shadow: 0 0 15px var(--accent-glow), 0 0 30px rgba(0, 204, 255, 0.3);
  animation: glitchPulse 2s ease-in-out infinite;
}

@keyframes glitchPulse {
  0%, 100% { text-shadow: 0 0 15px var(--accent-glow); }
  50% { text-shadow: 0 0 20px var(--accent-glow), 0 0 40px rgba(0, 204, 255, 0.5); }
}

.system-text {
  color: var(--text-secondary);
}

.subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
  opacity: 0.9;
  transition: opacity 0.3s ease;
}

.advisor-header:hover .subtitle {
  opacity: 1;
}

/* 输入区域 */
.input-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  align-items: stretch;
  position: relative;
}

.input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.input-prefix {
  position: absolute;
  left: 15px;
  font-size: 1.2rem;
  z-index: 1;
  pointer-events: none;
  color: var(--accent-primary);
  text-shadow: 0 0 8px var(--accent-glow);
  animation: prefixGlow 2s ease-in-out infinite alternate;
}

@keyframes prefixGlow {
  from { opacity: 0.7; }
  to { opacity: 1; }
}

.input-wrapper :deep(.el-input__wrapper) {
  background: rgba(10, 13, 32, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.3), 0 4px 15px rgba(0, 0, 0, 0.2);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.input-wrapper :deep(.el-input__wrapper)::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0.7;
}

.input-wrapper :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary);
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.2), 0 0 20px var(--accent-glow), 0 4px 15px rgba(0, 0, 0, 0.2);
  transform: translateY(-2px);
}

.input-wrapper :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.2), 0 0 25px var(--accent-primary), 0 4px 15px rgba(0, 0, 0, 0.2);
  transform: translateY(-2px);
}

.input-wrapper :deep(.el-input__inner) {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-family: var(--body-font);
  padding-left: 35px;
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.9);
  letter-spacing: 0.5px;
}

.input-section :deep(.el-button) {
  min-width: 120px;
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  border: none;
  color: var(--bg-primary);
  font-weight: 600;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2), 0 0 15px var(--accent-glow);
}

.input-section :deep(.el-button)::before {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0.7;
}

.input-section :deep(.el-button:hover:not(:disabled)) {
  box-shadow: 0 0 25px var(--accent-primary), 0 6px 20px rgba(0, 0, 0, 0.3);
  transform: translateY(-2px) scale(1.02);
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
}

.input-section :deep(.el-button:active:not(:disabled)) {
  transform: translateY(0);
}

.input-section :deep(.el-button.is-disabled) {
  opacity: 0.6;
  box-shadow: none;
  transform: none;
}

/* 加载状态 */
.loading-section {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 3rem;
}

.loading-animation {
  text-align: center;
}

.loading-ring {
  width: 70px;
  height: 70px;
  border: 4px solid var(--border-color);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  margin: 0 auto 1rem;
  animation: spin 1s linear infinite;
  box-shadow: 0 0 20px rgba(0, 204, 255, 0.3);
}

@keyframes spin {
  to { 
    transform: rotate(360deg); 
    box-shadow: 0 0 25px rgba(0, 204, 255, 0.5);
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 结果展示 */
.results-section {
  background: linear-gradient(135deg, rgba(45, 64, 184, 0.1), rgba(122, 131, 189, 0.05));
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 
    0 0 40px rgba(0, 204, 255, 0.15),
    inset 0 0 10px rgba(0, 204, 255, 0.05);
  backdrop-filter: blur(10px);
  animation: containerGlow 3s ease-in-out infinite alternate;
}

@keyframes containerGlow {
  0% { box-shadow: 0 0 30px rgba(0, 204, 255, 0.1); }
  100% { box-shadow: 0 0 40px rgba(0, 204, 255, 0.2); }
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.result-header h3 {
  margin: 0;
  font-size: 1.3rem;
}

.timestamp {
  color: var(--text-secondary);
  font-size: 0.8rem;
}

/* 任务卡片 */
.task-cards {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.task-card {
  background: rgba(10, 13, 32, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 1.5rem;
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(15px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  border-left: 4px solid var(--accent-primary);
}

.task-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  animation: cardHeaderGlow 3s ease-in-out infinite;
}

@keyframes cardHeaderGlow {
  0%, 100% { opacity: 0.5; box-shadow: 0 0 5px var(--accent-primary); }
  50% { opacity: 1; box-shadow: 0 0 15px var(--accent-primary); }
}

.task-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: -4px;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, var(--accent-primary), transparent);
  opacity: 0.7;
}

.task-card:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 0 25px var(--accent-glow), 0 8px 30px rgba(0, 0, 0, 0.3);
  transform: translateY(-4px) scale(1.01);
  background: rgba(10, 13, 32, 0.85);
}

.task-card:hover::after {
  opacity: 1;
  animation: sideGlow 1.5s ease-in-out infinite;
}

@keyframes sideGlow {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.task-title {
  font-family: var(--main-font);
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  background: linear-gradient(90deg, var(--text-primary), var(--accent-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  transition: all 0.3s ease;
}

.task-card:hover .task-title {
  -webkit-text-fill-color: var(--text-primary);
  text-shadow: 0 0 10px var(--accent-glow);
}

.task-priority {
  font-size: 0.85rem;
  color: var(--accent-primary);
  background: rgba(0, 255, 204, 0.1);
  padding: 0.35rem 1rem;
  border-radius: 16px;
  border: 1px solid rgba(0, 255, 204, 0.3);
  font-weight: 600;
  text-shadow: 0 0 5px rgba(0, 255, 204, 0.5);
  transition: all 0.3s ease;
}

.task-card:hover .task-priority {
  background: rgba(0, 255, 204, 0.2);
  border-color: var(--accent-primary);
  box-shadow: 0 0 10px var(--accent-glow);
  transform: scale(1.05);
}

.task-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.task-attribute {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  transition: all 0.3s ease;
}

.attribute-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.8;
  transition: opacity 0.3s ease;
}

.task-card:hover .attribute-label {
  opacity: 1;
  color: var(--accent-secondary);
}

.attribute-value {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.5;
  transition: all 0.3s ease;
}

.task-card:hover .attribute-value {
  text-shadow: 0 0 5px rgba(255, 255, 255, 0.2);
}

.task-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.task-progress {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.progress-bar {
  flex: 1;
  height: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 5px;
  overflow: hidden;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 5px;
  transition: width 0.8s ease;
  box-shadow: 0 0 15px var(--accent-glow);
  animation: progressPulse 2s ease-in-out infinite;
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: progressShimmer 2s infinite;
}

@keyframes progressShimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes progressPulse {
  0%, 100% { box-shadow: 0 0 10px var(--accent-glow); }
  50% { box-shadow: 0 0 20px var(--accent-glow), 0 0 30px rgba(0, 204, 255, 0.5); }
}

.progress-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  min-width: 35px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.task-card:hover .progress-text {
  color: var(--accent-primary);
  text-shadow: 0 0 5px var(--accent-glow);
}
  
  /* 加载进度条 */
  .progress-container {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 1rem;
    width: 100%;
    max-width: 400px;
  }
  
  .progress-bar-large {
    flex: 1;
    height: 8px;
    background-color: var(--bg-secondary);
    border-radius: 4px;
    overflow: hidden;
  }
  
  .progress-fill-large {
    height: 100%;
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
    transition: width 0.5s ease;
  }
  
  .progress-text-large {
    font-size: 1rem;
    color: var(--text-secondary);
    min-width: 40px;
    text-align: right;
  }
  
  .cancel-btn {
    margin-top: 1rem;
    color: var(--text-secondary);
  }

.start-task-btn {
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  border: none;
  color: var(--bg-primary);
  font-weight: 600;
  padding: 0.5rem 1.5rem;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.start-task-btn:hover {
  box-shadow: 0 0 20px var(--accent-glow);
  transform: translateY(-2px);
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
}

/* 原始结果 */
.raw-result {
  background: rgba(10, 13, 32, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1.5rem;
  line-height: 1.6;
  white-space: pre-wrap;
  font-family: var(--body-font);
  color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.2);
  position: relative;
  overflow: hidden;
}

.raw-result::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0.7;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 1.5rem;
  justify-content: center;
  margin-top: 2rem;
}

.action-btn {
  background: linear-gradient(135deg, rgba(25, 30, 60, 0.8), rgba(15, 20, 40, 0.8));
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  min-width: 120px;
  border-radius: 12px;
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  backdrop-filter: blur(5px);
  overflow: hidden;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.action-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0.7;
}

.action-btn:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 0 20px var(--accent-glow), 0 6px 20px rgba(0, 0, 0, 0.3);
  transform: translateY(-2px);
  background: linear-gradient(135deg, rgba(25, 30, 60, 0.9), rgba(15, 20, 40, 0.9));
}

.action-btn:active {
  transform: translateY(0);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 3rem;
  background: rgba(10, 13, 32, 0.75);
  border-radius: 16px;
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.empty-state:hover {
  box-shadow: 0 0 25px var(--accent-glow), 0 8px 32px rgba(0, 0, 0, 0.3);
  border-color: var(--accent-primary);
}

.empty-icon {
  font-size: 3.5rem;
  margin-bottom: 1.5rem;
  animation: float 3s ease-in-out infinite;
  color: var(--accent-primary);
  text-shadow: 0 0 20px var(--accent-glow);
}

@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-10px) rotate(2deg); }
}

.empty-state h3 {
  margin-bottom: 0.5rem;
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.4rem;
  background: linear-gradient(90deg, var(--text-primary), var(--accent-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.empty-state p {
  color: var(--text-secondary);
  margin-bottom: 2rem;
  line-height: 1.6;
  opacity: 0.8;
  transition: opacity 0.3s ease;
}

.empty-state:hover p {
  opacity: 1;
}

.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
  margin-top: 1.5rem;
}

.example-tag {
  background: linear-gradient(135deg, rgba(25, 30, 60, 0.7), rgba(15, 20, 40, 0.7));
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 0.65rem 1.25rem;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(5px);
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.example-tag::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0.7;
}

.example-tag:hover {
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  color: var(--bg-primary);
  border-color: var(--accent-primary);
  box-shadow: 0 0 20px var(--accent-glow), 0 6px 20px rgba(0, 0, 0, 0.3);
  transform: translateY(-2px) scale(1.02);
  font-weight: 600;
}

.example-tag:active {
  transform: translateY(0) scale(0.98);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .advisor-container {
    padding: 1rem;
  }
  
  .input-section {
    flex-direction: column;
  }
  
  .task-footer {
    flex-direction: column;
    align-items: stretch;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .examples {
    flex-direction: column;
    align-items: center;
  }
  
  .example-tag {
    width: 100%;
    max-width: 200px;
  }
}
</style>
