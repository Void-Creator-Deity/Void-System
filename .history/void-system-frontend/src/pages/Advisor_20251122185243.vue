<template>
  <div class="advisor-container">
    <!-- 页面标题区域 -->
    <header class="advisor-header">
      <h1 class="page-title">
        <span class="title-icon">🎯</span>
        任务生成
      </h1>
      <p class="page-description">根据设定目标形成任务，完成任务评估反馈系统币和评估属性值等等</p>
    </header>

    <!-- 输入区域 -->
    <div class="input-section">
      <div class="input-wrapper">
        <div class="input-field">
          <span class="input-prefix">📚</span>
          <input 
            v-model="userQuery" 
            type="text" 
            placeholder="输入您的目标..."
            @keyup.enter="submitQuery"
            :disabled="isLoading || isSubmitting"
          />
          <button 
            class="send-btn" 
            @click="submitQuery"
            :disabled="isLoading || isSubmitting || !userQuery.trim()"
          >
            <span class="btn-icon">{{ isLoading ? '⏱️' : '🚀' }}</span>
            <span class="btn-text">{{ isLoading ? '生成中...' : '发送' }}</span>
          </button>
        </div>
        
        <div class="input-tips">
          <span class="tip-icon">💡</span>
          <span class="tip-text">提示：请输入具体的目标</span>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-state">
      <div class="loading-container">
        <div class="loading-spinner"></div>
        <div class="loading-content">
          <h3 class="loading-title">正在分析您的问题...</h3>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <p class="loading-description">正在生成个性化任务</p>
        </div>
      </div>
    </div>

    <!-- 结果区域 -->
    <div v-else-if="advisorResult && !isLoading" class="result-section">
      <!-- 后端原始响应展示 -->
      <div class="raw-response-card">
        <div class="card-header">
          <h3 class="card-title">🤖 后端返回信息</h3>
        </div>
        <div class="card-content">
          <pre class="raw-response-content">{{ formattedRawResponse }}</pre>
        </div>
      </div>

      <!-- 任务解析结果 -->
      <div class="task-card">
        <div class="task-header">
          <h3 class="task-title">📋 任务预览</h3>
          <div class="task-meta">
            <span class="task-date">{{ formattedDate }}</span>
            <span v-if="estimatedDuration" class="task-duration">预计用时: {{ estimatedDuration }}</span>
          </div>
        </div>
        
        <div class="task-content">
          <div v-if="validationError" class="validation-error">
            <span class="error-icon">⚠️</span>
            <span class="error-message">{{ validationError }}</span>
          </div>
          
          <div class="learning-path">
            <div 
              v-for="(step, index) in learningSteps" 
              :key="index"
              class="path-step"
            >
              <div class="step-number">{{ index + 1 }}</div>
              <div class="step-content">
                <h4 class="step-title">{{ step.title }}</h4>
                <p class="step-description">{{ step.description }}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div class="task-footer">
          <button 
            class="footer-btn secondary-btn" 
            @click="resetForm"
            :disabled="isSubmitting"
          >
            重新生成
          </button>
          <button 
            class="footer-btn primary-btn" 
            @click="publishTask"
            :disabled="isSubmitting || validationError || learningSteps.length === 0"
          >
            {{ isSubmitting ? '发布中...' : '发布任务' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// 状态管理
const userQuery = ref('')
const isLoading = ref(false)
const isSubmitting = ref(false)
const progressPercent = ref(0)
const advisorResult = ref(null)
const validationError = ref('')

// 从advisorResult中解析任务步骤
const learningSteps = computed(() => {
  // 检查advisorResult是否存在
  if (!advisorResult.value) {
    return []
  }
  
  // 检查steps字段是否存在且为数组
  if (Array.isArray(advisorResult.value.steps)) {
    // 过滤出有效的步骤（包含title和description的对象）
    return advisorResult.value.steps.filter(step => 
      step && typeof step === 'object' && 
      step.title && typeof step.title === 'string' && 
      step.description && typeof step.description === 'string'
    )
  }
  
  // 如果steps不是数组或不存在，返回空数组
  return []
})

// 从advisorResult中解析估计用时
const estimatedDuration = computed(() => {
  // 检查advisorResult是否存在且包含有效的estimatedDuration字符串
  if (advisorResult.value && 
      advisorResult.value.estimatedDuration && 
      typeof advisorResult.value.estimatedDuration === 'string') {
    return advisorResult.value.estimatedDuration
  }
  
  // 如果数据不存在或无效，返回空字符串
  return ''
})

// 格式化后端原始响应为易读的JSON格式
const formattedRawResponse = computed(() => {
  if (!advisorResult.value) {
    return ''
  }
  return JSON.stringify(advisorResult.value, null, 2)
})

// 任务数据验证计算属性
const validateTaskData = computed(() => {
  // 重置验证错误
  validationError.value = ''
  
  // 检查advisorResult是否存在
  if (!advisorResult.value) {
    validationError.value = '无任务数据可供验证'
    return false
  }
  
  // 检查是否包含steps数组
  if (!Array.isArray(advisorResult.value.steps)) {
    validationError.value = '任务数据缺少有效的步骤列表'
    return false
  }
  
  // 检查是否有至少一个有效的步骤
  const validSteps = learningSteps.value
  if (validSteps.length === 0) {
    validationError.value = '任务步骤格式不正确，每个步骤需要包含标题和描述'
    return false
  }
  
  // 验证通过
  return true
})

// 计算属性
const formattedDate = computed(() => {
  const date = new Date()
  return date.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
})

// 提交查询函数
const submitQuery = async () => {
  // 验证输入
  if (!userQuery.value.trim()) {
    alert('请输入任务目标')
    return
  }
  
  // 重置状态
  isLoading.value = true
  progressPercent.value = 0
  advisorResult.value = null
  validationError.value = ''
  
  try {
    // 模拟进度更新
    const progressInterval = setInterval(() => {
      if (progressPercent.value < 90) {
        progressPercent.value += Math.floor(Math.random() * 10) + 5
      }
    }, 200)
    
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // 清除进度更新定时器
    clearInterval(progressInterval)
    progressPercent.value = 100
    
    // 模拟API返回结果（保持与后端数据格式一致）
    advisorResult.value = {
      query: userQuery.value,
      steps: [
        {
          title: '准备阶段',
          description: `为实现"${userQuery.value}"目标，收集必要的资源和信息`
        },
        {
          title: '规划阶段',
          description: '制定详细的行动计划，分解任务为可执行的步骤'
        },
        {
          title: '执行阶段',
          description: '按照计划逐步实施，确保每个步骤的质量'
        },
        {
          title: '评估与调整',
          description: '检查执行结果，进行必要的调整和优化'
        }
      ],
      estimatedDuration: '45分钟',
      createdAt: new Date(),
      fullResponse: `这是关于"${userQuery.value}"的完整任务规划。我们设计了一个包含准备、规划、执行和评估四个阶段的流程...`
    }
    
    // 实际项目中，这里应该调用真实的API
    // const response = await api.advisor.submitQuery(userQuery.value)
    // advisorResult.value = response.data
    
    // 验证返回的数据格式
    validateTaskData.value
    
  } catch (error) {
    console.error('生成任务失败:', error)
    alert('生成任务失败，请稍后重试')
  } finally {
    // 确保加载状态被重置
    isLoading.value = false
  }
}

// 发布任务函数
const publishTask = async () => {
  if (!validateTaskData.value) {
    alert('任务数据无效，无法发布')
    return
  }
  
  isSubmitting.value = true
  
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // 实际项目中，这里应该调用真实的发布任务API
    // await api.tasks.publish(advisorResult.value)
    
    alert('任务发布成功！')
    
    // 重置表单，准备下一次查询
    resetForm()
    
    } catch (error) {
      console.error('发布任务失败:', error)
      alert('发布任务失败，请稍后重试')
    } finally {
      isSubmitting.value = false
    }
  }
  
  // 重置表单函数
  const resetForm = () => {
    userQuery.value = ''
    advisorResult.value = null
    validationError.value = ''
  }
</script>

<style scoped>
.advisor-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* 页面标题区域 */
.advisor-header {
  text-align: center;
  margin-bottom: 40px;
}

.page-title {
  font-size: 2.5rem;
  color: #333;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.title-icon {
  font-size: 2rem;
}

.page-description {
  color: #666;
  font-size: 1.1rem;
}

/* 输入区域 */
.input-section {
  margin-bottom: 30px;
}

.input-wrapper {
  max-width: 800px;
  margin: 0 auto;
}

.input-field {
  display: flex;
  align-items: center;
  background: #f8f9fa;
  border-radius: 12px;
  padding: 5px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.3s ease;
}

.input-field:focus-within {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.input-prefix {
  font-size: 1.5rem;
  margin: 0 15px;
}

.input-field input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 15px;
  font-size: 1.1rem;
  outline: none;
}

.send-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-icon {
  font-size: 1.2rem;
}

.input-tips {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  color: #666;
  font-size: 0.9rem;
  padding-left: 15px;
}

.tip-icon {
  font-size: 1.1rem;
}

/* 加载状态 */
.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: white;
  padding: 40px;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  max-width: 500px;
  width: 100%;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-title {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 15px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 15px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.3s ease;
}

.loading-description {
  color: #666;
  font-size: 1rem;
}

/* 结果区域 */
.result-section {
  display: flex;
  flex-direction: column;
  gap: 30px;
  max-width: 1000px;
  margin: 0 auto;
}

/* 原始响应卡片 */
.raw-response-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.raw-response-card .card-header {
  background: #f8f9fa;
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
}

.raw-response-card .card-title {
  font-size: 1.3rem;
  color: #333;
  margin: 0;
}

.raw-response-card .card-content {
  padding: 20px;
  max-height: 300px;
  overflow-y: auto;
}

.raw-response-content {
  background: #f6f8fa;
  padding: 20px;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  color: #333;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

/* 任务卡片 */
.task-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.task-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 25px 30px;
}

.task-title {
  font-size: 1.5rem;
  margin: 0 0 10px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-meta {
  display: flex;
  gap: 20px;
  font-size: 0.9rem;
  opacity: 0.9;
}

.task-content {
  padding: 30px;
}

/* 验证错误提示 */
.validation-error {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
  padding: 15px 20px;
  border-radius: 8px;
  margin-bottom: 25px;
}

.error-icon {
  font-size: 1.2rem;
}

.error-message {
  font-weight: 500;
}

/* 学习路径 */
.learning-path {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.path-step {
  display: flex;
  gap: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.path-step:hover {
  transform: translateX(5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.step-number {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1.2rem;
}

.step-content {
  flex: 1;
}

.step-title {
  font-size: 1.2rem;
  color: #333;
  margin: 0 0 8px 0;
}

.step-description {
  color: #666;
  margin: 0;
  line-height: 1.6;
}

.task-footer {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  padding: 20px 30px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.footer-btn {
  padding: 12px 24px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.footer-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.secondary-btn {
  background: #e9ecef;
  color: #495057;
}

.secondary-btn:hover:not(:disabled) {
  background: #dee2e6;
  transform: translateY(-2px);
}

.primary-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.primary-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .advisor-container {
    padding: 15px;
  }
  
  .page-title {
    font-size: 2rem;
  }
  
  .input-field {
    flex-direction: column;
    padding: 15px;
  }
  
  .input-field input {
    width: 100%;
    margin-bottom: 15px;
  }
  
  .send-btn {
    width: 100%;
    justify-content: center;
  }
  
  .task-meta {
    flex-direction: column;
    gap: 5px;
  }
  
  .path-step {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  
  .task-footer {
    flex-direction: column;
  }
  
  .footer-btn {
    width: 100%;
  }
}
    isLoading.value = false
  }
}

// 发布任务函数
const publishTask = async () => {
  // 重新验证数据
  if (!validateTaskData.value) {
    alert('任务数据不符合要求，请检查后重试')
    return
  }
  
  isSubmitting.value = true
  
  try {
    // 准备要提交的数据
    const taskData = {
      title: userQuery.value,
      steps: learningSteps.value,
      estimatedDuration: estimatedDuration.value,
      rawData: advisorResult.value,
      createdAt: new Date()
    }
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // 实际项目中，这里应该调用后端API保存任务
    // await api.tasks.create(taskData)
    
    alert('任务发布成功！任务已保存到数据库')
    resetForm()
    
  } catch (error) {
    console.error('发布任务失败:', error)
    alert('发布任务失败，请稍后重试')
  } finally {
    isSubmitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  userQuery.value = ''
  advisorResult.value = null
  validationError.value = ''
  progressPercent.value = 0
}
    setTimeout(() => {
      isLoading.value = false
    }, 500)
  }
}

const useQuickTopic = (topic) => {
  userQuery.value = topic
  submitQuery()
}
</script>

<style scoped>
/* 主容器 */
.advisor-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
  position: relative;
}

.advisor-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: -20%;
  right: -20%;
  height: 200px;
  background: radial-gradient(circle at center, rgba(67, 97, 238, 0.1) 0%, transparent 70%);
  z-index: -1;
}

/* 页面标题区域 */
.advisor-header {
  text-align: center;
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-light);
  position: relative;
}

.advisor-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 25%;
  right: 25%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-md) 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.title-icon {
  font-size: 2rem;
  animation: pulse 2s ease-in-out infinite;
}

.page-description {
  font-size: 1.125rem;
  color: var(--color-text-secondary);
  margin: 0;
  background: linear-gradient(90deg, var(--color-text-primary), var(--color-text-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 输入区域 */
.input-section {
  margin-bottom: var(--spacing-xl);
}

.input-wrapper {
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

.input-wrapper::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
}

.input-field {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm);
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
}

.input-field:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
}

.input-prefix {
  font-size: 1.25rem;
  padding: 0 var(--spacing-sm);
  color: var(--color-text-secondary);
}

.input-field input {
  flex: 1;
  border: none;
  background: transparent;
  padding: var(--spacing-md);
  font-size: 1rem;
  color: var(--color-text-primary);
  outline: none;
}

.input-field input::placeholder {
  color: var(--color-text-muted);
}

.send-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  background-color: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.send-btn:hover:not(:disabled) {
  background-color: var(--color-primary-dark);
  transform: translateY(-1px);
}

.send-btn:disabled {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-muted);
  cursor: not-allowed;
  transform: none;
}

.btn-icon {
  font-size: 1.125rem;
}

.input-tips {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-md);
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.tip-icon {
  font-size: 1rem;
}

/* 快速主题 */
.quick-topics {
  margin-bottom: var(--spacing-lg);
}

.topics-header {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-xs) var(--spacing-md);
  background-color: rgba(67, 97, 238, 0.1);
  border-radius: var(--radius-full);
  border: 1px solid rgba(67, 97, 238, 0.2);
  display: inline-block;
}

