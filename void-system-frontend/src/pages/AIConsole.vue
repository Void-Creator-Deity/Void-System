<template>
  <div class="ai-console-layout">
    <!-- 左侧会话侧边栏 -->
    <aside class="console-sidebar card-glass" :class="{ 'collapsed': isSidebarCollapsed }">
      <div class="sidebar-header">
        <h3 v-if="!isSidebarCollapsed">量子指令集</h3>
        <el-button circle size="small" @click="isSidebarCollapsed = !isSidebarCollapsed">
          <el-icon><Fold v-if="!isSidebarCollapsed"/><Expand v-else/></el-icon>
        </el-button>
      </div>

      <div class="sidebar-actions" v-if="!isSidebarCollapsed">
        <el-button type="primary" class="new-btn" @click="createNewSession">
          <el-icon><Plus /></el-icon> 开启新对话
        </el-button>
        <el-button type="info" plain class="new-group-btn" @click="createNewGroup">
          <el-icon><FolderAdd /></el-icon> 新建组
        </el-button>
      </div>

      <div class="groups-list" v-if="!isSidebarCollapsed">
        <div v-for="group in chatStore.groups" :key="group.group_id" class="group-item">
          <div class="group-title" @click="toggleGroup(group.group_id)">
            <el-icon><Collection /></el-icon>
            <span>{{ group.group_name }}</span>
            <el-dropdown @command="(cmd) => handleGroupCommand(cmd, group)">
              <el-icon class="more-icon"><MoreFilled /></el-icon>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">重命名</el-dropdown-item>
                  <el-dropdown-item command="delete" dir="rtl">删除组</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          
          <div class="session-items-box">
              <div 
                v-for="session in group.sessions" 
                :key="session.session_id"
                class="session-link"
                :class="{ 'active': chatStore.activeSessionId === session.session_id }"
                @click="switchSession(group.group_id, session.session_id)"
                draggable="true"
                @dragstart="e => e.dataTransfer.setData('sessionId', session.session_id)"
              >
              <el-icon class="session-icon"><ChatLineRound /></el-icon>
              <span class="session-name">{{ session.session_name }}</span>
              <el-dropdown trigger="click" @command="(cmd) => handleSessionCommand(cmd, group.group_id, session)">
                <el-icon class="session-more"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="rename"><el-icon><EditPen /></el-icon>重命名</el-dropdown-item>
                    <el-dropdown-item command="duplicate"><el-icon><DocumentCopy /></el-icon>拷贝对话</el-dropdown-item>
                    <el-dropdown-item v-if="chatStore.groups.length > 1" command="move"><el-icon><Rank /></el-icon>移动到组</el-dropdown-item>
                    <el-dropdown-item command="delete" dir="rtl"><el-icon><Delete /></el-icon>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧主对话区 -->
    <main class="console-main">
      <div class="console-header">
        <div class="header-info">
          <div class="active-path">
            <span class="path-group">{{ currentGroup?.group_name }}</span>
            <el-icon><ArrowRight /></el-icon>
            <span class="path-session">{{ currentSession?.session_name }}</span>
          </div>
          <div class="status-indicator">
            <div class="status-dot" :class="{ 'online': !isLoading, 'loading': isLoading }"></div>
            <span>{{ isLoading ? '正在同步虚空指令...' : '虚空链路正常' }}</span>
          </div>
        </div>
      </div>

      <!-- 聊天内容 -->
      <div class="messages-viewport" ref="viewport">
        <div v-if="!messages?.length" class="empty-state">
          <div class="void-logo">V</div>
          <h3>虚空系统 · 指令控制台</h3>
          <p>请输入指令以开始。支持文件注入、跨会话引用与自动历史留档。</p>
          <div class="quick-starts">
            <div class="q-chip" @click="sendQuick('分析我目前的进化进度')">进度分析</div>
            <div class="q-chip" @click="sendQuick('生成下一阶段任务建议')">任务建议</div>
            <div class="q-chip" @click="sendQuick('系统性能自检')">系统自检</div>
          </div>
        </div>

        <div 
          v-for="(msg, idx) in messages" 
          :key="msg.id"
          :id="'msg-' + msg.id"
          class="message-wrapper"
          :class="[msg.role]"
        >
          <!-- 消息引用预览 -->
          <div v-if="msg.replyToId" class="reply-context" @click="navigateToMessage(msg.replyToId)">
            <el-icon><ChatDotSquare /></el-icon>
            <span>{{ msg.reply_content?.substring(0, 40) }}...</span>
          </div>

          <div class="bubble-container">
            <div class="avatar-cell">
              <div class="avatar" :class="msg.role">
                {{ msg.role === 'user' ? 'U' : 'V' }}
              </div>
            </div>
            
            <div class="bubble-content card-glass">
              <div class="bubble-header">
                <span class="role-tag">{{ msg.role === 'user' ? 'ME' : 'VOID_SYSTEM' }}</span>
                <div class="bubble-actions">
                  <el-button link size="small" @click="quoteMessage(msg)"><el-icon><ChatDotSquare /></el-icon></el-button>
                  <el-button link size="small" @click="copyToClipboard(msg.text)"><el-icon><CopyDocument /></el-icon></el-button>
                </div>
              </div>
              
              <div class="text-area">
                <div v-if="msg.role === 'system'" v-html="renderMarkdown(msg.text)" class="markdown-body"></div>
                <div v-else class="text-raw">{{ msg.text }}</div>
              </div>

              <div class="bubble-footer">
                <span class="time">{{ formatTime(msg.timestamp) }}</span>
                <span v-if="msg.tokens" class="tokens">[{{ msg.tokens }} TKS]</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="isLoading && !isStreamingMsg" class="message-wrapper system">
          <div class="bubble-container">
            <div class="avatar-cell"><div class="avatar system">V</div></div>
            <div class="bubble-content card-glass">
              <div class="typing"><span></span><span></span><span></span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <footer class="input-container">
        <!-- 引用提示栏 -->
        <div v-if="replyingMessage" class="reply-bar">
          <div class="reply-info">
            <el-icon><ChatDotSquare /></el-icon>
            引用: {{ replyingMessage.text.substring(0, 50) }}...
          </div>
          <el-icon class="close-reply" @click="replyingMessage = null"><Close /></el-icon>
        </div>

        <div class="input-panel card-glass">
          <div class="panel-left">
            <el-tooltip content="注入本地文件" placement="top">
              <div class="panel-icon" @click="fileInputRef?.click()">
                <el-icon><Link /></el-icon>
              </div>
            </el-tooltip>
            <input ref="fileInputRef" type="file" hidden @change="handleFileUpload" />
          </div>
          
          <el-input
            v-model="input"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 8 }"
            placeholder="在此键入指令... (Shift+Enter 换行, Enter 发送)"
            resize="none"
            class="main-textarea"
            @keydown.enter.prevent="handleKeyEnter"
            :disabled="isLoading"
          />

          <div class="panel-right">
            <el-button 
              v-if="!isLoading"
              type="primary" 
              circle 
              class="glow-btn"
              @click="handleSend"
              :disabled="!input.trim()"
            >
              <el-icon><Promotion /></el-icon>
            </el-button>
            <el-button 
              v-else
              type="danger" 
              circle 
              class="stop-btn"
              @click="stopGeneration"
            >
              <el-icon><VideoPause /></el-icon>
            </el-button>
          </div>
        </div>
      </footer>
    </main>

    <!-- 移动会话对话框 -->
    <el-dialog
      v-model="moveDialog.show"
      title="转移虚空会话"
      width="300px"
      custom-class="void-dialog"
      append-to-body
    >
      <div class="move-dialog-body">
        <p class="dialog-tip">选择目标任务组：</p>
        <el-radio-group v-model="moveDialog.targetGroupId" class="move-radio-group">
          <el-radio 
            v-for="g in moveDialog.otherGroups" 
            :key="g.group_id" 
            :label="g.group_id"
            border
          >
            <el-icon><Collection /></el-icon> {{ g.group_name }}
          </el-radio>
        </el-radio-group>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="moveDialog.show = false">取消</el-button>
          <el-button type="primary" :disabled="!moveDialog.targetGroupId" @click="executeMove">
            确认转移
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, reactive } from 'vue'
import { useChatStore } from '@/stores/chat'
import { 
  Fold, Expand, Plus, FolderAdd, Collection, MoreFilled, 
  ChatLineRound, Close, ArrowRight, Delete, DocumentCopy,
  ChatDotSquare, CopyDocument, Promotion, Link, EditPen, Rank, VideoPause
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import { ElMessage, ElMessageBox } from 'element-plus'
import { streamPersona } from "@/api/ai"
import { sessionApi } from "@/api/session"

const chatStore = useChatStore()
const isSidebarCollapsed = ref(false)
const input = ref('')
const isLoading = ref(false)
const viewport = ref(null)
const fileInputRef = ref(null)
const replyingMessage = ref(null)
const abortController = ref(null)

const moveDialog = reactive({
  show: false,
  sessionId: '',
  targetGroupId: '',
  otherGroups: []
})

// 当前状态
const currentGroup = computed(() => chatStore.activeGroup)
const currentSession = computed(() => chatStore.activeSession)
const messages = computed(() => chatStore.messages)
const isStreamingMsg = computed(() => {
  if (!messages.value.length) return false
  const last = messages.value[messages.value.length - 1]
  return last.role === 'system' && isLoading.value
})

// --- 动作 ---

const switchSession = (gid, sid) => {
  chatStore.switchGroup(gid)
  chatStore.switchSession(sid)
}

const createNewSession = () => {
  chatStore.createSession()
}

const createNewGroup = () => {
  chatStore.createGroup()
}

const handleGroupCommand = (cmd, group) => {
  if (cmd === 'rename') {
    ElMessageBox.prompt('请输入分组新名称', '重命名组', {
      inputValue: group.group_name,
      confirmButtonText: '保存',
      cancelButtonText: '取消'
    }).then(({ value }) => {
      if (value) chatStore.renameGroup(group.group_id, value)
    })
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(`确定删除组 "${group.group_name}" 及其所有会话吗？`, '警告', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    }).then(() => chatStore.deleteGroup(group.group_id))
  }
}

