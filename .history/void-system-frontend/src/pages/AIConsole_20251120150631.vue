<template>
  <div class="void-console">
    <!-- 控制台标题 -->
    <div class="console-header">
      <h2><span class="glitch">VOID</span> <span class="system-text">SYSTEM</span> <span class="console">CONSOLE</span></h2>
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
      <!-- 装饰元素 -->
      <div class="decorative-lines">
        <div class="line-vertical"></div>
        <div class="line-horizontal"></div>
      </div>
      
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
    // 在实际应用中，这里会调用API创建新会话
    // const response = await axios.post('/api/ai/conversation/init')
    // conversationId.value = response.data.conversationId
    
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
    // 在实际应用中，这里会调用API发送消息并携带会话ID
    // const response = await axios.post(`/api/ai/conversation/${conversationId.value}/message`, {
    //   content: tempInput
    // })
    // const reply = response.data.content
    
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
.void-console {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
  position: relative;
  min-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 控制台标题 */
.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
  position: relative;
}

.console-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0.7;
}

.console-header h2 {
  font-size: 2.2rem;
  margin: 0;
  letter-spacing: 3px;
  font-family: var(--main-font);
  position: relative;
}

.glitch {
  color: var(--accent-primary);
  text-shadow: 
    0 0 10px var(--accent-primary), 
    0 0 20px var(--accent-glow),
    0 0 30px var(--accent-primary),
    0 0 40px var(--accent-glow);
  animation: glitch 3s infinite;
}

@keyframes glitch {
  0% { text-shadow: 0 0 10px var(--accent-primary); }
  5% { text-shadow: -2px 0 var(--accent-secondary), 2px 0 var(--accent-primary); }
  10% { text-shadow: 0 0 10px var(--accent-primary); }
  95% { text-shadow: 0 0 10px var(--accent-primary); }
  100% { text-shadow: 0 0 10px var(--accent-primary); }
}

.system-text {
  color: var(--text-secondary);
  text-shadow: 0 0 5px rgba(255, 255, 255, 0.1);
}

.console {
  color: var(--text-primary);
  background: linear-gradient(90deg, var(--text-primary), var(--text-secondary));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  color: var(--text-secondary);
  background: rgba(10, 13, 32, 0.6);
  backdrop-filter: var(--blur-sm);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  font-family: var(--main-font);
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: var(--accent-primary);
  box-shadow: 0 0 10px var(--accent-glow);
  position: relative;
}

.status-dot::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  background: inherit;
  border-radius: inherit;
  animation: pulse 2s infinite;
}

.status-dot.online {
  background-color: var(--success-color);
  box-shadow: 0 0 10px var(--success-color);
}

.status-dot.loading {
  background-color: var(--accent-primary);
  box-shadow: 0 0 10px var(--accent-glow);
  animation: pulse 1s infinite;
}

/* 会话信息 */
.conversation-info {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: rgba(10, 13, 32, 0.8);
  backdrop-filter: var(--blur-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  color: var(--text-secondary);
  position: relative;
  overflow: hidden;
  margin-bottom: 0;
}

.conversation-info::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
  opacity: 0.5;
}

.conv-id, .token-count {
  font-family: 'Courier New', monospace;
  position: relative;
  z-index: 1;
}

.token-count {
  color: var(--accent-primary);
  font-weight: 600;
  text-shadow: 0 0 5px var(--accent-glow);
}

/* 系统和错误消息样式 */
.system-message .message-text {
  background: rgba(0, 204, 255, 0.1);
  border-left: 3px solid var(--accent-primary);
}

.message.isError .message-text {
  background: rgba(255, 68, 68, 0.1);
  border-left: 3px solid #ff4444;
  color: #ff6666;
}

/* 聊天容器 */
.chat-container {
  position: relative;
  background: linear-gradient(135deg, rgba(45, 64, 184, 0.1), rgba(122, 131, 189, 0.05));
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 
    0 0 40px rgba(0, 204, 255, 0.15),
    inset 0 0 10px rgba(0, 204, 255, 0.05);
  overflow: hidden;
  backdrop-filter: blur(10px);
  animation: containerGlow 3s ease-in-out infinite alternate;
}

@keyframes containerGlow {
  0% { box-shadow: 0 0 30px rgba(0, 204, 255, 0.1); }
  100% { box-shadow: 0 0 40px rgba(0, 204, 255, 0.2); }
}

