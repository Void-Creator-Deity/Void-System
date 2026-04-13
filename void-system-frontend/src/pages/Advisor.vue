<template>
  <div class="void-page-container advisor-page">
    <div class="void-content">
      <header class="page-header">
        <h1 class="logo-text"><span class="void-text-gradient">任务顾问</span></h1>
        <p class="subtitle">通过系统引擎进行实时分析，生成结构化任务推进路径。</p>
      </header>

      <!-- Input Section -->
      <section class="selection-box void-card animate-float">
        <div class="input-group">
          <div class="input-icon">🧬</div>
          <el-input 
            v-model="userQuery" 
            placeholder="输入你的目标... (例如：精通 Rust 异步编程)"
            class="void-input"
            @keyup.enter="submitQuery"
            :disabled="isLoading"
            clearable
          />
          <el-button 
            type="primary" 
            @click="submitQuery"
            class="void-btn primary big"
            :loading="isLoading"
            :disabled="isLoading || !userQuery.trim()"
          >
            {{ isLoading ? '分析中' : '生成路径' }}
          </el-button>
        </div>
        <div class="input-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>建议：目标描述越具体，生成结果越可执行。</span>
        </div>
      </section>

      <!-- Quick Topics -->
      <section class="quick-topics" v-if="quickTopics.length > 0">
        <h3 class="section-label">预设领域</h3>
        <div class="topics-grid">
          <div 
            v-for="topic in quickTopics" 
            :key="topic.id"
            class="topic-chip void-card interactive"
            @click="useQuickTopic(topic.text)"
          >
            <span class="chip-icon">{{ topic.icon }}</span>
            <span class="chip-text">{{ topic.text }}</span>
          </div>
        </div>
      </section>

      <!-- Synthesis Progress Overlay -->
      <div v-if="isLoading" class="synthesis-overlay">
        <div class="synthesis-core">
          <div class="void-loading-ring void-loading-ring--xl" aria-hidden="true"></div>
          <h3 class="synthesis-title void-text-gradient">正在分析任务链路...</h3>
          <div class="void-progress-bar">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <p class="synthesis-status">{{ loadingDescription }}{{ loadingDots }}</p>
        </div>
      </div>

      <!-- Result Section -->
      <section v-if="!isLoading && advisorResult" class="result-area animate-slide-up">
        <!-- AI Edit Panel (Crisis Mode) -->
        <div v-if="showAiEdit" class="void-card alert-box warning active">
          <div class="card-header">
            <h3><el-icon><Warning /></el-icon> 结构修正</h3>
            <el-button type="primary" size="small" class="void-btn primary" @click="rebuildFromEdit">重构</el-button>
          </div>
          <div class="card-body">
            <p class="hint-text">检测到结果结构不完整，需要人工修正后再继续。</p>
            <el-input
              v-model="aiEditContent"
              type="textarea"
              :rows="10"
              class="void-input mono"
            />
            <div v-if="aiEditError" class="error-log">{{ aiEditError }}</div>
          </div>
        </div>

        <!-- Generated Manifest -->
        <div class="manifest-card void-card">
          <header class="manifest-header">
            <div class="manifest-info">
              <h2 class="manifest-title">任务路径: {{ advisorResult.query }}</h2>
              <div class="manifest-meta">
                <span class="tag"><el-icon><Calendar /></el-icon> {{ formattedDate }}</span>
                <span class="tag" v-if="estimatedDuration"><el-icon><Timer /></el-icon> 预计用时 {{ estimatedDuration }}</span>
              </div>
            </div>
            <el-button 
              type="primary" 
              class="void-btn primary big" 
              @click="publishTask" 
              :loading="isLoading" 
              :disabled="!isValidTaskStructure"
            >
              发布到任务系统
            </el-button>
          </header>

          <div class="manifest-content">
            <div class="void-timeline">
              <div 
                v-for="(step, index) in learningSteps" 
                :key="index"
                class="timeline-item"
              >
                <div class="marker-lane">
                  <div class="marker-node">{{ index + 1 }}</div>
                  <div class="marker-line"></div>
                </div>
                <div class="content-lane">
                  <h4 class="step-title">{{ step.title }}</h4>
                  <p class="step-desc">{{ step.description }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 原始数据 (存档) -->
        <div class="raw-data-card void-card">
          <h3 class="card-title"><el-icon><Memo /></el-icon> 原始结果数据</h3>
          <div class="data-terminal">
            <pre>{{ formattedFullResponse }}</pre>
          </div>
        </div>
      </section>

      <!-- 消息 -->
      <div v-if="errorMessage" class="void-card alert-box error animate-fade-in">
        <el-icon><Warning /></el-icon>
        <span>异常: {{ errorMessage }}</span>
      </div>
      <div v-if="successMessage" class="void-card alert-box success animate-fade-in">
        <el-icon><Check /></el-icon>
        <span>完成: {{ successMessage }}</span>
      </div>
    </div>

    <!-- History Sidebar -->
    <div class="history-sidebar" :class="{ open: showHistory }">
      <header class="sidebar-header">
        <h3 class="sidebar-title">历史存档</h3>
        <div class="sidebar-btns">
          <el-button circle class="void-btn ghost" icon="Delete" @click="clearHistory" title="清除所有存档" />
          <el-button circle class="void-btn ghost" icon="Close" @click="toggleHistory" title="关闭" />
        </div>
      </header>

      <div class="sidebar-content">
        <div v-if="historyList.length === 0" class="empty-state">
          <span class="icon">📋</span>
          <p>未找到存档记录。</p>
        </div>
        
        <div 
          v-for="item in historyList" 
          :key="item.id"
          class="history-card void-card interactive"
          @click="restoreFromHistory(item)"
        >
          <header class="card-header">
            <h4 class="item-query">{{ item.query }}</h4>
            <span class="item-date">{{ new Date(item.createdAt).toLocaleDateString() }}</span>
          </header>
          <div class="card-body">
            <p class="item-preview">{{ typeof item.response === 'string' ? item.response.substring(0, 60) : JSON.stringify(item.response).substring(0, 60) }}...</p>
            <div class="item-stats">
              <span class="count">{{ item.steps.length }} 节点</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Toggle Sidebar -->
    <button class="sidebar-toggle" @click="toggleHistory">
      <span class="icon">📋</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  InfoFilled,
  Warning,
  Check,
  Calendar,
  Timer,
  Memo,
  Delete,
  Close
} from '@element-plus/icons-vue'
import { getAdvisor } from '@/api/ai'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'
import api from '@/api/index'
import { getTaskCategories } from '@/api/taskCategories'

