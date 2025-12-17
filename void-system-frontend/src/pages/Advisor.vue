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
          <span class="tip-text">提示：请输入具体的目标，例如："学习Python数据分析"或"准备英语四级考试"</span>
        </div>
      </div>
      
      <!-- 快速主题 -->
      <div class="quick-topics">
        <div class="topics-header">
          <span class="topics-title">快速主题</span>
          <span v-if="isLoadingCategories" class="topics-loading">加载中...</span>
          <span v-else-if="categoriesError" class="topics-error">{{ categoriesError }}</span>
        </div>
        <div class="topics-list">
          <div 
            v-for="topic in quickTopics" 
            :key="topic.id"
            class="topic-tag"
            :class="{ 'preset-topic': topic.isPreset }"
            @click="useQuickTopic(topic.text)"
          >
            <span class="topic-icon">{{ topic.icon }}</span>
            <span class="topic-text">{{ topic.text }}</span>
            <span v-if="topic.isPreset" class="preset-badge">预设</span>
          </div>
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
      <!-- AI编辑提示 -->
      <div v-if="showAiEdit" class="ai-edit-notice">
        <div class="notice-content">
          <span class="notice-icon">⚠️</span>
          <span class="notice-text">AI返回的任务结构不符合要求，您可以编辑原始响应后重新构建任务</span>
        </div>
      </div>
      
      <!-- AI编辑面板 -->
      <div v-if="showAiEdit" class="ai-edit-panel">
        <div class="panel-header">
          <h3 class="panel-title">AI原始响应编辑</h3>
          <div class="panel-actions">
            <button class="panel-btn rebuild-btn" @click="rebuildFromEdit">
              <span class="btn-icon">🔄</span>
              <span class="btn-text">重新构建任务</span>
            </button>
          </div>
        </div>
        
        <div class="panel-content">
          <div class="edit-tips">
            <span class="tip-icon">💡</span>
            <span class="tip-text">提示：请确保编辑后的JSON格式包含steps数组，每个步骤包含title和description字段</span>
          </div>
          <div class="edit-template">
            <h4 class="template-title">默认模板参考：</h4>
            <pre class="template-content">{
  "response": "基于您的目标，我已经为您生成了详细的任务计划。",
  "steps": [
    {
      "title": "步骤1",
      "description": "描述内容1"
    },
    {
      "title": "步骤2",
      "description": "描述内容2"
    }
  ],
  "estimatedDuration": "45分钟"
}</pre>
          </div>
          <textarea 
            v-model="aiEditContent" 
            class="ai-edit-textarea"
            placeholder="编辑AI原始响应..."
            rows="15"
          ></textarea>
          <div v-if="aiEditError" class="edit-error">
            <span class="error-icon">❌</span>
            <span class="error-text">{{ aiEditError }}</span>
          </div>
          <div v-else-if="aiEditContent" class="edit-success">
            <span class="success-icon">✅</span>
            <span class="success-text">JSON格式正确，可以重新构建任务</span>
          </div>
        </div>
        
        <div class="panel-footer">
          <button class="footer-btn primary-btn" @click="rebuildFromEdit">
            <span class="btn-icon">🔄</span>
            <span class="btn-text">重新构建任务</span>
          </button>
        </div>
      </div>
      
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
    
    <!-- 历史记录抽屉 -->
    <div class="history-drawer" :class="{ open: showHistory }">
      <div class="drawer-header">
        <h3 class="drawer-title">历史记录</h3>
        <div class="drawer-actions">
          <button class="drawer-btn clear-btn" @click="clearHistory">
            <span class="btn-text">清除</span>
          </button>
          <button class="drawer-btn close-btn" @click="toggleHistory">
            <span class="btn-text">关闭</span>
          </button>
        </div>
      </div>
      
      <div class="history-list">
        <div v-if="historyList.length === 0" class="empty-history">
          <span class="empty-icon">📋</span>
          <p class="empty-text">暂无历史记录</p>
          <p class="empty-subtext">开始生成任务建议，历史记录将保存在这里</p>
        </div>
        
        <div 
          v-for="item in historyList" 
          :key="item.id"
          class="history-item"
          @click="restoreFromHistory(item)"
        >
          <div class="history-item-header">
            <h4 class="history-query">{{ item.query }}</h4>
            <span class="history-date">{{ new Date(item.createdAt).toLocaleString() }}</span>
          </div>
          <div class="history-item-content">
              <p class="history-response">{{ typeof item.response === 'string' ? item.response.substring(0, 100) : JSON.stringify(item.response).substring(0, 100) }}...</p>
              <div class="history-steps-count">
                <span class="steps-count">{{ item.steps.length }} 个步骤</span>
              </div>
            </div>
        </div>
      </div>
    </div>
    
    <!-- 历史记录切换按钮 -->
    <button class="history-toggle" @click="toggleHistory">
      <span class="history-icon">📋</span>
    </button>
  </div>
