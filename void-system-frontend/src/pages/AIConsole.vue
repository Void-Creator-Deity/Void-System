<template>
  <div class="chat-workspace">
    <button v-if="mobileConversationsOpen" class="chat-backdrop" type="button" aria-label="关闭会话列表" @click="mobileConversationsOpen = false"></button>

    <aside class="chat-rail" :class="{ 'chat-rail--open': mobileConversationsOpen }" aria-label="对话列表">
      <div class="chat-rail__header">
        <div><p class="eyebrow">AI 助手</p><h1>对话</h1></div>
        <el-button class="chat-rail__close" text circle aria-label="关闭会话列表" @click="mobileConversationsOpen = false"><el-icon><Close /></el-icon></el-button>
      </div>
      <div class="chat-rail__actions">
        <el-button type="primary" @click="createNewSession"><el-icon><Plus /></el-icon>新对话</el-button>
        <el-button plain aria-label="新建分组" @click="createNewGroup"><el-icon><FolderAdd /></el-icon></el-button>
      </div>
      <div class="conversation-groups">
        <section v-for="group in chatStore.groups" :key="group.group_id" class="conversation-group">
          <div class="conversation-group__heading">
            <div><el-icon><Collection /></el-icon><span>{{ group.group_name }}</span></div>
            <el-dropdown trigger="click" @command="command => handleGroupCommand(command, group)">
              <el-button text circle size="small" aria-label="管理分组" @click.stop><el-icon><MoreFilled /></el-icon></el-button>
              <template #dropdown><el-dropdown-menu>
                <el-dropdown-item command="rename"><el-icon><EditPen /></el-icon>重命名</el-dropdown-item>
                <el-dropdown-item command="delete" divided><el-icon><Delete /></el-icon>删除分组</el-dropdown-item>
              </el-dropdown-menu></template>
            </el-dropdown>
          </div>
          <div v-for="session in group.sessions" :key="session.session_id" class="conversation-session" :class="{ 'conversation-session--active': chatStore.activeSessionId === session.session_id }">
            <button type="button" class="conversation-session__select" @click="selectSession(group.group_id, session.session_id)">
              <el-icon><ChatLineRound /></el-icon><span>{{ session.session_name }}</span>
            </button>
            <el-dropdown trigger="click" @command="command => handleSessionCommand(command, group, session)">
              <el-button text circle size="small" aria-label="管理对话"><el-icon><MoreFilled /></el-icon></el-button>
              <template #dropdown><el-dropdown-menu>
                <el-dropdown-item command="rename"><el-icon><EditPen /></el-icon>重命名</el-dropdown-item>
                <el-dropdown-item command="duplicate"><el-icon><DocumentCopy /></el-icon>复制对话</el-dropdown-item>
                <el-dropdown-item v-if="chatStore.groups.length > 1" command="move"><el-icon><Rank /></el-icon>移动到分组</el-dropdown-item>
                <el-dropdown-item command="delete" divided><el-icon><Delete /></el-icon>删除对话</el-dropdown-item>
              </el-dropdown-menu></template>
            </el-dropdown>
          </div>
        </section>
      </div>
      <div class="chat-rail__footer"><span>{{ chatStore.groups.length }} 个分组</span><span>{{ sessionCount }} 个对话</span></div>
    </aside>

    <main class="chat-main">
      <header class="chat-topbar">
        <div class="chat-topbar__context">
          <el-button class="chat-topbar__menu" text circle aria-label="打开会话列表" @click="mobileConversationsOpen = true"><el-icon><Menu /></el-icon></el-button>
          <div><p>{{ currentGroup?.group_name || '个人助手' }}</p><h2>{{ currentSession?.session_name || '新对话' }}</h2></div>
        </div>
        <div class="chat-topbar__tools">
          <span class="chat-status" :class="{ 'chat-status--busy': isGenerating }"><i></i>{{ isGenerating ? '正在生成' : '可开始对话' }}</span>
          <el-tooltip content="复制当前对话"><el-button text circle aria-label="复制当前对话" :disabled="!messages.length" @click="copyFullSession"><el-icon><CopyDocument /></el-icon></el-button></el-tooltip>
          <el-tooltip content="清空当前对话"><el-button text circle aria-label="清空当前对话" :disabled="!messages.length || isGenerating" @click="confirmClear"><el-icon><Delete /></el-icon></el-button></el-tooltip>
        </div>
      </header>

      <div v-if="chatStore.lastError" class="chat-error" role="alert"><el-icon><WarningFilled /></el-icon><span>{{ chatStore.lastError }}</span><el-button text circle aria-label="关闭错误提示" @click="chatStore.clearError()"><el-icon><Close /></el-icon></el-button></div>

      <section ref="viewport" class="messages-viewport" aria-live="polite">
        <div class="messages-thread">
          <div v-if="!messages.length && !isGenerating" class="conversation-empty">
            <div class="conversation-empty__mark"><el-icon><MagicStick /></el-icon></div>
            <p class="eyebrow">个人工作区</p><h3>从眼前的事开始</h3><p>整理优先级、梳理资料，或把一个模糊的想法推进成下一步。</p>
            <div class="prompt-list"><button type="button" @click="sendQuick('帮我梳理今天最重要的三件事')">梳理今天的优先级</button><button type="button" @click="sendQuick('分析我当前行动的推进情况')">看看行动进度</button><button type="button" @click="sendQuick('把这个目标拆成可执行的下一步')">拆解一个目标</button></div>
          </div>

          <article v-for="message in messages" :key="message.id" :id="'msg-' + message.id" class="chat-message" :class="message.role === 'user' ? 'chat-message--user' : 'chat-message--assistant'">
            <div class="chat-message__avatar"><el-icon v-if="message.role === 'user'"><UserFilled /></el-icon><el-icon v-else><MagicStick /></el-icon></div>
            <div class="chat-message__body">
              <button v-if="message.replyToId" type="button" class="message-reference" @click="navigateToMessage(message.replyToId)"><el-icon><ChatDotSquare /></el-icon><span>引用：{{ messagePreview(message.reply_content, 48) }}</span></button>
              <div class="chat-message__meta"><strong>{{ message.role === 'user' ? '你' : 'AI 助手' }}</strong><span>{{ formatTime(message.timestamp) }}</span><div><el-tooltip content="引用"><el-button text circle size="small" aria-label="引用消息" @click="quoteMessage(message)"><el-icon><ChatDotSquare /></el-icon></el-button></el-tooltip><el-tooltip content="复制"><el-button text circle size="small" aria-label="复制消息" @click="copyToClipboard(message.text)"><el-icon><CopyDocument /></el-icon></el-button></el-tooltip></div></div>
              <div class="chat-message__content"><div v-if="message.role !== 'user' && message.text" class="markdown-body" v-html="renderMarkdown(message.text)"></div><div v-else-if="message.role !== 'user' && isGenerating && message === messages.at(-1)" class="typing" aria-label="AI is generating"><i></i><i></i><i></i></div><div v-else-if="message.role === 'user'" class="chat-message__plain">{{ message.text }}</div></div>
              <small v-if="message.tokens">约 {{ message.tokens }} 字符</small>
            </div>
          </article>
        </div>
      </section>

      <footer class="composer-area"><div class="composer-thread">
        <div v-if="replyingMessage" class="composer-reference"><div><el-icon><ChatDotSquare /></el-icon><span>正在引用：{{ messagePreview(replyingMessage.text, 70) }}</span></div><el-button text circle size="small" aria-label="取消引用" @click="replyingMessage = null"><el-icon><Close /></el-icon></el-button></div>
        <div v-if="composerAttachments.length" class="composer-files"><div v-for="attachment in composerAttachments" :key="attachment.localId" class="composer-file" :class="{ 'composer-file--error': attachment.error }"><img v-if="attachment.previewUrl" :src="attachment.previewUrl" alt="" /><el-icon v-else><Document /></el-icon><span :title="attachment.fileName">{{ attachment.fileName }}</span><i v-if="attachment.uploading" class="upload-spinner"></i><small v-else-if="attachment.error">上传失败</small><el-button text circle size="small" aria-label="移除附件" @click="removeComposerAttachment(attachment)"><el-icon><Close /></el-icon></el-button></div></div>
        <div class="composer-box" :class="{ 'composer-box--focused': composerFocused }"><el-tooltip content="添加附件"><el-button text circle aria-label="添加附件" @click="fileInputRef?.click()"><el-icon><Paperclip /></el-icon></el-button></el-tooltip><input ref="fileInputRef" type="file" hidden @change="handleFileUpload" /><el-input v-model="input" class="composer-box__input" type="textarea" resize="none" :autosize="{ minRows: 1, maxRows: 6 }" :placeholder="inputPlaceholder" :disabled="isGenerating" @focus="composerFocused = true" @blur="composerFocused = false" @keydown.enter.prevent="handleKeyEnter" /><el-tooltip :content="isGenerating ? '停止生成' : '发送'"><el-button v-if="!isGenerating" type="primary" circle aria-label="发送" :disabled="!canSendMessage" @click="handleSend"><el-icon><Promotion /></el-icon></el-button><el-button v-else type="danger" circle aria-label="停止生成" @click="stopGeneration"><el-icon><VideoPause /></el-icon></el-button></el-tooltip></div>
      </div></footer>
    </main>

    <el-dialog v-model="moveDialog.show" title="移动到分组" width="min(92vw, 400px)" append-to-body><el-radio-group v-model="moveDialog.targetGroupId" class="move-group-list"><el-radio v-for="group in moveDialog.otherGroups" :key="group.group_id" :label="group.group_id" border>{{ group.group_name }}</el-radio></el-radio-group><template #footer><el-button @click="moveDialog.show = false">取消</el-button><el-button type="primary" :disabled="!moveDialog.targetGroupId" @click="executeMove">移动</el-button></template></el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ChatDotSquare, ChatLineRound, Close, Collection, CopyDocument, Delete, Document, DocumentCopy, EditPen, FolderAdd, MagicStick, Menu, MoreFilled, Paperclip, Plus, Promotion, Rank, UserFilled, VideoPause, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { streamPersona } from '@/api/ai'
