<template>
  <div class="qa-container">
    <!-- 页面标题 -->
    <div class="qa-header">
      <h2><span class="main-text">📖 知识</span> <span class="system-text">问答系统</span></h2>
      <p class="subtitle">虚空智能分析，助您获取精准专业知识</p>
    </div>
    
    <!-- 输入区域 -->
    <div class="input-section">
      <div class="input-wrapper">
        <div class="input-prefix">❓</div>
        <el-input 
          v-model="question" 
          placeholder="请输入您的问题，例如：如何提高学习效率？"
          @keyup.enter="ask"
          :disabled="isLoading"
          clearable
        />
      </div>
      <el-button 
        type="primary" 
        @click="ask"
        :loading="isLoading"
        :disabled="isLoading || !question.trim()"
      >
        <span v-if="!isLoading">提问</span>
        <span v-else>检索中...</span>
      </el-button>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-section">
      <div class="loading-animation">
        <div class="loading-ring"></div>
        <p>正在智能分析您的问题...</p>
      </div>
    </div>
    
    <!-- 答案展示 -->
    <div v-else-if="answer" class="answer-section fade-in">
      <div class="answer-header">
        <h3>📚 检索结果</h3>
        <div class="timestamp">{{ formatTime(new Date()) }}</div>
      </div>
      
      <div class="answer-content">
        <pre>{{ answer }}</pre>
      </div>
      
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
import { ref } from "vue"
import { askQA } from "@/api/ai"

const question = ref("")
const answer = ref("")
const isLoading = ref(false)

async function ask() {
  if (!question.value.trim()) return
  
  isLoading.value = true
  try {
    answer.value = await askQA(question.value)
  } catch (error) {
    console.error('提问失败:', error)
    answer.value = '抱歉，检索过程中出现错误，请稍后再试。'
  } finally {
    isLoading.value = false
  }
}

function clearAnswer() {
  answer.value = ''
  question.value = ''
}

function askNewQuestion() {
  question.value = ''
  // 聚焦输入框
  setTimeout(() => {
    const input = document.querySelector('.el-input__inner')
    if (input) input.focus()
  }, 100)
}

function formatTime(date) {
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

/* 输入区域 */
.input-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  align-items: center;
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg-tertiary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

.input-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
}

.input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 0 1rem;
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
}

.input-wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 15px rgba(67, 97, 238, 0.2);
  transform: translateY(-1px);
}

.input-prefix {
  font-size: 1.2rem;
  margin-right: 0.75rem;
  color: var(--color-primary);
  animation: pulse 2s ease-in-out infinite;
}

.input-wrapper .el-input {
    flex: 1;
    --el-input-bg-color: transparent;
    /* 确保在深色背景上的高对比度 */
    --el-input-text-color: var(--color-text-primary);
    --el-input-placeholder-color: var(--color-text-secondary);
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

.answer-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, var(--color-primary), transparent);
}

.answer-header h3 {
  margin: 0;
  font-size: 1.3rem;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-weight: 600;
}

.timestamp {
  color: var(--color-text-secondary);
  font-size: 0.8rem;
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border-light);
}

.answer-content {
  margin-bottom: 1.5rem;
  background: linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  border-left: 4px solid var(--color-primary);
  box-shadow: var(--shadow-sm);
  position: relative;
}

.answer-content::before {
  content: '';
  position: absolute;
  top: -1px;
  left: -1px;
  right: -1px;
  height: 1px;
  background: linear-gradient(90deg, var(--color-primary), transparent);
}

.answer-content pre {
  margin: 0;
  color: var(--color-text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  font-family: var(--body-font);
  font-size: 1rem;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 2rem;
}

.action-btn {
  transition: all 0.3s ease;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
  animation: float 3s ease-in-out infinite;
}

.empty-state p {
  margin: 0.5rem 0;
  font-size: 1.2rem;
  color: var(--text-primary);
}

.empty-subtitle {
  font-size: 1rem;
  opacity: 0.7;
  color: var(--text-secondary);
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
  
  .input-section {
    flex-direction: column;
  }
  
  .input-wrapper {
    width: 100%;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>