.topics-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.topic-tag {
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-full);
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: 0.875rem;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.topic-tag::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(67, 97, 238, 0.1), transparent);
  transition: left var(--transition-normal);
}

.topic-tag:hover::before {
  left: 100%;
}

.topic-tag:hover {
  background-color: var(--color-bg-tertiary);
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(67, 97, 238, 0.1);
}

/* 加载状态 */
.loading-state {
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

.loading-state::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
}

.loading-container {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 3px solid var(--color-bg-tertiary);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  box-shadow: 0 0 20px rgba(67, 97, 238, 0.2);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-content {
  flex: 1;
}

.loading-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-md) 0;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--spacing-md);
}

.progress-fill {
  height: 100%;
  background-color: var(--color-primary);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.loading-description {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
}

/* 结果区域 */
.result-section {
  margin-bottom: var(--spacing-xl);
}

/* 任务卡片 */
.task-card {
  background: linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
}

.task-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
}

.task-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-3px);
  border-color: rgba(67, 97, 238, 0.3);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
}

.task-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.task-meta {
  display: flex;
  gap: var(--spacing-md);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.task-content {
  margin-bottom: var(--spacing-lg);
}

.task-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}

/* 学习路径 */
.learning-path {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.path-step {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-start;
  padding: var(--spacing-md);
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  transition: all var(--transition-normal);
}

.path-step:hover {
  transform: translateX(5px);
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.step-number {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 0 15px rgba(67, 97, 238, 0.2);
  position: relative;
  overflow: hidden;
}

.step-number::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  animation: stepShine 3s linear infinite;
}

@keyframes stepShine {
  0% { left: -100%; }
  100% { left: 100%; }
}

.step-content {
  flex: 1;
}

.step-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
}