import { getApiErrorMessage } from '@/api'
import { sessionApi } from '@/api/session'
import { useChatStore } from '@/stores/chat'
import { renderAssistantMarkdown } from '@/utils/markdownThink'

const chatStore = useChatStore()
const input = ref('')
const viewport = ref(null)
const fileInputRef = ref(null)
const replyingMessage = ref(null)
const composerAttachments = ref([])
const abortController = ref(null)
const isGenerating = ref(false)
const composerFocused = ref(false)
const mobileConversationsOpen = ref(false)
let attachmentSequence = 0
const moveDialog = reactive({ show: false, sessionId: '', targetGroupId: '', otherGroups: [] })
const currentGroup = computed(() => chatStore.activeGroup)
const currentSession = computed(() => chatStore.activeSession)
const messages = computed(() => chatStore.messages)
const sessionCount = computed(() => chatStore.groups.reduce((total, group) => total + (group.sessions?.length || 0), 0))
const readyAttachments = computed(() => composerAttachments.value.filter(item => item.fileId && !item.uploading && !item.error))
const canSendMessage = computed(() => !isGenerating.value && Boolean(input.value.trim() || readyAttachments.value.length))
const inputPlaceholder = computed(() => readyAttachments.value.length ? '补充说明（可选）' : '输入问题或想法')