const handleSessionCommand = (cmd, gid, session) => {
  if (cmd === 'rename') {
    ElMessageBox.prompt('请输入对话新名称', '重命名对话', {
      inputValue: session.session_name,
      confirmButtonText: '保存',
      cancelButtonText: '取消'
    }).then(({ value }) => {
      if (value) chatStore.renameSession(session.session_id, value)
    })
  } else if (cmd === 'delete') {
    chatStore.deleteSession(session.session_id)
  } else if (cmd === 'duplicate') {
    chatStore.duplicateSession(session.session_id)
      .then(() => ElMessage.success('会话已克隆并自动切换'))
  } else if (cmd === 'move') {
    const otherGroups = chatStore.groups.filter(g => g.group_id !== gid)
    if (!otherGroups.length) {
      ElMessage.warning('暂无其他任务组可供转移')
      return
    }
    moveDialog.sessionId = session.session_id
    moveDialog.otherGroups = otherGroups
    moveDialog.targetGroupId = otherGroups[0].group_id
    moveDialog.show = true
  }
}

const executeMove = () => {
  if (!moveDialog.sessionId || !moveDialog.targetGroupId) return
  chatStore.moveSession(moveDialog.sessionId, moveDialog.targetGroupId)
    .then(() => {
      ElMessage.success('虚空会话已跨组转移')
      moveDialog.show = false
    })
}

