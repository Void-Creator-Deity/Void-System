<template>
  <div class="qa-container">
    <!-- 页面标题 -->
    <div class="qa-header">
      <h2><span>📖 系统问答</span></h2>
      <p class="subtitle">通过系统知识库获取精准信息</p>
    </div>
    
    <div class="search-options">
      <div class="search-mode-selector">
        <el-radio-group v-model="searchMode" size="small" class="cyber-radio">
          <el-radio-button label="vector">基础模式</el-radio-button>
          <el-radio-button label="hybrid">混合模式</el-radio-button>
        </el-radio-group>
      </div>
      
      <div class="input-section">
        <div class="input-wrapper">
          <div class="input-prefix">❓</div>
          <el-input 
            v-model="question" 
            placeholder="请输入您的问题... (Shift + Enter 换行)"
            @keyup.enter.native="handleEnter"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            :disabled="isLoading"
          />
        </div>
        <el-button 
          class="cyber-button"
          type="primary" 
          @click="ask"
          :loading="isLoading"
          :disabled="isLoading || !question.trim()"
        >
          <span v-if="!isLoading">开始提问</span>
          <span v-else>分析中...</span>
        </el-button>
      </div>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-section">
      <div class="loading-animation">
        <div class="loading-ring"></div>
        <p>正在搜索并分析您的问题...</p>
      </div>
    </div>
    
    <!-- 答案展示 -->
    <div v-else-if="answer" class="answer-section fade-in">
      <div class="answer-header">
        <h3>📚 检索结果</h3>
        <div class="timestamp">{{ formatTime(new Date()) }}</div>
      </div>
      
      <div class="answer-content markdown-body" v-html="renderMarkdown(answer)"></div>
      
      <div class="action-buttons">
        <el-button type="info" @click="clearAnswer" class="action-btn">
          🔄 清空结果
        </el-button>
        <el-button type="success" @click="askNewQuestion" class="action-btn">
          💬 继续提问
        </el-button>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="empty-state">
      <div class="empty-icon">❓</div>
      <p>准备就绪</p>
      <p class="empty-subtitle">输入问题开始知识库检索</p>
    </div>
  </div>
</template>

<script setup>
/**
 * QA Component - Knowledge Base Q&A
 * ----------------------------------
 * 知识库问答页面，基于 RAG 技术提供智能问答功能
 */

import { ref, nextTick } from "vue"
import { ElMessage } from "element-plus"
import { askQA } from "@/api/ai"
import { marked } from 'marked'

// ==================== 响应式状态 ====================
const question = ref("")
const answer = ref("")
const isLoading = ref(false)
const searchMode = ref("vector") // vector, hybrid

// ==================== 业务逻辑 ====================

/**
 * 处理 Enter 键 (防抖 + Shift Enter 支持)
 */
const handleEnter = (e) => {
  if (!e.shiftKey) {
    e.preventDefault()
    ask()
  }
}

/**
 * 提问并获取答案
 */
const ask = async () => {
  if (!question.value.trim()) {
    return
  }
  
  isLoading.value = true
  try {
    const result = await askQA(question.value.trim(), { 
      mode: searchMode.value 
    })
    answer.value = result
    ElMessage.success('检索完成')
  } catch (error) {
    console.error('提问失败:', error)
    const errorMessage = error.response?.data?.detail || 
                        error.message || 
                        '检索过程中出现错误，请稍后再试'
    answer.value = `抱歉，${errorMessage}`
    ElMessage.error('检索失败，请稍后重试')
  } finally {
    isLoading.value = false
  }
}

/**
 * 清空答案和问题
 */
const clearAnswer = () => {
  answer.value = ''
  question.value = ''
}

/**
 * 渲染 Markdown 内容
 */
const renderMarkdown = (text) => {
  if (!text) return ''
  return marked.parse(text)
}

/**
 * 准备新问题（清空当前问题并聚焦输入框）
 */
const askNewQuestion = async () => {
  question.value = ''
  answer.value = ''
  
  // 等待 DOM 更新后聚焦输入框
  await nextTick()
  const input = document.querySelector('.el-input__inner')
  if (input) {
    input.focus()
  }
}

/**
 * 格式化时间
 * @param {Date} date - 日期对象
 * @returns {string} 格式化后的时间字符串
 */
const formatTime = (date) => {
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<style scoped>
.qa-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
  position: relative;
}

.qa-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: -20%;
  right: -20%;
  height: 200px;
  background: radial-gradient(circle at center, rgba(67, 97, 238, 0.1) 0%, transparent 70%);
  z-index: -1;
}

.qa-header {
  text-align: center;
  margin-bottom: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border-light);
  position: relative;
}

.qa-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 25%;
  right: 25%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
}