// ==================== Reactive State ====================
const userQuery = ref('')
const isLoading = ref(false)
const progressPercent = ref(0)
const advisorResult = ref(null)
const errorMessage = ref('')
const successMessage = ref('')
const loadingDescription = ref('正在合成任务本质')
const loadingDots = ref('')
const showHistory = ref(false)

// AI raw content and editing state
const aiRawResponse = ref('')
const showAiEdit = ref(false)
const aiEditContent = ref('')
const aiEditError = ref('')

// Quick topics and categories
const quickTopics = ref([])
const isLoadingCategories = ref(false)

// History from localStorage
const historyList = ref(JSON.parse(localStorage.getItem('advisor_history')) || [])

// ==================== Animations ====================
const updateLoadingDots = () => {
  let dots = ''
  const interval = setInterval(() => {
    dots = dots.length < 3 ? dots + '.' : ''
    loadingDots.value = dots
  }, 500)
  return interval
}

// ==================== Watchers ====================
watch(aiEditContent, (newContent) => {
  if (!newContent.trim()) {
    aiEditError.value = ''
    return
  }
  
  try {
    const parsed = JSON.parse(newContent)
    if (!parsed.steps || !Array.isArray(parsed.steps)) {
      aiEditError.value = '格式无效：缺少 steps 数组'
      return
    }
    
    const invalidSteps = parsed.steps.filter(step => 
      !step || typeof step !== 'object' || !step.title || !step.description
    )
    
    if (invalidSteps.length > 0) {
      aiEditError.value = '格式无效：步骤必须包含标题和描述'
      return
    }
    
    aiEditError.value = ''
  } catch (error) {
    aiEditError.value = `语法错误: ${error.message}`
  }
})

