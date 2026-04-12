<template>
  <div class="void-page-container qa-page">
    <div class="void-content">
      <header class="page-header">
        <h1 class="logo-text"><span class="void-text-gradient">虚空</span> 知识库</h1>
        <p class="subtitle">通过虚空知识库进行神经检索。精准、合成。</p>
      </header>

      <!-- Search Area -->
      <section class="selection-box void-card animate-float">
        <div class="mode-selector">
          <el-radio-group v-model="searchMode" size="small" class="void-radio-group">
            <el-radio-button label="vector">向量路径 (Vector)</el-radio-button>
            <el-radio-button label="hybrid">混合脉冲 (Hybrid)</el-radio-button>
          </el-radio-group>
        </div>

        <div class="input-group">
          <div class="input-icon">🔍</div>
          <el-input 
            v-model="question" 
            placeholder="输入神经查询... (Shift + Enter 换行)"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 6 }"
            class="void-input"
            @keydown.enter="handleEnter"
            :disabled="isLoading"
          />
          <el-button 
            type="primary" 
            @click="ask"
            class="void-btn primary big"
            :loading="isLoading"
            :disabled="isLoading || !question.trim()"
          >
            {{ isLoading ? '检索中' : '询问虚空' }}
          </el-button>
        </div>
      </section>

      <!-- Synthesis State -->
      <div v-if="isLoading" class="loading-state animate-fade-in">
        <div class="synthesis-core">
          <div class="core-ring"></div>
          <p class="status-msg">正在扫描多维索引...</p>
        </div>
      </div>

      <!-- Result Area -->
      <div v-else-if="answer" class="result-area animate-slide-up">
        <div class="answer-card void-card">
          <header class="card-header">
            <div class="header-info">
              <h3><el-icon><Reading /></el-icon> 检索到的知识</h3>
              <span class="timestamp">{{ formatTime(new Date()) }}</span>
            </div>
            <div class="header-actions">
              <el-button circle class="void-btn ghost" icon="Refresh" @click="clearAnswer" title="清空" />
            </div>
          </header>

          <div class="card-body">
            <div class="markdown-body void-markdown" v-html="renderMarkdown(answer)"></div>
          </div>

          <footer class="card-footer">
            <el-button type="info" plain @click="clearAnswer" class="void-btn ghost">清空终端</el-button>
            <el-button type="primary" @click="askNewQuestion" class="void-btn primary">重置上下文</el-button>
          </footer>
        </div>
      </div>

      <!-- Idle State -->
      <div v-else class="empty-state animate-fade-in">
        <div class="void-card subtle-placeholder">
          <div class="icon">🔮</div>
          <h3>系统就绪</h3>
          <p>等待神经输入以进行知识检索。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from "vue"
import { ElMessage } from "element-plus"
import { 
  Reading, 
  Refresh, 
  Search,
  ChatDotRound
} from "@element-plus/icons-vue"
import { askQA } from "@/api/ai"
import { getUserInfo } from "@/api/user"
import { marked } from 'marked'

// ==================== State ====================
const question = ref("")
const answer = ref("")
const isLoading = ref(false)
const searchMode = ref("vector")

// ==================== Logic ====================

const handleEnter = (e) => {
  if (!e.shiftKey) {
    e.preventDefault()
    ask()
  }
}

const ask = async () => {
  if (!question.value.trim()) return
  
  isLoading.value = true
  try {
    const userInfo = getUserInfo()
    const userId = userInfo?.user_id || userInfo?.user?.user_id
    const result = await askQA(question.value.trim(), { 
      mode: searchMode.value,
      userId: userId
    })
    answer.value = result
    ElMessage.success('神经链路已建立')
  } catch (error) {
    const errorDetail = error.response?.data?.detail || error.message || '接口错误'
    answer.value = `### [系统异常]\n\n神经检索失败: ${errorDetail}`
     ElMessage.error('检索失败')
  } finally {
    isLoading.value = false
  }
}

const clearAnswer = () => {
  answer.value = ''
  question.value = ''
}

const renderMarkdown = (text) => {
  if (!text) return ''
  return marked.parse(text)
}

const askNewQuestion = async () => {
  question.value = ''
  answer.value = ''
  await nextTick()
  const input = document.querySelector('.el-textarea__inner')
  input?.focus()
}

</script>

<style scoped>
.qa-page {
  background: var(--bg-page);
  min-height: 100vh;
}

.void-content {
  padding: var(--spacing-xxl) 0;
}

.page-header {
  margin-bottom: var(--spacing-xxl);
}

.subtitle {
  color: var(--text-muted);
  font-size: 1.1rem;
}

/* Search Area */
.selection-box {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xxl);
}

.mode-selector {
  display: flex;
  justify-content: center;
  margin-bottom: var(--spacing-md);
}

.input-group {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-end;
}

.input-icon {
  font-size: 1.5rem;
  margin-bottom: var(--spacing-xs);
  filter: drop-shadow(0 0 5px var(--color-primary-transparent));
}

.big {
  height: 52px;
  padding: 0 var(--spacing-xl);
}

/* Synthesis State */
.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: var(--spacing-xxl);
  min-height: 200px;
}

.synthesis-core {
  text-align: center;
}

.core-ring {
  width: 60px;
  height: 60px;
  border: 4px solid var(--border-color);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  margin: 0 auto var(--spacing-lg);
  animation: voidSpin 1s linear infinite;
}

.status-msg {
  color: var(--text-muted);
  font-family: var(--font-family-mono);
  font-size: 0.9rem;
}

/* Result Area */
.answer-card {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xxl);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 2px solid var(--border-color-light);
}

.header-info h3 {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin: 0;
}

.timestamp {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-family-mono);
}

.card-body {
  margin-bottom: var(--spacing-xl);
}

.void-markdown {
  background: var(--bg-tertiary);
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-primary);
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--border-color-light);
}

/* Empty State */
.empty-state {
  padding: var(--spacing-xxl) 0;
  text-align: center;
}

.subtle-placeholder {
  display: inline-block;
  padding: var(--spacing-xxl);
  max-width: 400px;
  background: var(--bg-card);
}

.subtle-placeholder .icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-md);
  opacity: 0.5;
}

.subtle-placeholder h3 {
  margin-bottom: var(--spacing-sm);
  color: var(--text-main);
}

.subtle-placeholder p {
  color: var(--text-muted);
}

@keyframes voidSpin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .input-group {
    flex-direction: column;
    align-items: stretch;
  }
  
  .card-footer {
    flex-direction: column;
  }
}
</style>