</template>

<script setup>
/**
 * Advisor Component - Learning Task Advisor
 * -------------------------------------------
 * 学习任务建议页面，根据用户输入生成结构化的学习任务计划
 */

import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdvisor } from '@/api/ai'
import api from '@/api/index'
import { getTaskCategories } from '@/api/taskCategories'

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
const showHistory = ref(false)

// AI原始返回内容和编辑状态
const aiRawResponse = ref('')
const showAiEdit = ref(false)
const aiEditContent = ref('')
const aiEditError = ref('')

// 快速主题列表
const quickTopics = ref([])
const isLoadingCategories = ref(false)
const categoriesError = ref('')

// 历史记录（从localStorage获取）
const historyList = ref(JSON.parse(localStorage.getItem('advisor_history')) || [])

// 加载点动画
const updateLoadingDots = () => {
  let dots = ''
  const interval = setInterval(() => {
    dots = dots.length < 3 ? dots + '.' : ''
    loadingDots.value = dots
  }, 500)
  return interval
}

// 监听AI编辑内容变化，实时验证JSON格式
watch(aiEditContent, (newContent) => {
  if (!newContent.trim()) {
    aiEditError.value = ''
    return
  }
  
  try {
    const parsed = JSON.parse(newContent)
    
    // 验证基本结构
    if (!parsed.steps || !Array.isArray(parsed.steps)) {
      aiEditError.value = 'JSON格式错误：缺少steps数组'
      return
    }
    
    // 验证每个步骤的结构
    const invalidSteps = parsed.steps.filter(step => 
      !step || typeof step !== 'object' || 
      !step.title || typeof step.title !== 'string' || 
      !step.description || typeof step.description !== 'string'
    )
    
    if (invalidSteps.length > 0) {
      aiEditError.value = 'JSON格式错误：部分步骤缺少title或description字段'
      return
    }
    
    aiEditError.value = ''
  } catch (error) {
    aiEditError.value = `JSON格式错误：${error.message}`
  }
})

// 初始化获取任务类别
onMounted(async () => {
  try {
    isLoadingCategories.value = true
    categoriesError.value = ''
    
    const categories = await getTaskCategories()
    
    // 确保categories是数组，防止API返回非数组数据时出错
    if (Array.isArray(categories)) {
      // 将后端返回的类别转换为前端需要的格式
      quickTopics.value = categories.map((category, index) => ({
        id: category.category_id || index + 1,
        text: category.category_name,
        icon: category.icon,
        isPreset: category.is_preset
      }))
    } else {
      // 如果API返回的不是数组，使用默认主题
      console.warn('API返回的任务类别数据不是数组，使用默认主题')
      quickTopics.value = [
        { id: 1, text: '学习Python数据分析', icon: '🐍', isPreset: true },
        { id: 2, text: '准备英语四级考试', icon: '📚', isPreset: true },
        { id: 3, text: '学习Vue 3框架', icon: '💻', isPreset: true },
        { id: 4, text: '减肥健身计划', icon: '🏃‍♂️', isPreset: true },
        { id: 5, text: '学习摄影技巧', icon: '📷', isPreset: true },
        { id: 6, text: '准备考研数学', icon: '📐', isPreset: true },
        { id: 7, text: '学习UI设计', icon: '🎨', isPreset: true },
        { id: 8, text: '学习吉他基础', icon: '🎸', isPreset: true }
      ]
    }
  } catch (error) {
    console.error('获取任务类别失败:', error)
    categoriesError.value = '获取任务类别失败，使用默认主题'
    
    // 使用默认主题作为备选
    quickTopics.value = [
      { id: 1, text: '学习Python数据分析', icon: '🐍', isPreset: true },
      { id: 2, text: '准备英语四级考试', icon: '📚', isPreset: true },
      { id: 3, text: '学习Vue 3框架', icon: '💻', isPreset: true },
      { id: 4, text: '减肥健身计划', icon: '🏃‍♂️', isPreset: true },
      { id: 5, text: '学习摄影技巧', icon: '📷', isPreset: true },
      { id: 6, text: '准备考研数学', icon: '📐', isPreset: true },
      { id: 7, text: '学习UI设计', icon: '🎨', isPreset: true },
      { id: 8, text: '学习吉他基础', icon: '🎸', isPreset: true }
    ]
  } finally {
    isLoadingCategories.value = false
  }
})

