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
            :disabled="isLoading"
          />
          <button 
            class="send-btn" 
            @click="submitQuery"
            :disabled="isLoading || !userQuery.trim()"
          >
            <span class="btn-icon">{{ isLoading ? '⏱️' : '🚀' }}</span>
            <span class="btn-text">{{ isLoading ? '分析中...' : '生成任务' }}</span>
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
          <h3 class="loading-title">正在分析您的目标.</h3>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <p class="loading-description">正在生成个性化任务</p>
        </div>
      </div>
    </div>

    <!-- 消息提示区域 -->
    <div v-if="errorMessage" class="message-area error-message">
      <span class="message-icon">⚠️</span>
      <span>{{ errorMessage }}</span>
    </div>
    <div v-if="successMessage" class="message-area success-message">
      <span class="message-icon">✅</span>
      <span>{{ successMessage }}</span>
    </div>

    <!-- 结果区域 -->
    <div v-else-if="advisorResult && !isLoading" class="result-section">
      <!-- 任务卡片 -->
      <div class="task-card">
        <div class="task-header">
          <h3 class="task-title">📋 任务计划</h3>
          <div class="task-meta">
            <span class="task-date">{{ formattedDate }}</span>
            <span v-if="estimatedDuration" class="task-duration">预计用时: {{ estimatedDuration }}</span>
          </div>
        </div>
        
        <div class="task-content">
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
          <button class="footer-btn secondary-btn" @click="publishTask" :disabled="isLoading || !isValidTaskStructure">
            <span class="btn-icon">{{ isLoading ? '⏱️' : '🚀' }}</span>
            <span class="btn-text">{{ isLoading ? '发布中...' : '发布任务' }}</span>
          </button>
          <button class="footer-btn primary-btn" disabled>
            <span class="btn-icon">💾</span>
            <span class="btn-text">应用任务</span>
          </button>
        </div>
      </div>
      
      <!-- 完整后端响应 -->
      <div class="raw-response-section">
        <h3 class="section-title">📊 完整后端响应</h3>
        <div class="raw-response-content">
          <pre>{{ formattedFullResponse }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Advisor Component - Learning Task Advisor
 * -------------------------------------------
 * 学习任务建议页面，根据用户输入生成结构化的学习任务计划
 */

import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdvisor } from '@/api/ai'
import api from '@/api/index'

// ==================== 响应式状态 ====================
const userQuery = ref('')
const isLoading = ref(false)
const progressPercent = ref(0)
const advisorResult = ref(null)
const errorMessage = ref('')
const successMessage = ref('')
const loadingTitle = ref('正在分析您的目标')
const loadingDescription = ref('虚空炼金术士正在提炼您的任务精华')
const loadingDots = ref('')

// 加载点动画
const updateLoadingDots = () => {
  let dots = ''
  const interval = setInterval(() => {
    dots = dots.length < 3 ? dots + '.' : ''
    loadingDots.value = dots
  }, 500)
  return interval
}

// ==================== 计算属性 ====================

/**
 * 从 advisorResult 中解析任务步骤
 */
const learningSteps = computed(() => {
  if (!advisorResult.value) {
    return []
  }
  
  if (Array.isArray(advisorResult.value.steps)) {
    return advisorResult.value.steps.filter(step => 
      step && typeof step === 'object' && 
      step.title && typeof step.title === 'string' && 
      step.description && typeof step.description === 'string'
    )
  }
  
  return []
})

/**
 * 从 advisorResult 中解析估计用时
 */
const estimatedDuration = computed(() => {
  if (advisorResult.value && 
      advisorResult.value.estimatedDuration && 
      typeof advisorResult.value.estimatedDuration === 'string') {
    return advisorResult.value.estimatedDuration
  }
  
  return ''
})

/**
 * 检查是否是有效的任务结构
 */
const isValidTaskStructure = computed(() => {
  if (!advisorResult.value) return false
  
  const hasRequiredFields = advisorResult.value.query && 
                            Array.isArray(advisorResult.value.steps) && 
                            advisorResult.value.steps.length > 0
  
  const hasValidSteps = advisorResult.value.steps.every(step => 
    step && typeof step === 'object' && 
    step.title && typeof step.title === 'string' && 
    step.description && typeof step.description === 'string'
  )
  
  return hasRequiredFields && hasValidSteps
})

/**
 * 格式化当前日期
 */
const formattedDate = computed(() => {
  const date = new Date()
  return date.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
})

// ==================== 业务逻辑 ====================

