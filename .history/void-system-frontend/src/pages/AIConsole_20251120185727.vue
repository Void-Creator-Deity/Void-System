<template>
  <div class="ai-console">
    <!-- 控制台标题 -->
    <div class="console-header">
      <h2>AI 命令控制台</h2>
      <div class="status-indicator">
        <div class="status-dot" :class="{ 'online': !isLoading && messages.length > 0, 'loading': isLoading }"></div>
        <span>{{ isLoading ? '连接中...' : (messages.length > 0 ? '在线' : '离线') }}</span>
      </div>
    </div>
    
    <!-- 会话信息 -->
    <div v-if="conversationId" class="conversation-info">
      <span class="conv-id">会话ID: {{ conversationId }}</span>
      <span class="token-count">使用令牌: {{ totalTokens }}</span>
    </div>
    
    <!-- 聊天面板 -->
    <div class="chat-container">
      <!-- 消息区域 -->
      <div class="messages-container" ref="messagesContainer">
        <div v-if="messages.length === 0" class="welcome-message">
          <div class="system-icon">⟩</div>
          <p>虚空系统已启动</p>
          <p class="subtitle">你好，我是系统精灵。有什么可以帮助你的？</p>
        </div>
        
        <div v-for="(msg, idx) in messages" :key="idx" 
             :class="['message', msg.role, idx === messages.length - 1 ? 'fade-in' : '']">
          
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="user-message">
            <div class="message-avatar">👤</div>
            <div class="message-content">
              <div class="message-header">
                <span class="role-label">用户</span>
                <span class="timestamp">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <div class="message-text">{{ msg.text }}</div>
            </div>
          </div>
          
          <!-- 系统消息 -->
          <div v-else class="system-message">
            <div class="message-avatar">⚡</div>
            <div class="message-content">
              <div class="message-header">
                <span class="role-label">系统精灵</span>
                <span class="timestamp">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <div class="message-text">{{ msg.text }}</div>
            </div>
          </div>
        </div>
        
        <!-- 加载动画 -->
        <div v-if="isLoading" class="loading-indicator">
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
      
      <!-- 输入区域 -->
      <div class="input-container">
        <div class="input-wrapper">
          <div class="input-prefix">⟩</div>
          <el-input
            v-model="input"
            placeholder="输入指令..."
            @keyup.enter="send"
            :disabled="isLoading"
          />
        </div>
        <el-button @click="send" :loading="isLoading" :disabled="isLoading || !input.trim()">
          发送
        </el-button>
      </div>
    </div>
    
    <!-- 底部状态信息 -->
    <div class="console-footer">
      <div class="connection-info">
        <span class="connection-status">连接状态: 稳定</span>
        <span class="version">版本: v1.0.0</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from "vue"
import { ElMessage } from "element-plus"
import { askPersona } from "@/api/ai"

const input = ref("")
const messages = ref([])
const isLoading = ref(true)
const messagesContainer = ref(null)
const conversationId = ref('')
const totalTokens = ref(0)

// 自动滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 监听消息变化，自动滚动
watch(messages, scrollToBottom, { flush: 'post' })

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

// 初始化会话
const initializeConversation = async () => {
  try {
    isLoading.value = true
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    conversationId.value = 'conv_' + Date.now()
    
    console.log('会话初始化成功:', conversationId.value)
  } catch (error) {
    console.error('会话初始化失败:', error)
    ElMessage.error('系统连接失败，请稍后再试')
  } finally {
    isLoading.value = false
  }
}

// 发送消息
async function send() {
  if (!input.value.trim() || isLoading.value) return
  
  // 添加用户消息
  const userMessage = {
    role: "user",
    text: input.value,
    timestamp: new Date().toISOString()
  }
  messages.value.push(userMessage)
  
  const tempInput = input.value
  input.value = ""
  isLoading.value = true
  
  try {
    // 获取系统回复
    const reply = await askPersona(tempInput)
    
    // 计算token数量（示例计算方式）
    const tokens = Math.floor(reply.length / 4)
    totalTokens.value += tokens
    
    // 添加系统消息
    const systemMessage = {
      role: "system",
      text: reply,
      timestamp: new Date().toISOString(),
      tokens: tokens
    }
    messages.value.push(systemMessage)
    
    ElMessage.success('消息发送成功')
  } catch (error) {
    console.error('发送消息失败:', error)
    ElMessage.error('消息发送失败，请检查网络连接')
    messages.value.push({
      role: "system",
      text: "[系统错误] 消息发送失败，请稍后重试。",
      timestamp: new Date().toISOString(),
      isError: true
    })
  } finally {
    isLoading.value = false
  }
}

// 组件挂载时初始化
onMounted(() => {
  console.log('AI控制台初始化中...')
  initializeConversation()
})
</script>

<style scoped>
/* 控制台主容器 */
.ai-console {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: var(--spacing-xl);
  min-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

/* 控制台标题 */
.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
}

.console-header h2 {
  font-size: 1.75rem;
  margin: 0;
  color: var(--color-primary);
  font-weight: 600;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  background: var(--color-bg-tertiary);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--color-text-muted);
}

.status-dot.online {
  background-color: var(--color-success);
}

