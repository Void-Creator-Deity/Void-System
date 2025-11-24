<template>
  <div class="qa-container">
    <!-- 页面标题 -->
    <div class="qa-header">
      <h2><span class="glitch">知识</span> <span class="system-text">问答</span></h2>
      <p class="subtitle">向系统提问，获取知识库中的相关信息</p>
    </div>
    
    <!-- 输入区域 -->
    <div class="input-section">
      <div class="input-wrapper">
        <div class="input-prefix">❓</div>
        <el-input 
          v-model="question" 
          placeholder="输入您的问题，例如：什么是机器学习？"
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
        <p>正在从知识库检索相关信息...</p>
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
}

.qa-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.qa-header h2 {
  font-size: 2rem;
  margin: 0 0 1rem 0;
  font-family: var(--main-font);
}

.glitch {
  color: var(--accent-primary);
  text-shadow: 0 0 10px var(--accent-glow);
}

.system-text {
  color: var(--text-secondary);
}

.subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
  margin: 0;
}

/* 输入区域 */
.input-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  align-items: center;
}

.input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(10, 13, 32, 0.7);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0 1rem;
  transition: all 0.3s ease;
}

.input-wrapper:focus-within {
  border-color: var(--accent-primary);
  box-shadow: 0 0 15px var(--accent-glow);
}

.input-prefix {
  font-size: 1.2rem;
  margin-right: 0.75rem;
  color: var(--accent-primary);
}

.input-wrapper .el-input {
    flex: 1;
    --el-input-bg-color: transparent;
    /* 确保在深色背景上的高对比度 */
    --el-input-text-color: rgba(255, 255, 255, 0.9);
    --el-input-placeholder-color: var(--text-secondary);
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

/* 答案展示 */
.answer-section {
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

.answer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.answer-header h3 {
  margin: 0;
  font-size: 1.3rem;
  color: var(--text-primary);
}

.timestamp {
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.answer-content {
  margin-bottom: 1.5rem;
  background: rgba(10, 13, 32, 0.9);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1.5rem;
  border-left: 4px solid var(--accent-primary);
}

.answer-content pre {
  margin: 0;
  /* 修改为高对比度文本颜色，确保在深色背景上的可读性 */
  color: rgba(255, 255, 255, 0.9);
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