function messagePreview(text, limit = 48) { const value = String(text || '').replace(/\s+/g, ' ').trim(); return value.length > limit ? value.slice(0, limit) + '…' : value || '这条消息' }
function renderMarkdown(text) { return renderAssistantMarkdown(text || '') }
function formatTime(timestamp) { const date = new Date(timestamp); return timestamp && !Number.isNaN(date.getTime()) ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '' }
function scrollToBottom() { nextTick(() => { if (viewport.value) viewport.value.scrollTop = viewport.value.scrollHeight }) }
function clearComposerAttachments() { composerAttachments.value.forEach(item => { if (item.previewUrl) URL.revokeObjectURL(item.previewUrl) }); composerAttachments.value = [] }
async function disposeComposerAttachments() { const attachments = [...composerAttachments.value]; clearComposerAttachments(); await Promise.allSettled(attachments.filter(item => item.fileId).map(item => sessionApi.deleteTemporaryFile(item.fileId))) }

async function selectSession(groupId, sessionId) { if (isGenerating.value) return ElMessage.info('回复完成后再切换对话'); try { await chatStore.switchSession(sessionId, groupId); mobileConversationsOpen.value = false; void disposeComposerAttachments(); scrollToBottom() } catch (error) { ElMessage.error(getApiErrorMessage(error, '切换对话失败')) } }
async function createNewSession() { try { await chatStore.createSession(); mobileConversationsOpen.value = false; void disposeComposerAttachments(); ElMessage.success('已新建对话') } catch (error) { ElMessage.error(getApiErrorMessage(error, '新建对话失败')) } }
async function createNewGroup() { try { const { value } = await ElMessageBox.prompt('给这个分组起个名称', '新建分组', { inputValue: '新分组', confirmButtonText: '创建', cancelButtonText: '取消', inputValidator: value => value?.trim() || '请输入分组名称' }); await chatStore.createGroup(value); mobileConversationsOpen.value = false; void disposeComposerAttachments(); ElMessage.success('分组已创建') } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error, '创建分组失败')) } }
async function handleGroupCommand(command, group) { try { if (command === 'rename') { const { value } = await ElMessageBox.prompt('请输入新的分组名称', '重命名分组', { inputValue: group.group_name, confirmButtonText: '保存', cancelButtonText: '取消', inputValidator: value => value?.trim() || '请输入分组名称' }); await chatStore.renameGroup(group.group_id, value); return ElMessage.success('分组名称已更新') } await ElMessageBox.confirm('删除“' + group.group_name + '”及其中全部对话？此操作无法撤销。', '删除分组', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }); await chatStore.deleteGroup(group.group_id); ElMessage.success('分组已删除') } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error, '操作失败')) } }
async function handleSessionCommand(command, group, session) { try { if (command === 'rename') { const { value } = await ElMessageBox.prompt('请输入新的对话名称', '重命名对话', { inputValue: session.session_name, confirmButtonText: '保存', cancelButtonText: '取消', inputValidator: value => value?.trim() || '请输入对话名称' }); await chatStore.renameSession(session.session_id, value); return ElMessage.success('对话名称已更新') } if (command === 'duplicate') { await chatStore.duplicateSession(session.session_id); return ElMessage.success('已复制为新的对话') } if (command === 'move') { moveDialog.sessionId = session.session_id; moveDialog.otherGroups = chatStore.groups.filter(item => item.group_id !== group.group_id); moveDialog.targetGroupId = moveDialog.otherGroups[0]?.group_id || ''; moveDialog.show = true; return } await ElMessageBox.confirm('删除“' + session.session_name + '”？此操作无法撤销。', '删除对话', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }); await chatStore.deleteSession(session.session_id); ElMessage.success('对话已删除') } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error, '操作失败')) } }
async function executeMove() { try { await chatStore.moveSession(moveDialog.sessionId, moveDialog.targetGroupId); moveDialog.show = false; ElMessage.success('对话已移动') } catch (error) { ElMessage.error(getApiErrorMessage(error, '移动对话失败')) } }
async function confirmClear() { try { await ElMessageBox.confirm('清空后无法恢复当前对话的消息。', '清空对话', { type: 'warning', confirmButtonText: '清空', cancelButtonText: '取消' }); await chatStore.clearActiveSession(); ElMessage.success('对话已清空') } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(getApiErrorMessage(error, '清空对话失败')) } }
function quoteMessage(message) { replyingMessage.value = message }
function navigateToMessage(messageId) { const element = document.getElementById('msg-' + messageId); if (!element) return ElMessage.info('引用的消息不在当前列表中'); element.scrollIntoView({ behavior: 'smooth', block: 'center' }); element.classList.add('chat-message--highlighted'); window.setTimeout(() => element.classList.remove('chat-message--highlighted'), 1300) }
async function copyToClipboard(text) { try { await navigator.clipboard.writeText(text || ''); ElMessage.success('已复制') } catch { ElMessage.error('复制失败，请检查浏览器权限') } }
function copyFullSession() { copyToClipboard(messages.value.map(message => '[' + (message.role === 'user' ? '你' : 'AI 助手') + '] ' + message.text).join('\n\n')) }
function sendQuick(text) { input.value = text; handleSend() }
function handleKeyEnter(event) { if (!event.shiftKey) handleSend() }
function stopGeneration() { abortController.value?.abort() }