const toggleGroup = (id) => {
  // 可以在此处实现收起/展开组的逻辑，如果需要的话。
}

const navigateToMessage = (mid) => {
  const el = document.getElementById('msg-' + mid)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('highlight-flash')
    setTimeout(() => el.classList.remove('highlight-flash'), 2000)
  } else {
    ElMessage.warning('引用的消息不在当前视图中')
  }
}

const confirmClear = () => {
  ElMessageBox.confirm('一键格式化当前会话历史？', '系统警告', {
    type: 'warning'
  }).then(() => chatStore.clearActiveSession())
}

const stopGeneration = () => {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
    isLoading.value = false
    ElMessage.info('指令已强行中断')
  }
}

const quoteMessage = (msg) => {
  replyingMessage.value = msg
}

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}

const copyFullSession = () => {
  const content = messages.value.map(m => `[${m.role.toUpperCase()}] ${m.text}`).join('\n\n')
  copyToClipboard(content)
}

const handleKeyEnter = (e) => {
  if (e.shiftKey) return
  handleSend()
}

const sendQuick = (txt) => {
  input.value = txt
  handleSend()
}

const handleSend = async () => {
  const text = input.value.trim()
  if (!text || isLoading.value) return

  const userMsg = {
    role: 'user',
    text: text,
    replyTo: replyingMessage.value ? { id: replyingMessage.value.id, text: replyingMessage.value.text } : null
  }

  input.value = ''
  replyingMessage.value = null
  chatStore.addMessage(userMsg)
  
  isLoading.value = true
  
  // 占位响应（不立即保存到数据库，等流结束后统一保存）
  chatStore.addMessage({ role: 'system', text: '', tokens: 0 }, false)
  scrollToBottom()

  try {
    let acc = ""
    abortController.value = new AbortController()
    
    streamPersona(text, chatStore.activeSessionId, (content, done) => {
      if (done) {
        chatStore.saveLastMessage(acc, Math.floor(acc.length / 3))
        isLoading.value = false
        abortController.value = null
      } else {
        acc += content
        // 临时更新UI展示
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'system') lastMsg.text = acc
        scrollToBottom()
      }
    }, (err) => {
      // 如果是手动取消，不报错
      if (err.name === 'AbortError') return
      
      isLoading.value = false
      abortController.value = null
      ElMessage.error('虚空链路中断: ' + (err.message || '未知错误'))
    }, abortController.value.signal)
  } catch (e) {
    isLoading.value = false
    ElMessage.error('指令发送失败')
  }
}