// ==================== 计算属性 ====================

/**
 * 从 advisorResult 中解析任务步骤
 */
const learningSteps = computed(() => {
  try {
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
  } catch (error) {
    console.error('解析任务步骤失败:', error)
    return []
  }
})

/**
 * 从 advisorResult 中解析估计用时
 */
const estimatedDuration = computed(() => {
  try {
    if (advisorResult.value && 
        advisorResult.value.estimatedDuration && 
        typeof advisorResult.value.estimatedDuration === 'string') {
      return advisorResult.value.estimatedDuration
    }
    
    return ''
  } catch (error) {
    console.error('解析估计用时失败:', error)
    return ''
  }
})

/**
 * 检查是否是有效的任务结构
 */
const isValidTaskStructure = computed(() => {
  try {
    if (!advisorResult.value) return false
    
    const hasRequiredFields = advisorResult.value.query && 
                              Array.isArray(advisorResult.value.steps) && 
                              advisorResult.value.steps.length > 0
    
    if (!hasRequiredFields) return false
    
    const hasValidSteps = advisorResult.value.steps.every(step => 
      step && typeof step === 'object' && 
      step.title && typeof step.title === 'string' && 
      step.description && typeof step.description === 'string'
    )
    
    return hasValidSteps
  } catch (error) {
    console.error('检查任务结构失败:', error)
    return false
  }
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
 * 保存历史记录到localStorage
 * @param {Object} result - 任务建议结果
 */
const saveToHistory = (result) => {
  const historyItem = {
    id: Date.now(),
    query: result.query,
    response: result.response,
    createdAt: new Date().toISOString(),
    steps: result.steps
  }
  
  // 添加到历史记录列表
  historyList.value.unshift(historyItem)
  
  // 限制历史记录数量
  if (historyList.value.length > 20) {
    historyList.value = historyList.value.slice(0, 20)
  }
  
  // 保存到localStorage
  localStorage.setItem('advisor_history', JSON.stringify(historyList.value))
}

/**
 * 解析AI返回结果
 * @param {string|Object} result - AI返回的原始结果
 * @param {string} query - 用户查询
 * @returns {Object} 解析后的任务结果
 */
const parseAiResult = (result, query) => {
  // 保存原始返回内容
  aiRawResponse.value = typeof result === 'string' ? result : JSON.stringify(result, null, 2)
  
  try {
    // 尝试解析JSON格式的结果
    const parsedResult = typeof result === 'string' ? JSON.parse(result) : result
    
    // 清理结果，确保不包含数字键名或其他无效数据
    const cleanResult = {
      response: parsedResult.response || `基于您的目标"${query}"，我已经为您生成了详细的任务计划。`,
      steps: [],
      estimatedDuration: parsedResult.estimatedDuration || '45分钟'
    }
    
    // 确保steps是有效的数组，并且每个步骤都有正确的格式
    if (parsedResult.steps && Array.isArray(parsedResult.steps)) {
      cleanResult.steps = parsedResult.steps
        .filter(step => step && typeof step === 'object')
        .map(step => {
          // 清理步骤对象，只保留有效的字符串属性
          const cleanStep = {
            title: typeof step.title === 'string' ? step.title : '未命名步骤',
            description: typeof step.description === 'string' ? step.description : '无描述'
          }
          
          // 移除所有数字键名和无效属性
          return Object.fromEntries(
            Object.entries(cleanStep).filter(([key]) => isNaN(Number(key)))
          )
        })
    }
    
    // 检查是否为有效的任务结构
    if (cleanResult.steps.length > 0) {
      const finalResult = {
        query: query,
        ...cleanResult,
        createdAt: new Date(),
        additionalInfo: 'AI生成的任务计划'
      }
      
      return finalResult
    }
    
    // 如果步骤不符合要求，标记为需要编辑
    showAiEdit.value = true
    aiEditContent.value = aiRawResponse.value
    
    return {
      query: query,
      response: cleanResult.response,
      steps: [
        {
          title: '准备阶段',
          description: `为实现"${query}"目标，收集必要的资源和信息`
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
      estimatedDuration: cleanResult.estimatedDuration,
      createdAt: new Date(),
      additionalInfo: 'AI生成的任务计划（需要编辑）'
    }
  } catch (e) {
    // 如果解析失败，标记为需要编辑
    showAiEdit.value = true
    aiEditContent.value = aiRawResponse.value
    
    return {
      query: query,
      response: result || `基于您的目标"${query}"，我已经为您生成了详细的任务计划。`,
      steps: [
        {
          title: '准备阶段',
          description: `为实现"${query}"目标，收集必要的资源和信息`
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
      additionalInfo: 'AI生成的任务计划（需要编辑）'
    }
  }
}

/**
 * 从编辑内容重新构建任务
 */
const rebuildFromEdit = () => {
  try {
    const parsedResult = JSON.parse(aiEditContent.value)
    const query = advisorResult.value.query
    
    // 清理结果，确保不包含数字键名或其他无效数据
    const cleanResult = {
      response: parsedResult.response || `基于您的目标"${query}"，我已经为您生成了详细的任务计划。`,
      steps: [],
      estimatedDuration: parsedResult.estimatedDuration || '45分钟'
    }
    
    // 确保steps是有效的数组，并且每个步骤都有正确的格式
    if (parsedResult.steps && Array.isArray(parsedResult.steps)) {
      cleanResult.steps = parsedResult.steps
        .filter(step => step && typeof step === 'object')
        .map(step => {
          // 清理步骤对象，只保留有效的字符串属性
          const cleanStep = {
            title: typeof step.title === 'string' ? step.title : '未命名步骤',
            description: typeof step.description === 'string' ? step.description : '无描述'
          }
          
          // 移除所有数字键名和无效属性
          return Object.fromEntries(
            Object.entries(cleanStep).filter(([key]) => isNaN(Number(key)))
          )
        })
    } else {
      // 使用默认步骤
      cleanResult.steps = [
        {
          title: '准备阶段',
          description: `为实现"${query}"目标，收集必要的资源和信息`
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
      ]
    }
    
    const finalResult = {
      query: query,
      ...cleanResult,
      createdAt: new Date(),
      additionalInfo: '从编辑内容重新构建的任务计划'
    }
    
    advisorResult.value = finalResult
    showAiEdit.value = false
    
    // 保存到历史记录
    saveToHistory(finalResult)
    
    ElMessage.success('任务重新构建成功')
  } catch (error) {
    console.error('重新构建任务失败:', error)
    ElMessage.error('重新构建任务失败，请检查编辑内容格式是否正确')
  }
}

/**
   * 提交查询并生成任务建议
   */
  const submitQuery = async () => {
    // 重置状态
    errorMessage.value = ''
    successMessage.value = ''
    showAiEdit.value = false
    
    // 验证输入
    const query = userQuery.value.trim()
    if (!query) {
      errorMessage.value = '请输入有效的学习目标'
      ElMessage.warning('请输入学习目标')
      return
    }
    
    // 设置加载状态
    isLoading.value = true
    progressPercent.value = 0
    
    // 定义定时器变量，确保在finally块中可用
    let progressInterval = null
    let dotsInterval = null
    
    try {
      // 模拟进度更新
      progressInterval = setInterval(() => {
        if (progressPercent.value < 90) {
          progressPercent.value += Math.floor(Math.random() * 10) + 5
        }
      }, 200)
      
      // 加载点动画
      dotsInterval = updateLoadingDots()
      
      // 调用 AI API 获取任务建议
      console.log('开始调用getAdvisor API，topic:', query)
      const result = await getAdvisor(query)
      console.log('getAdvisor API调用成功，result:', result)
      
      // 清除进度更新定时器
      clearInterval(progressInterval)
      progressPercent.value = 100
      
      // 解析 AI 返回的结果
      console.log('开始解析AI结果，result:', result, 'query:', query)
      const finalResult = parseAiResult(result, query)
      console.log('AI结果解析成功，finalResult:', finalResult)
      
      advisorResult.value = finalResult
      
      // 保存到历史记录
      saveToHistory(finalResult)
      
      ElMessage.success('任务建议生成成功')
    } catch (error) {
      console.error('生成任务失败:', error)
      console.error('错误详情:', error.response?.data || error.message)
      console.error('错误堆栈:', error.stack)
      errorMessage.value = '生成任务失败，请稍后重试'
      ElMessage.error(error.response?.data?.detail || '生成任务失败，请稍后重试')
    } finally {
        // 确保加载状态被重置
        setTimeout(() => {
          isLoading.value = false
          progressPercent.value = 0
          if (progressInterval) clearInterval(progressInterval)
          if (dotsInterval) clearInterval(dotsInterval)
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
    
    // 确保task_name不是空字符串
    const taskName = advisorResult.value.query.trim()
    if (!taskName) {
      errorMessage.value = '任务名称不能为空'
      ElMessage.warning('任务名称不能为空')
      isLoading.value = false
      return
    }
    
    // 确保estimated_time是一个有效的整数
    const estimatedTime = parseInt(advisorResult.value.estimatedDuration)
    const finalEstimatedTime = isNaN(estimatedTime) ? 45 : estimatedTime
    
    // 确保description是一个字符串，而不是一个对象
    let description = ''
    if (advisorResult.value.response) {
      if (typeof advisorResult.value.response === 'string') {
        description = advisorResult.value.response
      } else if (typeof advisorResult.value.response === 'object') {
        // 如果是对象，尝试获取content字段或转换为字符串
        if (advisorResult.value.response.content) {
          description = advisorResult.value.response.content
        } else {
          description = JSON.stringify(advisorResult.value.response)
        }
      } else {
        description = String(advisorResult.value.response)
      }
    }
    
    // 构建任务数据，确保与后端API期望的格式匹配
    // 移除related_attrs字段，让后端使用默认值None
    const taskData = {
      task_name: taskName,
      description: description || '',
      // related_attrs: null,  // 移除这个字段，让后端使用默认值None
      estimated_time: finalEstimatedTime,  // 确保是有效的整数
      reward_coins: 20  // 默认奖励，确保是有效的整数
    }
    
    console.log('发布任务数据:', taskData)
    
    // 调用 API 创建任务
    const response = await api.post('/api/tasks', taskData)
    
    console.log('发布任务响应:', response)
    
    successMessage.value = '任务发布成功！'
    ElMessage.success('任务已成功发布到任务系统，您可以在首页查看和管理该任务')
    
    // 清空结果，准备下一个查询
    advisorResult.value = null
    userQuery.value = ''
  } catch (error) {
    console.error('发布任务失败:', error)
    // 显示详细的错误信息，包括后端返回的具体错误
    let errorDetail = '未知错误'
    
    // 打印完整的错误对象，用于调试
    console.log('完整错误对象:', error)
    
    if (error.response) {
      // 服务器返回了错误响应
      console.log('错误响应状态码:', error.response.status)
      console.log('错误响应头:', error.response.headers)
      console.log('错误响应数据:', error.response.data)
      console.log('错误响应数据类型:', typeof error.response.data)
      console.log('错误响应数据详细:', JSON.stringify(error.response.data, null, 2))
      
      // 确保error.response.data是字符串或对象
      const responseData = error.response.data
      
      if (typeof responseData === 'string') {
        // 如果是字符串，直接使用
        errorDetail = responseData
      } else if (typeof responseData === 'object') {
        // 如果是对象，尝试获取详细信息
        if (responseData.detail) {
          errorDetail = responseData.detail
        } else if (responseData.errors) {
          // 处理 Pydantic 验证错误
          const errors = responseData.errors
          if (Array.isArray(errors)) {
            errorDetail = errors.map(err => `${err.loc.join('.')}: ${err.msg}`).join('; ')
          } else {
            errorDetail = JSON.stringify(errors, null, 2)
          }
        } else {
          // 尝试将对象转换为字符串
          try {
            errorDetail = JSON.stringify(responseData, null, 2)
          } catch (e) {
            errorDetail = '无法解析的错误对象'
          }
        }
      } else {
        // 其他类型，转换为字符串
        errorDetail = String(responseData)
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      errorDetail = '服务器没有响应'
    } else if (error.message) {
      // 请求配置出错
      errorDetail = error.message
    } else {
      // 其他错误
      errorDetail = String(error)
    }
    
    console.log('最终错误信息:', errorDetail)
    
    errorMessage.value = `发布任务失败: ${errorDetail}`
    ElMessage.error(`发布任务失败: ${errorDetail}`)
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
  try {
    if (!advisorResult.value) return '暂无响应数据'
    return JSON.stringify(advisorResult.value, null, 2)
  } catch (error) {
    console.error('格式化响应数据失败:', error)
    return '响应数据格式化失败: ' + error.message
  }
})

/**
 * 使用快速主题
 * @param {string} topic - 预设主题
 */
const useQuickTopic = (topic) => {
  userQuery.value = topic
  submitQuery()
}

/**
 * 从历史记录中恢复查询
 * @param {Object} historyItem - 历史记录项
 */
const restoreFromHistory = (historyItem) => {
  userQuery.value = historyItem.query
  advisorResult.value = {
    query: historyItem.query,
    response: historyItem.response,
    steps: historyItem.steps,
    estimatedDuration: '45分钟',
    createdAt: new Date(historyItem.createdAt),
    additionalInfo: '从历史记录恢复'
  }
  
  // 关闭历史记录抽屉
  showHistory.value = false
}

/**
 * 清除历史记录
 */
const clearHistory = () => {
  if (confirm('确定要清除所有历史记录吗？')) {
    historyList.value = []
    localStorage.removeItem('advisor_history')
    ElMessage.success('历史记录已清除')
  }
}

/**
 * 切换历史记录抽屉显示
 */
const toggleHistory = () => {
  showHistory.value = !showHistory.value
}
</script>

<style scoped>
/* 消息区域样式 */
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

/* AI响应区域样式 */
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

/* 原始响应区域样式 */
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
  transition: left var(--transition-normal);
}

.step-number:hover::before {
  left: 100%;
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

/* 行动按钮 */
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

/* AI编辑提示 */
.ai-edit-notice {
  background-color: rgba(255, 165, 0, 0.1);
  border: 1px solid #ffa500;
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.notice-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: #ffa500;
  font-weight: 500;
}

.notice-icon {
  font-size: 1.2rem;
}

/* AI编辑面板 */
.ai-edit-panel {
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-lg);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

/* 编辑模板 */
.edit-template {
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.template-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.template-content {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
  background: rgba(0, 0, 0, 0.01);
  padding: var(--spacing-sm);
  border-radius: var(--radius-sm);
  overflow-x: auto;
}

/* 编辑错误提示 */
.edit-error {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
  color: #d32f2f;
  font-size: 0.875rem;
}

.edit-success {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
  color: #2e7d32;
  font-size: 0.875rem;
}

.error-icon, .success-icon {
  font-size: 1rem;
}

.error-text, .success-text {
  flex: 1;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  background: linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%);
  border-bottom: 1px solid var(--color-border-light);
}

.panel-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.panel-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.panel-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-normal);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.rebuild-btn {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: white;
  border: none;
}

.rebuild-btn:hover {
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-primary));
  box-shadow: 0 4px 15px rgba(67, 97, 238, 0.3);
}

.panel-content {
  padding: var(--spacing-lg);
}

.edit-tips {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-md);
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.ai-edit-textarea {
  width: 100%;
  padding: var(--spacing-md);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%);
  color: var(--color-text-primary);
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  resize: vertical;
  min-height: 200px;
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
}

.ai-edit-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
}

.panel-footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--spacing-lg);
  border-top: 1px solid var(--color-border-light);
  background: linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%);
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
  .action-buttons,
  .panel-header,
  .panel-actions {
    flex-direction: column;
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
  
  .panel-actions {
    width: 100%;
    margin-top: var(--spacing-md);
  }
  
  .panel-btn {
    width: 100%;
    justify-content: center;
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
  
  .ai-edit-textarea {
    font-size: 0.75rem;
  }
}
</style>