async function handleSend() {
  const text = input.value.trim(); const attachments = readyAttachments.value
  if (!canSendMessage.value || !chatStore.activeSessionId) return
  const sessionId = chatStore.activeSessionId
  try {
    await chatStore.addMessage({ role: 'user', text: text || '已附上文件，请结合文件内容处理。', replyToId: replyingMessage.value?.id || null, reply_content: replyingMessage.value?.text || '' }, true, sessionId)
    input.value = ''; replyingMessage.value = null; isGenerating.value = true
    const assistantMessage = await chatStore.addMessage({ role: 'assistant', text: '', tokens: 0 }, false, sessionId)
    let responseText = ''; abortController.value = new AbortController()
    await streamPersona(text || '请结合已附文件回答。', sessionId, content => { if (!content) return; responseText += content; assistantMessage.text = responseText; scrollToBottom() }, null, abortController.value.signal, { sessionFileIds: attachments.map(item => item.fileId) })
    if (responseText.trim()) await chatStore.saveLastMessage(responseText, Math.ceil(responseText.length / 3), sessionId)
    else { const index = chatStore.messages.indexOf(assistantMessage); if (index >= 0) chatStore.messages.splice(index, 1); ElMessage.warning('服务没有返回可用内容，请稍后再试') }
    await disposeComposerAttachments()
  } catch (error) {
    const lastMessage = chatStore.messages.at(-1)
    if (error?.name === 'AbortError') { if (lastMessage?.role === 'assistant' && lastMessage.text.trim()) { try { await chatStore.saveLastMessage(lastMessage.text, Math.ceil(lastMessage.text.length / 3), sessionId) } catch {} } else if (lastMessage?.role === 'assistant') chatStore.messages.pop(); ElMessage.info('已停止生成') }
    else { if (lastMessage?.role === 'assistant' && !lastMessage.text) chatStore.messages.pop(); ElMessage.error(getApiErrorMessage(error, '发送失败')) }
  } finally { isGenerating.value = false; abortController.value = null; scrollToBottom() }
}