const handleFileUpload = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  
  isLoading.value = true
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    const res = await sessionApi.uploadTemporaryFile(chatStore.activeSessionId, formData)
    if (res.data.success) {
      chatStore.addMessage({
        role: "system",
        text: `### 📁 外部数据注入成功\n---\n- **名称**: \`${file.name}\`\n- **大小**: \`${(file.size/1024).toFixed(1)} KB\`\n\n数据已解析并进入虚空缓存，现在可以针对此文件进行提问。`
      })
      ElMessage.success('注入成功')
    }
  } catch (err) {
    ElMessage.error('注入失败')
  } finally {
    isLoading.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

// --- 工具 ---

const renderMarkdown = (text) => marked.parse(text || '')
const formatTime = (ts) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const scrollToBottom = () => {
  nextTick(() => {
    if (viewport.value) {
      viewport.value.scrollTop = viewport.value.scrollHeight
    }
  })
}

watch(messages, () => scrollToBottom(), { deep: true })
onMounted(() => {
  chatStore.initStore()
  scrollToBottom()
})

</script>

<style scoped>
.ai-console-layout {
  display: flex;
  height: calc(100vh - 100px);
  gap: 1.5rem;
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* 侧边栏 */
.console-sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-glass);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: width 0.3s ease;
  overflow: hidden;
}

.console-sidebar.collapsed { width: 60px; }

.sidebar-header {
  padding: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--color-border-light);
}

.sidebar-header h3 {
  font-size: 1.1rem;
  color: var(--color-primary-light);
  margin: 0;
}