/**
 * 提交查询并生成任务建议
 */
const submitQuery = async () => {
  // 重置消息
  errorMessage.value = ''
  successMessage.value = ''
  
  // 验证输入
  if (!userQuery.value.trim()) {
    errorMessage.value = '请输入有效的学习目标'
    ElMessage.warning('请输入学习目标')
    return
  }
  
  // 设置加载状态
  isLoading.value = true
  progressPercent.value = 0
  
  try {
    // 模拟进度更新
    const progressInterval = setInterval(() => {
      if (progressPercent.value < 90) {
        progressPercent.value += Math.floor(Math.random() * 10) + 5
      }
    }, 200)
    
    // 加载点动画
    const dotsInterval = updateLoadingDots()
    
    // 调用 AI API 获取任务建议
    const result = await getAdvisor(userQuery.value.trim())
    
    // 清除进度更新定时器
    clearInterval(progressInterval)
    progressPercent.value = 100
    
    // 解析 AI 返回的结果
    // 注意：实际返回格式可能因 AI 模型而异，需要根据实际情况调整
    advisorResult.value = {
      query: userQuery.value,
      response: result || `基于您的目标"${userQuery.value}"，我已经为您生成了详细的任务计划。`,
      steps: learningSteps.value.length > 0 ? learningSteps.value : [
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
      estimatedDuration: estimatedDuration.value || '45分钟',
      createdAt: new Date(),
      additionalInfo: '这是一个标准的任务执行流程，适用于大多数目标实现场景'
    }
    
    ElMessage.success('任务建议生成成功')
  } catch (error) {
    console.error('生成任务失败:', error)
    errorMessage.value = '生成任务失败，请稍后重试'
    ElMessage.error(error.response?.data?.detail || '生成任务失败，请稍后重试')
  } finally {
      // 确保加载状态被重置
      setTimeout(() => {
        isLoading.value = false
        progressPercent.value = 0
        clearInterval(dotsInterval)
        loadingDots.value = ''
      }, 500)
    }
}

/**
 * 发布任务到任务系统
 */
const publishTask = async () => {
  // 重置消息
  errorMessage.value = ''
  successMessage.value = ''
  
  // 验证任务结构
  if (!isValidTaskStructure.value) {
    errorMessage.value = '任务结构不符合要求，请重新生成任务'
    ElMessage.warning('请先生成有效的任务建议')
    return
  }
  
  try {
    isLoading.value = true
    
    // 构建任务数据
    const taskData = {
      task_name: advisorResult.value.query,
      description: advisorResult.value.response || '',
      estimated_time: 45,  // 默认45分钟
      reward_coins: 20
    }
    
    // 调用 API 创建任务
    await api.post('/tasks', taskData)
    
    successMessage.value = '任务发布成功！'
    ElMessage.success('任务已成功发布到任务系统')
    
    // 可选：清空结果，准备下一个查询
    // advisorResult.value = null
    // userQuery.value = ''
  } catch (error) {
    console.error('发布任务失败:', error)
    errorMessage.value = '发布任务失败，请稍后重试'
    ElMessage.error(error.response?.data?.detail || '发布任务失败，请稍后重试')
  } finally {
    setTimeout(() => {
      isLoading.value = false
    }, 500)
  }
}

/**
 * 格式化完整响应的计算属性（用于调试）
 */
const formattedFullResponse = computed(() => {
  if (!advisorResult.value) return '暂无响应数据'
  return JSON.stringify(advisorResult.value, null, 2)
})

/**
 * 使用快速主题
 * @param {string} topic - 预设主题
 */
const useQuickTopic = (topic) => {
  userQuery.value = topic
  submitQuery()
}
</script>

<style scoped>
/* 新增样式 */
  .message-area {
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .error-message {
    background-color: rgba(255, 99, 71, 0.1);
    border: 1px solid tomato;
    color: #d32f2f;
  }
  
  .success-message {
    background-color: rgba(76, 175, 80, 0.1);
    border: 1px solid #4caf50;
    color: #2e7d32;
  }
  
  .message-icon {
    font-size: 1.2rem;
  }
  
  .ai-response-section {
    background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }
  
  .section-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    color: #333;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .ai-response-content {
    font-size: 1rem;
    line-height: 1.6;
    color: #444;
  }
  
  .raw-response-section {
    background: rgba(0, 0, 0, 0.02);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-top: 1.5rem;
    border: 1px solid #e0e0e0;
  }
  
  .raw-response-content {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    max-height: 300px;
    overflow-y: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  
  .raw-response-content pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
 /* 新增样式 */
  .message-area {
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .error-message {
    background-color: rgba(255, 99, 71, 0.1);
    border: 1px solid tomato;
    color: #d32f2f;
  }
  
  .success-message {
    background-color: rgba(76, 175, 80, 0.1);
    border: 1px solid #4caf50;
    color: #2e7d32;
  }
  
  .message-icon {
    font-size: 1.2rem;
  }
  
  .ai-response-section {
    background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }
  
  .section-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    color: #333;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .ai-response-content {
    font-size: 1rem;
    line-height: 1.6;
    color: #444;
  }
  
  .raw-response-section {
    background: rgba(0, 0, 0, 0.02);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-top: 1.5rem;
    border: 1px solid #e0e0e0;
  }
  
  .raw-response-content {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    max-height: 300px;
    overflow-y: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  
  .raw-response-content pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
/* 新增样式 */
  .message-area {
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .error-message {
    background-color: rgba(255, 99, 71, 0.1);
    border: 1px solid tomato;
    color: #d32f2f;
  }
  
  .success-message {
    background-color: rgba(76, 175, 80, 0.1);
    border: 1px solid #4caf50;
    color: #2e7d32;
  }
  
  .message-icon {
    font-size: 1.2rem;
  }
  
  .ai-response-section {
    background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }
  
  .section-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    color: #333;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .ai-response-content {
    font-size: 1rem;
    line-height: 1.6;
    color: #444;
  }
  
  .raw-response-section {
    background: rgba(0, 0, 0, 0.02);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-top: 1.5rem;
    border: 1px solid #e0e0e0;
  }
  
  .raw-response-content {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    max-height: 300px;
    overflow-y: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  
  .raw-response-content pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
/* 新增样式 */
  .message-area {
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .error-message {
    background-color: rgba(255, 99, 71, 0.1);
    border: 1px solid tomato;
    color: #d32f2f;
  }
  
  .success-message {
    background-color: rgba(76, 175, 80, 0.1);
    border: 1px solid #4caf50;
    color: #2e7d32;
  }
  
  .message-icon {
    font-size: 1.2rem;
  }
  
  .ai-response-section {
    background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }
  
  .section-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    color: #333;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .ai-response-content {
    font-size: 1rem;
    line-height: 1.6;
    color: #444;
  }
  
  .raw-response-section {
    background: rgba(0, 0, 0, 0.02);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-top: 1.5rem;
    border: 1px solid #e0e0e0;
  }
  
  .raw-response-content {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    max-height: 300px;
    overflow-y: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  
  .raw-response-content pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
  /* 新增样式 */
  .message-area {
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .error-message {
    background-color: rgba(255, 99, 71, 0.1);
    border: 1px solid tomato;
    color: #d32f2f;
  }
  
  .success-message {
    background-color: rgba(76, 175, 80, 0.1);
    border: 1px solid #4caf50;
    color: #2e7d32;
  }
  
  .message-icon {
    font-size: 1.2rem;
  }
  
  .ai-response-section {
    background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }
  
  .section-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    color: #333;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .ai-response-content {
    font-size: 1rem;
    line-height: 1.6;
    color: #444;
  }
  
  .raw-response-section {
    background: rgba(0, 0, 0, 0.02);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-top: 1.5rem;
    border: 1px solid #e0e0e0;
  }
  
  .raw-response-content {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    max-height: 300px;
    overflow-y: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  
  .raw-response-content pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
/* 新增样式 */
  .message-area {
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .error-message {
    background-color: rgba(255, 99, 71, 0.1);
    border: 1px solid tomato;
    color: #d32f2f;
  }
  
  .success-message {
    background-color: rgba(76, 175, 80, 0.1);
    border: 1px solid #4caf50;
    color: #2e7d32;
  }
  
  .message-icon {
    font-size: 1.2rem;
  }
  
  .ai-response-section {
    background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  }
  
  .section-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    color: #333;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .ai-response-content {
    font-size: 1rem;
    line-height: 1.6;
    color: #444;
  }
  
  .raw-response-section {
    background: rgba(0, 0, 0, 0.02);
    padding: 1.5rem;
    border-radius: 0.75rem;
    margin-top: 1.5rem;
    border: 1px solid #e0e0e0;
  }
  
  .raw-response-content {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    max-height: 300px;
    overflow-y: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  
  .raw-response-content pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
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