async function handleFileUpload(event) { const file = event.target.files?.[0]; if (!file || !chatStore.activeSessionId) { if (fileInputRef.value) fileInputRef.value.value = ''; return } const attachment = { localId: 'attachment-' + (++attachmentSequence) + '-' + Date.now(), fileName: file.name, fileId: null, previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : '', uploading: true, error: '' }; composerAttachments.value.push(attachment); try { const formData = new FormData(); formData.append('file', file); const uploaded = await sessionApi.uploadTemporaryFile(chatStore.activeSessionId, formData); attachment.fileId = uploaded.file_id } catch (error) { attachment.error = getApiErrorMessage(error, '上传失败'); ElMessage.error('上传失败：' + attachment.error) } finally { attachment.uploading = false; if (fileInputRef.value) fileInputRef.value.value = '' } }
async function removeComposerAttachment(attachment) { const index = composerAttachments.value.findIndex(item => item.localId === attachment.localId); if (index < 0) return; if (attachment.fileId) { try { await sessionApi.deleteTemporaryFile(attachment.fileId) } catch {} } if (attachment.previewUrl) URL.revokeObjectURL(attachment.previewUrl); composerAttachments.value.splice(index, 1) }
watch(messages, scrollToBottom, { deep: true })
onMounted(async () => { try { await chatStore.initStore(); scrollToBottom() } catch (error) { ElMessage.error(getApiErrorMessage(error, '无法加载对话')) } })
onBeforeUnmount(() => { abortController.value?.abort(); void disposeComposerAttachments() })
</script>