// ==================== Lifecycle ====================
onMounted(async () => {
  try {
    isLoadingCategories.value = true
    const categories = await getTaskCategories()
    
    if (Array.isArray(categories)) {
      quickTopics.value = categories.map((cat, idx) => ({
        id: cat.category_id || idx + 1,
        text: cat.category_name,
        icon: cat.icon || '🧬',
        isPreset: cat.is_preset
      }))
    } else {
      quickTopics.value = [
        { id: 1, text: '精通 Python 数据分析', icon: '🐍' },
        { id: 2, text: '英语能力提升路径', icon: '📚' },
        { id: 3, text: 'Vue 3 系统架构', icon: '💻' },
        { id: 4, text: '健身与健康管理网格', icon: '🏃‍♂️' }
      ]
    }
  } catch (error) {
    console.error('Failed to load categories:', error)
  } finally {
    isLoadingCategories.value = false
  }
})

// ==================== Computed ====================
const learningSteps = computed(() => {
  if (!advisorResult.value || !Array.isArray(advisorResult.value.steps)) return []
  return advisorResult.value.steps.filter(step => step.title && step.description)
})

const estimatedDuration = computed(() => {
  return advisorResult.value?.estimatedDuration || ''
})

const isValidTaskStructure = computed(() => {
  const result = advisorResult.value
  if (!result || !result.query || !Array.isArray(result.steps) || result.steps.length === 0) return false
  return result.steps.every(step => step.title && step.description)
})

const formattedDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', { 
    year: 'numeric', month: 'long', day: 'numeric' 
  })
})

const formattedFullResponse = computed(() => {
  if (!advisorResult.value) return '系统空闲。等待脉冲信号...'
  return JSON.stringify(advisorResult.value, null, 2)
})

// ==================== Actions ====================

const saveToHistory = (result) => {
  const historyItem = {
    id: Date.now(),
    query: result.query,
    response: result.response,
    createdAt: new Date().toISOString(),
    steps: result.steps
  }
  
  historyList.value.unshift(historyItem)
  if (historyList.value.length > 20) historyList.value.pop()
  localStorage.setItem('advisor_history', JSON.stringify(historyList.value))
}

const parseAiResult = (result, query) => {
  aiRawResponse.value = typeof result === 'string' ? result : JSON.stringify(result, null, 2)
  
  try {
    const parsed = typeof result === 'string' ? JSON.parse(result) : result
    const cleanSteps = (parsed.steps || []).filter(s => s.title && s.description)
    
    if (cleanSteps.length > 0) {
      return {
        query,
        response: parsed.response || '路径合成成功。',
        steps: cleanSteps,
        estimatedDuration: parsed.estimatedDuration || '45d',
        createdAt: new Date()
      }
    }
    
    showAiEdit.value = true
    aiEditContent.value = aiRawResponse.value
    return fallbackSteps(query, parsed.response)
  } catch (e) {
    showAiEdit.value = true
    aiEditContent.value = aiRawResponse.value
    return fallbackSteps(query, result)
  }
}

const fallbackSteps = (query, response) => ({
  query,
  response: response || '数据流损坏。正在重新初始化...',
  steps: [
    { title: '初始化', description: '正在对齐神经路径...' },
    { title: '正在处理', description: '正在解析核心目标...' }
  ],
  estimatedDuration: '--',
  createdAt: new Date()
})