.sidebar-actions {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.new-btn { width: 100%; font-weight: 700; box-shadow: var(--shadow-glow); }
.new-group-btn { width: 100%; }

.groups-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.group-item { margin-bottom: 1.5rem; }

.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  letter-spacing: 0.5px;
}
.group-title .el-icon:first-child { 
  width: 20px; 
  display: flex; 
  justify-content: center; 
  font-size: 15px; 
  opacity: 0.7; 
}

.group-title:hover { color: var(--color-text-primary); }
.more-icon { margin-left: auto; cursor: pointer; padding: 4px; border-radius: 4px; }
.more-icon:hover { background: rgba(255,255,255,0.1); }

.session-items-box { padding-left: 1.5rem; margin-top: 4px; }

.session-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin: 1px 0;
  border-radius: 6px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.85rem;
}
.session-icon { 
  width: 20px; 
  display: flex; 
  justify-content: center; 
  font-size: 15px; 
  flex-shrink: 0; 
}

.session-link:hover { background: rgba(255,255,255,0.05); color: var(--color-text-primary); }
.session-link.active { background: rgba(99, 102, 241, 0.15); color: var(--color-primary-light); border-right: 3px solid var(--color-primary); }

.session-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-more { opacity: 0; font-size: 14px; transition: opacity 0.2s; padding: 4px; }
.session-link:hover .session-more { opacity: 0.6; }
.session-more:hover { opacity: 1 !important; color: var(--color-primary-light); }

/* 主对话区 */
.console-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-glass);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.console-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.active-path { display: flex; align-items: center; gap: 8px; font-size: 0.9rem; }
.path-group { color: var(--color-text-muted); }
.path-session { color: var(--color-text-primary); font-weight: 700; }

.status-indicator { display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--color-text-muted); margin-top: 4px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #444; }
.status-dot.online { background: var(--color-success); box-shadow: 0 0 8px var(--color-success); }
.status-dot.loading { background: var(--color-primary); animation: pulse 1s infinite; }

@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* 消息区 */
.messages-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.empty-state {
  margin: auto;
  text-align: center;
  max-width: 500px;
}

.void-logo {
  width: 60px; height: 60px; background: var(--grad-cyber); color: #fff;
  border-radius: 12px; display: flex; align-items: center; justify-content: center;
  font-size: 2rem; font-weight: 900; margin: 0 auto 1.5rem; animation: rotateLogo 10s linear infinite;
}

@keyframes rotateLogo { 0% {transform: rotateY(0)} 100% {transform: rotateY(360deg)} }

.quick-starts { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 2rem; }
.q-chip { padding: 6px 14px; background: rgba(255,255,255,0.03); border: 1px solid var(--color-border); border-radius: 20px; font-size: 0.85rem; cursor: pointer; transition: 0.2s; }
.q-chip:hover { border-color: var(--color-primary); color: var(--color-primary-light); background: rgba(99,102,241,0.1); }

.message-wrapper { display: flex; flex-direction: column; width: 100%; transition: opacity 0.3s; }
.message-wrapper.user { align-items: flex-end; }
.message-wrapper.system { align-items: flex-start; }

.reply-context {
  margin-bottom: 4px; padding: 4px 12px; background: rgba(255,255,255,0.05);
  border-left: 2px solid var(--color-primary); border-radius: 4px;
  font-size: 0.75rem; color: var(--color-text-muted); display: flex; align-items: center; gap: 6px;
  max-width: 300px;
}

.bubble-container { display: flex; gap: 12px; max-width: 85%; }
.user .bubble-container { flex-direction: row-reverse; }