.status-dot.loading {
  background-color: var(--color-primary);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 会话信息 */
.conversation-info {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.conv-id, .token-count {
  font-family: 'Courier New', monospace;
}

.token-count {
  color: var(--color-primary);
  font-weight: 500;
}

/* 系统和错误消息样式 */
.system-message .message-text {
  background: var(--color-bg-tertiary);
  border-left: 3px solid var(--color-primary);
}

.message.isError .message-text {
  background: rgba(231, 76, 60, 0.05);
  border-left: 3px solid var(--color-error);
  color: var(--color-error);
}

/* 聊天容器 */
.chat-container {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-sm);
  flex: 1;
  min-height: 600px;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

/* 消息容器 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding-right: var(--spacing-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
}

.messages-container::-webkit-scrollbar-thumb {
  background: var(--color-border-dark);
  border-radius: var(--radius-full);
  transition: background-color var(--transition-fast);
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-muted);
}

/* 欢迎消息 */
.welcome-message {
  text-align: center;
  padding: var(--spacing-2xl);
  color: var(--color-text-secondary);
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  margin: var(--spacing-xl) auto;
  max-width: 80%;
}

.system-icon {
  font-size: 3rem;
  color: var(--color-primary);
  margin-bottom: var(--spacing-lg);
}

.welcome-message p {
  margin: var(--spacing-sm) 0;
  font-size: 1.25rem;
  color: var(--color-text-primary);
  font-weight: 500;
}

.welcome-message .subtitle {
  font-size: 1rem;
  color: var(--color-text-secondary);
  max-width: 600px;
  margin: 0 auto;
}

/* 消息样式 */
.message {
  margin-bottom: var(--spacing-xl);
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  flex-shrink: 0;
  transition: all var(--transition-fast);
}

.message:hover .message-avatar {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: var(--color-primary);
}

.message-content {
  flex: 1;
  max-width: calc(100% - 60px);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xs);
  font-size: 0.875rem;
  padding: 0 var(--spacing-xs);
}

.role-label {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.75rem;
}

.user-message .role-label {
  color: var(--color-text-primary);
}

.system-message .role-label {
  color: var(--color-primary);
}

.timestamp {
  color: var(--color-text-muted);
  font-size: 0.75rem;
}

.message-text {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  line-height: 1.6;
  color: var(--color-text-primary);
  font-weight: 400;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.message:hover .message-text {
  background: var(--color-bg-primary);
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

/* 用户消息特殊样式 */
.user-message .message-text {
  border-left: 3px solid var(--color-primary);
}

/* 系统消息特殊样式 */
.system-message .message-text {
  border-left: 3px solid var(--color-primary-light);
  background: var(--color-bg-secondary);
}

/* 加载指示器 */
.loading-indicator {
  display: flex;
  justify-content: center;
  padding: var(--spacing-lg) 0;
  animation: fadeIn 0.3s ease-out;
}

.loading-dots {
  display: flex;
  gap: 8px;
}

.loading-dots span {
  width: 10px;
  height: 10px;
  background-color: var(--color-primary);
  border-radius: 50%;
  animation: loading 1.4s ease-in-out infinite both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes loading {
  0%, 80%, 100% { 
    transform: scale(0.8);
    opacity: 0.6;
  } 
  40% { 
    transform: scale(1);
    opacity: 1;
  }
}

/* 输入容器 */
.input-container {
  display: flex;
  gap: var(--spacing-md);
  align-items: stretch;
}

.input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.input-prefix {
  position: absolute;
  left: 18px;
  color: var(--color-primary);
  font-size: 1.25rem;
  z-index: 1;
  pointer-events: none;
  font-family: 'Courier New', monospace;
}

.input-wrapper :deep(.el-input__wrapper) {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: none;
  transition: all var(--transition-fast);
}

.input-wrapper :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
}

.input-wrapper :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.2);
}

.input-wrapper :deep(.el-input__inner) {
  background: transparent;
  border: none;
  color: var(--color-text-primary);
  font-family: inherit;
  padding-left: 40px;
  font-size: 1rem;
}

.input-container :deep(.el-button) {
  min-width: 90px;
  background: var(--color-primary);
  border: none;
  color: white;
  font-weight: 500;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.input-container :deep(.el-button:hover:not(:disabled)) {
  background: var(--color-primary-dark);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.input-container :deep(.el-button.is-disabled) {
  opacity: 0.6;
  transform: none;
}

/* 底部信息 */
.console-footer {
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.connection-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  background: var(--color-bg-tertiary);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  gap: var(--spacing-xl);
  flex: 1;
}

.connection-status {
  color: var(--color-primary);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.connection-status::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .ai-console {
    padding: var(--spacing-md);
  }
  
  .console-header {
    flex-direction: column;
    gap: var(--spacing-md);
    text-align: center;
  }
  
  .console-header h2 {
    font-size: 1.5rem;
  }
  
  .chat-container {
    padding: var(--spacing-md);
    min-height: 500px;
  }
  
  .welcome-message {
    padding: var(--spacing-lg);
    max-width: 100%;
  }
  
  .system-icon {
    font-size: 2.5rem;
  }
  
  .connection-info {
    flex-direction: column;
    gap: var(--spacing-sm);
    text-align: center;
  }
  
  .message-content {
    max-width: calc(100% - 50px);
  }
  
  .message-avatar {
    width: 35px;
    height: 35px;
    font-size: 1.125rem;
  }
}
</style>