.step-description {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
}

/* 资源列表 */
.resources-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.resource-item {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-start;
  padding: var(--spacing-md);
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border-radius: var(--radius-md);
  transition: all var(--transition-normal);
  border: 1px solid var(--color-border-light);
  position: relative;
  overflow: hidden;
}

.resource-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: linear-gradient(to bottom, var(--color-primary), var(--color-secondary));
}

.resource-item:hover {
  background-color: var(--color-bg-tertiary);
  transform: translateX(5px);
  box-shadow: var(--shadow-sm);
  border-color: var(--color-primary);
}

.resource-item:hover {
  background-color: var(--color-bg-tertiary);
}

.resource-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.resource-info {
  flex: 1;
}

.resource-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
}

.resource-description {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-xs) 0;
}

.resource-link {
  background: none;
  border: none;
  color: var(--color-primary);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  padding: var(--spacing-xs) 0;
  transition: color var(--transition-fast);
}

.resource-link:hover {
  color: var(--color-primary-dark);
  text-decoration: underline;
}

/* 常见问题 */
.faq-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.faq-item {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all var(--transition-normal);
}

.faq-item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.faq-question {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.faq-question::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(67, 97, 238, 0.1), transparent);
  transition: left var(--transition-normal);
}

.faq-question:hover::before {
  left: 100%;
}