/* 装饰线条 */
.decorative-lines {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.line-vertical {
  position: absolute;
  left: 60px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(to bottom, transparent, var(--border-color), transparent);
  opacity: 0.3;
}

.line-horizontal {
  position: absolute;
  top: 40px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(to right, transparent, var(--border-color), transparent);
  opacity: 0.3;
}

/* 消息容器 */
.messages-container {
  height: 500px;
  overflow-y: auto;
  margin-bottom: 1.5rem;
  padding-right: 0.5rem;
  scrollbar-width: thin;
  scrollbar-color: var(--accent-secondary) transparent;
  scroll-behavior: smooth;
}

.messages-container::-webkit-scrollbar {
  width: 8px;
}

.messages-container::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: var(--accent-secondary);
  border-radius: 4px;
  transition: background 0.3s ease;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: var(--accent-primary);
  box-shadow: 0 0 10px var(--accent-glow);
}

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: var(--accent-secondary);
}

/* 欢迎消息 */
.welcome-message {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--text-secondary);
}

.system-icon {
  font-size: 3rem;
  color: var(--accent-primary);
  margin-bottom: 1rem;
  animation: float 3s ease-in-out infinite;
}

.welcome-message p {
  margin: 0.5rem 0;
  font-size: 1.2rem;
  /* 修改为高对比度文本颜色，确保在深色背景上的可读性 */
  color: rgba(255, 255, 255, 0.9);
}

.welcome-message .subtitle {
  font-size: 1rem;
  opacity: 0.8;
}

/* 消息样式 */
.message {
  margin-bottom: 1.5rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary));
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  max-width: calc(100% - 60px);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
}

.role-label {
  font-weight: 600;
  font-family: var(--main-font);
}

.user-message .role-label {
  /* 修改为高对比度文本颜色，确保在深色背景上的可读性 */
  color: rgba(255, 255, 255, 0.8);
}

.system-message .role-label {
  color: var(--accent-primary);
  text-shadow: 0 0 5px var(--accent-glow);
}

.timestamp {
  color: var(--text-secondary);
  opacity: 0.7;
}

.message-text {
  background: rgba(10, 13, 32, 0.9);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.2rem;
  line-height: 1.6;
  position: relative;
  overflow: hidden;
  /* 修改为高对比度文本颜色，确保在深色背景上的可读性 */
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
  transition: all 0.3s ease;
}

.message-text:hover {
  background: rgba(10, 13, 32, 1);
  border-color: var(--accent-primary);
  box-shadow: 0 4px 15px rgba(0, 204, 255, 0.1);
  transform: translateY(-2px);
}

.message-text::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(to right, transparent, var(--accent-primary), transparent);
  opacity: 0.5;
}

/* 用户消息特殊样式 */
.user-message .message-text {
  border-left: 3px solid var(--accent-primary);
}

/* 系统消息特殊样式 */
.system-message .message-text {
  border-left: 3px solid var(--accent-secondary);
}

/* 加载指示器 */
.loading-indicator {
  display: flex;
  justify-content: center;
  padding: 1rem 0;
  animation: fadeIn 0.5s ease-out;
}

.loading-dots {
  display: flex;
  gap: 8px;
}

.loading-dots span {
  width: 10px;
  height: 10px;
  background-color: var(--accent-primary);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--accent-glow);
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
    transform: scale(0);
    opacity: 0.5;
  } 
  40% { 
    transform: scale(1);
    opacity: 1;
    box-shadow: 0 0 15px var(--accent-primary);
  }
}

/* 输入容器 */
.input-container {
  display: flex;
  gap: 1rem;
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
  left: 15px;
  color: var(--accent-primary);
  font-size: 1.2rem;
  z-index: 1;
  pointer-events: none;
}

.input-wrapper :deep(.el-input__wrapper) {
  background: rgba(5, 7, 20, 0.8);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5);
  transition: all var(--transition-fast) ease;
}

.input-wrapper :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary);
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5), 0 0 10px var(--accent-glow);
}

.input-wrapper :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5), 0 0 15px var(--accent-primary);
}

.input-wrapper :deep(.el-input__inner) {
    background: transparent;
    border: none;
    color: var(--text-primary);
    font-family: var(--body-font);
    padding-left: 35px;
    /* 确保在深色背景上的高对比度 */
    color: rgba(255, 255, 255, 0.9);
  }

.input-container :deep(.el-button) {
  min-width: 80px;
  background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary));
  border: none;
  color: var(--bg-primary);
  font-weight: 600;
}

.input-container :deep(.el-button:hover:not(:disabled)) {
  box-shadow: 0 0 20px var(--accent-primary);
  transform: translateY(-1px);
}

.input-container :deep(.el-button.is-disabled) {
  opacity: 0.5;
}

/* 底部信息 */
.console-footer {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.connection-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--text-secondary);
  opacity: 0.7;
}
</style>