.avatar {
  width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-weight: 900; font-size: 0.9rem;
}
.avatar.user { background: var(--color-primary); color: #fff; }
.avatar.system { background: var(--color-bg-tertiary); border: 1px solid var(--color-border); color: var(--color-primary); }

.bubble-content {
  padding: 12px 16px; border-radius: 12px; position: relative;
  background: rgba(30, 41, 59, 0.4); border: 1px solid var(--color-border-light);
}

.user .bubble-content { background: var(--color-primary-dark); border-color: rgba(99, 102, 241, 0.3); }

.bubble-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.role-tag { font-size: 10px; font-weight: 800; letter-spacing: 1px; color: var(--color-text-muted); }
.bubble-actions { opacity: 0; transition: 0.2s; display: flex; gap: 4px; }
.bubble-content:hover .bubble-actions { opacity: 1; }

.text-area { font-size: 0.95rem; line-height: 1.6; word-wrap: break-word; }
.bubble-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px; font-size: 0.7rem; color: var(--color-text-muted); }

/* 输入栏 */
.input-container { padding: 0 1.5rem 1.5rem; }

.reply-bar {
  background: rgba(99, 102, 241, 0.1); border: 1px solid var(--color-primary);
  border-bottom: none; border-radius: 8px 8px 0 0; padding: 8px 12px;
  display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem;
}
.close-reply { cursor: pointer; color: var(--color-accent); }

.input-panel {
  display: flex; align-items: flex-end; padding: 6px 12px; gap: 10px;
  background: rgba(15, 23, 42, 0.6); border: 1px solid var(--color-border); border-radius: var(--radius-md);
}

.panel-icon { cursor: pointer; padding: 8px; color: var(--color-text-muted); transition: 0.2s; }
.panel-icon:hover { color: var(--color-primary-light); transform: scale(1.1); }

.main-textarea :deep(.el-textarea__inner) {
  background: transparent; border: none; box-shadow: none; color: #fff; padding: 8px 0;
}

.glow-btn {
  width: 44px; height: 44px; background: var(--grad-cyber) !important; border: none !important;
  box-shadow: 0 0 15px rgba(99,102,241,0.3); transition: 0.3s;
}
.glow-btn:hover { transform: scale(1.05); box-shadow: 0 0 25px rgba(99,102,241,0.5); }

.stop-btn {
  width: 44px; height: 44px; background: rgba(239, 68, 68, 0.2) !important; border: 1px solid #ef4444 !important;
  color: #ef4444 !important; transition: 0.3s;
}
.stop-btn:hover { background: rgba(239, 68, 68, 0.3) !important; transform: scale(1.05); }

/* 移动对话框样式 */
.move-radio-group { display: flex; flex-direction: column; gap: 10px; width: 100%; }
.move-radio-group :deep(.el-radio) { margin-right: 0; width: 100%; height: auto; padding: 12px; display: flex; align-items: center; border: 1px solid rgba(255,255,255,0.05); background: rgba(255,255,255,0.02); }
.move-radio-group :deep(.el-radio.is-bordered.is-checked) { border-color: var(--color-primary); background: rgba(99,102,241,0.1); }
.dialog-tip { font-size: 13px; color: var(--color-text-secondary); margin-bottom: 15px; }

/* Markdown */
.markdown-body :deep(h1,h2,h3) { margin: 10px 0; color: var(--color-primary-light); }
.markdown-body :deep(pre) { background: rgba(0,0,0,0.4); padding: 12px; border-radius: 8px; margin: 8px 0; }
.markdown-body :deep(code) { font-family: var(--font-family-mono); background: rgba(255,255,255,0.1); padding: 2px 4px; border-radius: 4px; }

/* Typing */
.typing { display: flex; gap: 4px; margin: 4px 0; }
.typing span { width: 6px; height: 6px; background: var(--color-primary); border-radius: 50%; animation: typAnim 1s infinite alternate; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typAnim { from {opacity: 0.3} to {opacity: 1} }

.highlight-flash {
  animation: flashBg 2s ease;
}

@keyframes flashBg {
  0% { background: rgba(99, 102, 241, 0.3); }
  100% { background: transparent; }
}

/* 滚动条 */
.messages-viewport::-webkit-scrollbar { width: 6px; }
.messages-viewport::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
</style>