.faq-question:hover {
  background-color: var(--color-bg-tertiary);
  transform: translateX(3px);
}

.faq-question:hover {
  background-color: var(--color-bg-tertiary);
}

.faq-arrow {
  font-size: 0.75rem;
  color: var(--color-primary);
  transition: transform var(--transition-fast);
}

.faq-arrow.rotated {
  transform: rotate(90deg);
}

.faq-text {
  flex: 1;
  font-weight: 500;
  color: var(--color-text-primary);
}

.faq-answer {
  padding: var(--spacing-md);
  background-color: var(--color-bg-primary);
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  line-height: 1.5;
  border-top: 1px solid var(--color-border);
}

/* 行动按钮 */
.action-buttons {
  display: flex;
  justify-content: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
}

.action-btn, .footer-btn {
  padding: var(--spacing-sm) var(--spacing-xl);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  box-shadow: var(--shadow-sm);
}

.footer-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: 0.875rem;
}

.action-btn::before, .footer-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left var(--transition-normal);
}

.action-btn:hover::before, .footer-btn:hover::before {
  left: 100%;
}

.action-btn:hover, .footer-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-btn:active, .footer-btn:active {
  transform: translateY(0);
}

.primary-btn {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: white;
  border: none;
}

.primary-btn:hover {
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  box-shadow: 0 4px 15px rgba(67, 97, 238, 0.3);
}