.qa-header h2 {
  font-size: 2.5rem;
  margin: 0 0 1rem 0;
  font-family: var(--main-font);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.main-text {
  background: linear-gradient(90deg, var(--color-text-primary), var(--color-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 700;
  position: relative;
}

.main-text::after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, var(--color-primary), transparent);
  opacity: 0.7;
}

.system-text {
  color: var(--color-text-primary);
  font-weight: 600;
}

.subtitle {
  color: var(--color-text-secondary);
  font-size: 1.1rem;
  margin: 0;
  background: linear-gradient(90deg, var(--color-text-primary), var(--color-text-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 搜索选项 */
.search-options {
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.search-mode-selector {
  display: flex;
  justify-content: center;
}

.cyber-radio :deep(.el-radio-button__inner) {
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  border-color: var(--color-border-light);
  font-weight: 600;
  letter-spacing: 1px;
}

.cyber-radio :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--grad-cyber);
  border-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
}

/* 输入区域 */
.input-section {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-md);
  position: relative;
}

.cyber-button {
  height: 54px;
  padding: 0 25px;
  font-weight: 700;
  letter-spacing: 1px;
  background: var(--grad-cyber);
  border: none;
  box-shadow: var(--shadow-glow);
}

.input-wrapper {
  flex: 1;
  display: flex;
  align-items: flex-start;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  transition: all var(--transition-normal);
}

.input-wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-cyber);
}

.input-prefix {
  font-size: 1.2rem;
  margin-right: 0.75rem;
  margin-top: 4px;
}

.input-wrapper :deep(.el-textarea__inner) {
  background: transparent;
  border: none;
  color: var(--color-text-primary);
  font-size: 1rem;
  padding: 0;
  box-shadow: none !important;
}

/* 加载状态 */
.loading-section {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 3rem;
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

.loading-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
}

.loading-animation {
  text-align: center;
}

.loading-ring {
  width: 70px;
  height: 70px;
  border: 4px solid var(--color-border-light);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  margin: 0 auto 1rem;
  animation: spin 1s linear infinite;
  box-shadow: 0 0 20px rgba(67, 97, 238, 0.3);
  position: relative;
}

.loading-ring::before {
  content: '';
  position: absolute;
  top: -4px;
  left: -4px;
  right: -4px;
  bottom: -4px;
  border: 4px solid transparent;
  border-top-color: var(--color-secondary);
  border-radius: 50%;
  opacity: 0.7;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  to { 
    transform: rotate(360deg); 
    box-shadow: 0 0 25px rgba(67, 97, 238, 0.5);
  }
}

/* 答案展示 */
.answer-section {
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 2rem;
  box-shadow: 
    var(--shadow-md),
    inset 0 0 10px rgba(67, 97, 238, 0.05);
  backdrop-filter: blur(10px);
  animation: containerGlow 3s ease-in-out infinite alternate;
  position: relative;
  overflow: hidden;
}

.answer-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
}

@keyframes containerGlow {
  0% { box-shadow: var(--shadow-md), 0 0 30px rgba(67, 97, 238, 0.1); }
  100% { box-shadow: var(--shadow-md), 0 0 40px rgba(67, 97, 238, 0.2); }
}

.answer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border-light);
  position: relative;
}

.answer-content {
  margin-bottom: 1.5rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 2rem;
  border-left: 4px solid var(--color-primary);
  box-shadow: var(--shadow-sm);
}

/* Markdown 样式 */
.markdown-body {
  color: var(--color-text-primary);
  line-height: 1.7;
}

.markdown-body :deep(h1), 
.markdown-body :deep(h2), 
.markdown-body :deep(h3) {
  color: var(--color-primary-light);
  margin-top: 1.5em;
  margin-bottom: 1em;
  font-weight: 700;
}

.markdown-body :deep(p) {
  margin-bottom: 1em;
}

.markdown-body :deep(ul), 
.markdown-body :deep(ol) {
  padding-left: 2em;
  margin-bottom: 1em;
}

.markdown-body :deep(code) {
  background: var(--color-bg-tertiary);
  padding: 0.2em 0.4em;
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
  font-size: 0.9em;
  color: var(--color-accent);
}

.markdown-body :deep(pre) {
  background: var(--color-bg-secondary);
  padding: 1.5em;
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin-bottom: 1em;
  border: 1px solid var(--color-border);
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: var(--color-text-primary);
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid var(--color-border-cyber);
  padding-left: 1em;
  color: var(--color-text-secondary);
  font-style: italic;
  margin: 1em 0;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 2rem;
}

.action-btn {
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.action-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left var(--transition-normal);
}

.action-btn:hover::before {
  left: 100%;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-btn:active {
  transform: translateY(0);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

.empty-state::before {
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
  margin-bottom: 1rem;
  opacity: 0.8;
  animation: float 3s ease-in-out infinite;
  color: var(--color-primary);
}

.empty-state p {
  margin: 0.5rem 0;
  font-size: 1.2rem;
  color: var(--color-text-primary);
  background: linear-gradient(90deg, var(--color-text-primary), var(--color-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 600;
}

.empty-subtitle {
  font-size: 1rem;
  opacity: 0.9;
  color: var(--color-text-secondary);
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border-light);
  display: inline-block;
  margin-top: 0.5rem;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-in {
  animation: fade-in 0.6s ease-out;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .qa-container {
    padding: 1rem;
  }
  
  .qa-header h2 {
    font-size: 2rem;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .input-section {
    flex-direction: column;
    gap: 1rem;
  }
  
  .input-wrapper {
    width: 100%;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .answer-header {
    flex-direction: column;
    gap: 0.75rem;
    align-items: flex-start;
  }
}
</style>
