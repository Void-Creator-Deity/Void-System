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
            <span class="btn-text">{{ isLoading ? '生成中...' : '发送' }}</span>
          </button>
        </div>
        
        <div class="input-tips">
          <span class="tip-icon">💡</span>
          <span class="tip-text">提示：请输入具体的目标</span>
        </div>
      </div>

      <!-- 预设问题标签 -->
      <div class="quick-topics">
        <div class="topics-header">快速目标：</div>
        <div class="topics-list">
          <button 
            v-for="topic in quickTopics" 
            :key="topic.id"
            class="topic-tag"
            @click="useQuickTopic(topic.text)"
          >
            {{ topic.text }}
          </button>
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
      <!-- 学习计划卡片 -->
      <div class="task-card">
        <div class="task-header">
          <h3 class="task-title">📋 任务</h3>
          <div class="task-meta">
            <span class="task-date">{{ formattedDate }}</span>
            <span class="task-duration">预计用时: {{ estimatedDuration }}</span>
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
          <button class="footer-btn secondary-btn">保存任务</button>
          <button class="footer-btn primary-btn">应用任务</button>
        </div>
      </div>
    </div>

    <!-- 历史记录抽屉 -->
    <div class="history-drawer" :class="{ 'open': showHistory }">
      <div class="drawer-header">
        <h3 class="drawer-title">历史记录</h3>
        <button class="drawer-close" @click="toggleHistory">×</button>
      </div>
      <div class="history-list">
        <div 
          v-for="(item, index) in historyItems" 
          :key="index"
          class="history-item"
          @click="loadHistoryItem(item)"
        >
          <div class="history-query">{{ item.query }}</div>
          <div class="history-date">{{ formatHistoryDate(item.timestamp) }}</div>
        </div>
        <div v-if="historyItems.length === 0" class="empty-history">暂无历史记录</div>
      </div>
    </div>
    
    <!-- 历史记录切换按钮 -->
    <button class="history-toggle" @click="toggleHistory">
      <span class="history-icon">🕒</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// 状态管理
const userQuery = ref('')
const isLoading = ref(false)
const progressPercent = ref(0)
const advisorResult = ref(null)
const showHistory = ref(false)
const expandedFaqIndex = ref(-1)

// 计算属性
const formattedDate = computed(() => {
  const date = new Date()
  return date.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
})

const estimatedDuration = computed(() => {
  return '2-3 小时'
})

// 快速主题列表
const quickTopics = [
  { id: 1, text: '学习Vue.js框架' },
  { id: 2, text: 'Python数据分析入门' },
  { id: 3, text: '前端性能优化' },
  { id: 4, text: '算法与数据结构' },
  { id: 5, text: 'Git版本控制' }
]

// 示例问题
const examples = [
  { id: 1, icon: '💻', text: '如何快速掌握JavaScript?' },
  { id: 2, icon: '📊', text: '推荐哪些数据可视化工具?' },
  { id: 3, icon: '🔒', text: '前端安全最佳实践' },
  { id: 4, icon: '⚡', text: '如何提高网页加载速度?' },
  { id: 5, icon: '🌐', text: '响应式设计技巧' },
  { id: 6, icon: '🧪', text: '自动化测试入门' }
]

// 模拟学习步骤数据
const learningSteps = [
  {
    title: '基础知识学习',
    description: '掌握核心概念和基本语法，建议通过官方文档和入门教程学习'
  },
  {
    title: '实际项目练习',
    description: '通过小型项目巩固所学知识，从简单到复杂逐步提升难度'
  },
  {
    title: '深入进阶内容',
    description: '学习高级特性和最佳实践，了解底层原理和优化技术'
  },
  {
    title: '社区交流与反馈',
    description: '参与开源项目或技术社区讨论，获取反馈并持续改进'
  }
]

// 模拟资源数据
const resources = [
  {
    icon: '📚',
    title: '官方文档',
    description: '全面的官方指南和API参考',
    link: 'javascript:void(0)'
  },
  {
    icon: '🎓',
    title: '在线课程',
    description: '结构化的视频教程和实践项目',
    link: 'javascript:void(0)'
  },
  {
    icon: '📝',
    title: '实战教程',
    description: '从入门到精通的步骤式教程',
    link: 'javascript:void(0)'
  },
  {
    icon: '💻',
    title: '代码示例',
    description: '丰富的示例代码和模板',
    link: 'javascript:void(0)'
  }
]

// 处理资源点击事件
const handleResourceClick = (resource, event) => {
  event.preventDefault();
  // 这里可以添加资源点击后的处理逻辑
  // 例如：显示提示信息、打开模态框展示资源详情等
  console.log('资源点击:', resource.title);
}

// 模拟常见问题数据
const faqs = [
  {
    question: '学习需要哪些前置知识?',
    answer: '建议具备基础的编程概念和逻辑思维能力。如果有相关编程语言经验会更容易上手，但不是必须的。',
    expanded: false
  },
  {
    question: '每天应该学习多长时间?',
    answer: '建议每天保持1-2小时的学习时间，持续性学习比集中性学习更有效。重要的是保持学习习惯。',
    expanded: false
  },
  {
    question: '如何解决学习中遇到的问题?',
    answer: '遇到问题时，可以先通过官方文档、搜索引擎和技术社区寻找答案。尝试自己解决问题是学习过程中的重要部分。',
    expanded: false
  }
]

// 模拟历史记录
const historyItems = ref([])

// 方法定义
const submitQuery = () => {
  if (!userQuery.value.trim() || isLoading.value) return
  
  isLoading.value = true
  progressPercent.value = 0
  
  // 模拟加载进度
  const progressInterval = setInterval(() => {
    progressPercent.value += Math.random() * 20
    if (progressPercent.value >= 100) {
      progressPercent.value = 100
      clearInterval(progressInterval)
      
      // 模拟完成加载
      setTimeout(() => {
        isLoading.value = false
        advisorResult.value = { query: userQuery.value }
        
        // 添加到历史记录
        historyItems.value.unshift({
          query: userQuery.value,
          timestamp: new Date()
        })
        
        // 清空输入
        userQuery.value = ''
      }, 500)
    }
  }, 300)
}

const useQuickTopic = (topic) => {
  userQuery.value = topic
  submitQuery()
}

const useExample = (example) => {
  userQuery.value = example
  submitQuery()
}

const toggleFaq = (index) => {
  faqs[index].expanded = !faqs[index].expanded
}

const toggleHistory = () => {
  showHistory.value = !showHistory.value
}

const loadHistoryItem = (item) => {
  userQuery.value = item.query
  showHistory.value = false
}

const formatHistoryDate = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', { 
    month: 'numeric', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
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