.secondary-btn {
  background: linear-gradient(135deg, var(--color-bg-tertiary), var(--color-bg-secondary));
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-light);
}

.secondary-btn:hover {
  background: linear-gradient(135deg, var(--color-bg-secondary), var(--color-bg-tertiary));
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* 空状态 */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.empty-container {
  text-align: center;
  max-width: 600px;
  padding: var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

.empty-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: var(--spacing-lg);
  animation: pulse 2s ease-in-out infinite;
}

.empty-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-md) 0;
  background: linear-gradient(90deg, var(--color-text-primary), var(--color-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.empty-description {
  font-size: 1rem;
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-lg) 0;
  line-height: 1.6;
}

.examples {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  justify-content: center;
}

.example-tag {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  background: linear-gradient(135deg, var(--color-bg-tertiary) 0%, var(--color-bg-secondary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-full);
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: 0.875rem;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.example-tag::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(67, 97, 238, 0.1), transparent);
  transition: left var(--transition-normal);
}

.example-tag:hover::before {
  left: 100%;
}

.example-tag:hover {
  background-color: var(--color-bg-tertiary);
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(67, 97, 238, 0.1);
}

.example-icon {
  font-size: 1rem;
}

/* 历史记录抽屉 */
.history-drawer {
  position: fixed;
  right: -400px;
  top: 0;
  bottom: 0;
  width: 400px;
  background: linear-gradient(180deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%);
  border-left: 1px solid var(--color-border-light);
  transition: right var(--transition-normal);
  z-index: 200;
  display: flex;
  flex-direction: column;
  box-shadow: -5px 0 20px rgba(0, 0, 0, 0.1);
}

.history-drawer.open {
  right: 0;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-light);
  background: linear-gradient(90deg, var(--color-bg-secondary) 0%, var(--color-bg-primary) 100%);
  position: relative;
}