const submitQuery = async () => {
  const query = userQuery.value.trim()
  if (!query) return ElMessage.warning('需要先定义目标')
  
  errorMessage.value = ''
  successMessage.value = ''
  showAiEdit.value = false
  isLoading.value = true
  progressPercent.value = 0
  
  let progressIdx = setInterval(() => {
    if (progressPercent.value < 90) progressPercent.value += Math.random() * 10
  }, 300)
  
  const dotsIdx = updateLoadingDots()
  
  try {
    const result = await getAdvisor(query)
    clearInterval(progressIdx)
    progressPercent.value = 100
    
    advisorResult.value = parseAiResult(result, query)
    saveToHistory(advisorResult.value)
    ElMessage.success('合成已完成')
  } catch (error) {
    errorMessage.value = formatAxiosErrorMessage(error, '神经链路故障')
    ElMessage.error(errorMessage.value)
  } finally {
    setTimeout(() => {
      isLoading.value = false
      clearInterval(progressIdx)
      clearInterval(dotsIdx)
      loadingDots.value = ''
    }, 500)
  }
}

const publishTask = async () => {
  if (!isValidTaskStructure.value) return ElMessage.warning('结构不完整')
  
  isLoading.value = true
  try {
    const chainData = {
      chain_name: advisorResult.value.query.trim(),
      description: advisorResult.value.response || 'AI-generated evolution path',
      steps: advisorResult.value.steps.map(step => ({
        title: step.title,
        description: step.description,
        completion_type: 'ai_eval'
      }))
    }
    
    await api.post('/api/task-chains', chainData)
    ElMessage.success('路径已部署到意识网格')
    advisorResult.value = null
    userQuery.value = ''
  } catch (error) {
    ElMessage.error('部署失败: ' + formatAxiosErrorMessage(error, error?.message || '未知错误'))
  } finally {
    isLoading.value = false
  }
}

const useQuickTopic = (topic) => {
  userQuery.value = topic
  submitQuery()
}

const restoreFromHistory = (item) => {
  userQuery.value = item.query
  advisorResult.value = { ...item, createdAt: new Date(item.createdAt) }
  showHistory.value = false
}

const clearHistory = async () => {
  try {
    await ElMessageBox.confirm('确认清除所有神经存档？', '警告', {
      confirmButtonText: '清除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    historyList.value = []
    localStorage.removeItem('advisor_history')
    ElMessage.success('Archives cleared')
  } catch (e) {}
}

const toggleHistory = () => (showHistory.value = !showHistory.value)

const rebuildFromEdit = () => {
  try {
    const parsed = JSON.parse(aiEditContent.value)
    advisorResult.value = {
      query: advisorResult.value.query,
      ...parsed,
      createdAt: new Date()
    }
    showAiEdit.value = false
    saveToHistory(advisorResult.value)
    ElMessage.success('神经图谱已重构')
  } catch (e) {
    ElMessage.error('合成错误：请检查 JSON 格式')
  }
}
</script>

<style scoped>
.advisor-page {
  position: relative;
  min-height: 100vh;
}

.advisor-page::after {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at 10% 10%, var(--color-primary-transparent) 0%, transparent 40%);
  pointer-events: none;
  z-index: 0;
}

.advisor-page .void-content {
  position: relative;
  z-index: 1;
}

.advisor-page .page-header .logo-text {
  font-size: 3rem;
  letter-spacing: -2px;
  margin-bottom: var(--spacing-xs);
}

/* Input Box */
.selection-box {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xxl);
}

.input-group {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.input-icon {
  font-size: 2rem;
  filter: drop-shadow(0 0 10px var(--color-primary));
}

.big {
  height: 52px;
  padding: 0 var(--spacing-xl);
}

.input-hint {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* Topics */
.quick-topics {
  margin-bottom: var(--spacing-xxl);
}

.section-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: var(--spacing-lg);
}

.topics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

.topic-chip {
  padding: var(--spacing-md);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  transition: all var(--transition-normal);
}

.topic-chip:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  background: var(--bg-card-hover);
}