<style scoped>
.chat-workspace{display:flex;height:100vh;min-height:100vh;background:var(--bg-primary);color:var(--text-primary)}.chat-rail{display:flex;flex:0 0 282px;flex-direction:column;min-width:0;border-right:1px solid var(--border-color);background:var(--bg-secondary)}.chat-rail__header{display:flex;align-items:flex-start;justify-content:space-between;padding:24px 20px 16px}.eyebrow{margin:0 0 5px;color:var(--text-muted);font-size:11px;font-weight:700;letter-spacing:0;text-transform:uppercase}.chat-rail h1{margin:0;font-size:20px}.chat-rail__close{display:none}.chat-rail__actions{display:grid;grid-template-columns:minmax(0,1fr) 40px;gap:8px;padding:0 14px 16px;border-bottom:1px solid var(--border-color-light)}.chat-rail__actions .el-button{min-height:38px;margin:0;border-radius:7px}.conversation-groups{flex:1;overflow:auto;padding:14px 10px}.conversation-group{margin-bottom:20px}.conversation-group__heading{display:flex;align-items:center;justify-content:space-between;min-height:30px;padding:0 5px 4px 9px;color:var(--text-muted)}.conversation-group__heading>div{display:flex;min-width:0;align-items:center;gap:7px;font-size:12px;font-weight:700}.conversation-group__heading span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.conversation-session{display:flex;width:100%;min-width:0;align-items:center;gap:2px;min-height:40px;border:1px solid transparent;border-radius:7px;padding:0 5px 0 4px;color:var(--text-secondary);background:transparent;text-align:left;transition:.16s}.conversation-session:hover{color:var(--text-primary);background:var(--bg-tertiary)}.conversation-session--active{border-color:color-mix(in srgb,var(--color-primary) 25%,var(--border-color));color:var(--color-primary-dark);background:color-mix(in srgb,var(--color-primary) 10%,var(--bg-secondary));font-weight:700}.conversation-session__select{display:flex;min-width:0;flex:1;align-items:center;gap:9px;align-self:stretch;border:0;border-radius:5px;padding:0 6px;color:inherit;background:transparent;text-align:left;cursor:pointer;outline:none}.conversation-session__select>span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}.conversation-session__select:focus-visible{box-shadow:0 0 0 2px color-mix(in srgb,var(--color-primary) 42%,transparent)}.conversation-session .el-button{opacity:0}.conversation-session:hover .el-button,.conversation-session:focus-within .el-button,.conversation-session--active .el-button{opacity:1}.chat-rail__footer{display:flex;gap:10px;padding:14px 20px;border-top:1px solid var(--border-color-light);color:var(--text-muted);font-size:11px}.chat-main{display:flex;min-width:0;flex:1;flex-direction:column}.chat-topbar{display:flex;min-height:72px;align-items:center;justify-content:space-between;gap:18px;border-bottom:1px solid var(--border-color-light);padding:0 30px;background:color-mix(in srgb,var(--bg-primary) 94%,transparent)}.chat-topbar__context{display:flex;min-width:0;align-items:center;gap:10px}.chat-topbar__menu{display:none}.chat-topbar p{margin:0 0 3px;overflow:hidden;color:var(--text-muted);font-size:12px;text-overflow:ellipsis;white-space:nowrap}.chat-topbar h2{margin:0;overflow:hidden;font-size:16px;text-overflow:ellipsis;white-space:nowrap}.chat-topbar__tools{display:flex;flex:0 0 auto;align-items:center;gap:3px}.chat-status{display:inline-flex;align-items:center;gap:7px;margin-right:7px;color:var(--text-muted);font-size:12px}.chat-status i{width:7px;height:7px;border-radius:50%;background:var(--color-success)}.chat-status--busy{color:var(--color-primary-dark)}.chat-status--busy i{background:var(--color-primary);animation:pulse 1.1s ease-in-out infinite}.chat-error{display:flex;max-width:920px;width:calc(100% - 40px);align-items:center;gap:9px;margin:14px auto 0;border:1px solid color-mix(in srgb,var(--color-warning) 35%,var(--border-color));border-radius:7px;padding:9px 10px 9px 12px;color:var(--text-secondary);background:color-mix(in srgb,var(--color-warning) 9%,var(--bg-secondary));font-size:13px}.chat-error>.el-icon{color:var(--color-warning)}.chat-error .el-button{margin-left:auto}.messages-viewport{flex:1;overflow:auto;padding:36px 24px 24px}.messages-thread,.composer-thread{width:min(100%,880px);margin:0 auto}.messages-thread{display:flex;min-height:100%;flex-direction:column;gap:28px}.conversation-empty{display:grid;align-self:center;justify-items:center;max-width:540px;margin:auto;padding:34px 0 56px;text-align:center}.conversation-empty__mark{display:grid;width:42px;height:42px;place-items:center;margin-bottom:18px;border:1px solid color-mix(in srgb,var(--color-primary) 20%,var(--border-color));border-radius:7px;color:var(--color-primary-dark);background:color-mix(in srgb,var(--color-primary) 9%,var(--bg-secondary));font-size:20px}.conversation-empty h3{margin:0;font-size:26px;line-height:1.25}.conversation-empty>p:not(.eyebrow){max-width:420px;margin:12px 0 0;color:var(--text-secondary);font-size:14px;line-height:1.75}.prompt-list{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:24px}.prompt-list button{border:1px solid var(--border-color);border-radius:7px;padding:9px 12px;color:var(--text-secondary);background:var(--bg-secondary);font:inherit;font-size:13px;cursor:pointer}.prompt-list button:hover{border-color:color-mix(in srgb,var(--color-primary) 40%,var(--border-color));color:var(--color-primary-dark);background:color-mix(in srgb,var(--color-primary) 7%,var(--bg-secondary))}.chat-message{display:flex;width:100%;align-items:flex-start;gap:12px;scroll-margin-block:28px}.chat-message--user{justify-content:flex-end}.chat-message__avatar{display:grid;flex:0 0 auto;width:30px;height:30px;place-items:center;border:1px solid var(--border-color);border-radius:50%;color:var(--color-primary-dark);background:var(--bg-secondary);font-size:14px}.chat-message--user .chat-message__avatar{order:2;background:color-mix(in srgb,var(--color-primary) 15%,var(--bg-secondary))}.chat-message__body{min-width:0;max-width:min(100%,780px)}.chat-message--user .chat-message__body{max-width:min(78%,650px)}.chat-message__meta{display:flex;align-items:center;gap:8px;min-height:22px;margin-bottom:5px;color:var(--text-muted);font-size:12px}.chat-message--user .chat-message__meta{justify-content:flex-end}.chat-message__meta strong{color:var(--text-secondary);font-size:13px}.chat-message__meta>div{display:flex;margin-left:2px;opacity:0;transition:opacity .16s}.chat-message:hover .chat-message__meta>div{opacity:1}.chat-message__meta .el-button{margin:0}.chat-message__content{color:var(--text-primary);font-size:14px;line-height:1.78;overflow-wrap:anywhere}.chat-message--user .chat-message__content{border:1px solid color-mix(in srgb,var(--color-primary) 24%,var(--border-color));border-radius:7px;padding:11px 13px;background:color-mix(in srgb,var(--color-primary) 8%,var(--bg-secondary))}.chat-message__plain{white-space:pre-wrap}.chat-message small{display:block;margin-top:7px;color:var(--text-muted);font-size:11px}.chat-message--user small{text-align:right}.message-reference,.composer-reference{display:flex;align-items:center;gap:7px;border-left:2px solid var(--color-primary);color:var(--text-muted);font-size:12px}.message-reference{max-width:100%;margin:0 0 8px;padding:4px 8px;border-top:0;border-right:0;border-bottom:0;background:transparent;cursor:pointer}.message-reference span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.chat-message--highlighted .chat-message__body{animation:highlight 1.25s ease}.typing{display:flex;align-items:center;gap:5px;min-height:35px}.typing i{width:6px;height:6px;border-radius:50%;background:var(--color-primary);animation:typing .95s ease-in-out infinite}.typing i:nth-child(2){animation-delay:.14s}.typing i:nth-child(3){animation-delay:.28s}.composer-area{padding:14px 24px 24px;border-top:1px solid var(--border-color-light);background:var(--bg-primary)}.composer-reference{justify-content:space-between;min-height:34px;margin-bottom:8px;padding:5px 5px 5px 10px;background:color-mix(in srgb,var(--color-primary) 5%,var(--bg-secondary))}.composer-reference>div{display:flex;min-width:0;align-items:center;gap:7px}.composer-reference span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.composer-files{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}.composer-file{display:flex;max-width:min(100%,310px);align-items:center;gap:7px;min-height:38px;border:1px solid var(--border-color);border-radius:7px;padding:4px 5px 4px 8px;background:var(--bg-secondary)}.composer-file--error{border-color:color-mix(in srgb,var(--color-danger) 45%,var(--border-color))}.composer-file img{width:28px;height:28px;border-radius:4px;object-fit:cover}.composer-file>span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-secondary);font-size:12px}.composer-file small{color:var(--color-danger);font-size:11px}.composer-file .el-button{margin-left:auto}.upload-spinner{width:12px;height:12px;border:2px solid color-mix(in srgb,var(--color-primary) 22%,transparent);border-top-color:var(--color-primary);border-radius:50%;animation:spin .72s linear infinite}.composer-box{display:flex;align-items:flex-end;gap:8px;border:1px solid var(--border-color);border-radius:8px;padding:8px;background:var(--bg-secondary);box-shadow:0 6px 18px color-mix(in srgb,var(--text-primary) 4%,transparent);transition:.16s}.composer-box--focused{border-color:color-mix(in srgb,var(--color-primary) 50%,var(--border-color));box-shadow:0 0 0 3px color-mix(in srgb,var(--color-primary) 10%,transparent)}.composer-box .el-button{flex:0 0 auto;margin:0}.composer-box__input{flex:1}.composer-box__input :deep(.el-textarea__inner){min-height:30px!important;border:0;padding:5px 2px;box-shadow:none;color:var(--text-primary);background:transparent;line-height:1.55}.composer-box__input :deep(.el-textarea__inner:focus){box-shadow:none}.move-group-list{display:grid;gap:8px}.move-group-list :deep(.el-radio){width:100%;margin:0}@keyframes typing{0%,60%,100%{transform:translateY(0);opacity:.45}30%{transform:translateY(-4px);opacity:1}}@keyframes spin{to{transform:rotate(360deg)}}@keyframes pulse{50%{opacity:.42;transform:scale(.78)}}@keyframes highlight{0%,100%{background:transparent}45%{background:color-mix(in srgb,var(--color-primary) 10%,transparent)}}@media(max-width:900px){.chat-workspace{height:calc(100vh - 60px);min-height:calc(100vh - 60px)}.chat-rail{position:fixed;z-index:45;top:0;bottom:0;left:0;width:min(84vw,320px);transform:translateX(-104%);transition:transform .2s ease;box-shadow:12px 0 30px color-mix(in srgb,var(--text-primary) 16%,transparent)}.chat-rail--open{transform:translateX(0)}.chat-backdrop{position:fixed;z-index:44;inset:0;border:0;background:color-mix(in srgb,var(--text-primary) 36%,transparent)}.chat-rail__close,.chat-topbar__menu{display:inline-flex}.chat-topbar{min-height:62px;padding:0 14px}.chat-status{display:none}.messages-viewport{padding:24px 14px 16px}.composer-area{padding:10px 14px 14px}.chat-message--user .chat-message__body{max-width:86%}.conversation-empty{padding:24px 0 44px}.conversation-empty h3{font-size:22px}.chat-message__meta>div{opacity:1}.chat-topbar__tools>.el-button:first-of-type{display:none}}@media(max-width:560px){.chat-topbar__context{max-width:calc(100% - 82px)}.chat-message{gap:8px}.chat-message__avatar{width:28px;height:28px}.chat-message__meta>span{display:none}.prompt-list{display:grid;width:100%}.prompt-list button{width:100%}.composer-box{gap:4px}.composer-file{max-width:100%}.chat-error{width:calc(100% - 28px)}}
</style>