.drawer-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
}

.drawer-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.drawer-close {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: var(--spacing-xs);
  color: var(--color-text-secondary);
  transition: color var(--transition-fast);
}

.drawer-close:hover {
  color: var(--color-text-primary);
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
}

.history-item {
  padding: var(--spacing-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.history-item:hover {
  background-color: var(--color-bg-secondary);
  border-color: var(--color-primary);
}

.history-query {
  font-size: 0.875rem;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.history-date {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.empty-history {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--spacing-xl);
  font-size: 0.875rem;
}

.history-toggle {
  position: fixed;
  right: var(--spacing-lg);
  bottom: var(--spacing-lg);
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: white;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow-md), 0 0 20px rgba(67, 97, 238, 0.3);
  transition: all var(--transition-normal);
  z-index: 100;
  position: relative;
  overflow: hidden;
}

.history-toggle::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left var(--transition-normal);
}

.history-toggle:hover::before {
  left: 100%;
}

.history-toggle:hover {
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  transform: scale(1.1);
  box-shadow: var(--shadow-lg), 0 0 25px rgba(67, 97, 238, 0.4);
}

.history-icon {
  font-size: 1.25rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .advisor-container {
    padding: 0 var(--spacing-md);
  }
  
  .page-title {
    font-size: 2rem;
  }
  
  .input-section, 
  .task-footer, 
  .action-buttons {
    flex-direction: column;
  }
  
  .examples {
    flex-direction: column;
    align-items: stretch;
  }
  
  .example-tag {
    width: 100%;
    justify-content: center;
  }
  
  .loading-container {
    flex-direction: column;
    text-align: center;
  }
  
  .task-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }
  
  .task-meta {
    flex-direction: column;
    gap: var(--spacing-xs);
  }
  
  .history-drawer {
    width: 100%;
    right: -100%;
  }
}

@media (max-width: 640px) {
  .input-field {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
  
  .input-field input {
    width: 100%;
  }
  
  .send-btn {
    width: 100%;
    justify-content: center;
  }
  
  .path-step {
    flex-direction: column;
  }
  
  .step-number {
    align-self: center;
  }
  
  .resource-item {
    flex-direction: column;
    text-align: center;
  }
}
</style>