.chip-icon {
  font-size: 1.25rem;
}

.chip-text {
  font-weight: 600;
  color: var(--text-main);
}

/* Synthesis Overlay */
.synthesis-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-page-transparent);
  backdrop-filter: blur(20px);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.synthesis-core {
  text-align: center;
  width: 400px;
}

.synthesis-core .void-loading-ring--xl {
  margin: 0 auto var(--spacing-xl);
}

.synthesis-title {
  font-size: 1.5rem;
  margin-bottom: var(--spacing-lg);
}

.void-progress-bar {
  width: 100%;
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: var(--spacing-md);
}

.progress-fill {
  height: 100%;
  background: var(--void-gradient);
  transition: width 0.3s ease;
}

.synthesis-status {
  color: var(--text-muted);
  font-family: var(--font-family-mono);
  font-size: 0.9rem;
}

/* Results */
.manifest-card {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.manifest-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-xxl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color-light);
}

.manifest-title {
  font-size: 1.75rem;
  margin: 0 0 var(--spacing-sm) 0;
}

.manifest-meta {
  display: flex;
  gap: var(--spacing-lg);
}

.tag {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* Timeline */
.void-timeline {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  display: flex;
  gap: var(--spacing-xl);
}

.marker-lane {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.marker-node {
  width: 36px;
  height: 36px;
  background: var(--bg-page);
  border: 2px solid var(--color-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  color: var(--color-primary);
  z-index: 1;
}

.marker-line {
  flex: 1;
  width: 2px;
  background: linear-gradient(to bottom, var(--color-primary), var(--border-color-light));
  margin: var(--spacing-xs) 0;
}

.timeline-item:last-child .marker-line {
  display: none;
}

.content-lane {
  flex: 1;
  padding-bottom: var(--spacing-xxl);
}

.step-title {
  font-size: 1.25rem;
  color: var(--color-primary-light);
  margin: 0 0 var(--spacing-sm) 0;
}

.step-desc {
  color: var(--text-muted);
  line-height: 1.6;
}

/* Alert Boxes */
.alert-box {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.alert-box.warning { border-left: 4px solid var(--color-warning); }
.alert-box.error { border-left: 4px solid var(--color-error); }
.alert-box.success { border-left: 4px solid var(--color-success); }

.error-log {
  color: var(--color-error);
  font-size: 0.8rem;
  margin-top: var(--spacing-sm);
  font-family: var(--font-family-mono);
}

.hint-text {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-bottom: var(--spacing-md);
}

/* Raw Data */
.raw-data-card {
  padding: var(--spacing-lg);
}

.data-terminal {
  background: var(--bg-tertiary);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  max-height: 250px;
  overflow-y: auto;
  font-family: var(--font-family-mono);
  font-size: 0.85rem;
}

/* History Sidebar */
.history-sidebar {
  position: fixed;
  top: 0;
  right: -400px;
  width: 400px;
  height: 100vh;
  background: var(--bg-card);
  backdrop-filter: blur(40px);
  border-left: 1px solid var(--border-color);
  z-index: 2000;
  transition: right var(--transition-normal) cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
}

.history-sidebar.open {
  right: 0;
}

.sidebar-header {
  padding: var(--spacing-xl);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color-light);
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}

.history-card {
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.item-query {
  font-size: 1rem;
  margin-bottom: var(--spacing-xs);
}

.item-date {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.item-preview {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin: var(--spacing-md) 0;
}

.sidebar-toggle {
  position: fixed;
  right: var(--spacing-xl);
  bottom: var(--spacing-xl);
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--void-gradient);
  border: none;
  box-shadow: 0 0 20px var(--color-primary-transparent);
  z-index: 1500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: transform 0.3s ease;
}

.sidebar-toggle:hover {
  transform: scale(1.1) rotate(15deg);
}

@media (max-width: 768px) {
  .manifest-header {
    flex-direction: column;
    gap: var(--spacing-lg);
  }
}
</style>
