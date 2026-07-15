import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as chatApi from '@/api/chat'

const ACTIVE_GROUP_KEY = 'void_active_group_id'
const ACTIVE_SESSION_KEY = 'void_active_session_id'

function readableError(error, fallback) {
  return error?.response?.data?.message || error?.response?.data?.detail || error?.message || fallback
}

export const useChatStore = defineStore('chat', () => {
  const groups = ref([])
  const activeGroupId = ref(null)
  const activeSessionId = ref(null)
  const messages = ref([])
  const isLoading = ref(false)
  const lastError = ref('')

  const activeGroup = computed(() => groups.value.find((group) => group.group_id === activeGroupId.value) || null)
  const activeSession = computed(() => activeGroup.value?.sessions?.find((session) => session.session_id === activeSessionId.value) || null)

  function clearError() {
    lastError.value = ''
  }

  function rememberSelection(groupId, sessionId) {
    activeGroupId.value = groupId || null
    activeSessionId.value = sessionId || null

    if (groupId) localStorage.setItem(ACTIVE_GROUP_KEY, groupId)
    else localStorage.removeItem(ACTIVE_GROUP_KEY)

    if (sessionId) localStorage.setItem(ACTIVE_SESSION_KEY, sessionId)
    else localStorage.removeItem(ACTIVE_SESSION_KEY)
  }

  function groupForSession(sessionId) {
    return groups.value.find((group) => group.sessions?.some((session) => session.session_id === sessionId)) || null
  }

  async function refreshHistory() {
    groups.value = await chatApi.getChatHistory()
    return groups.value
  }

  async function loadMessages(sessionId) {
    try {
      const loaded = await chatApi.getChatMessages(sessionId)
      if (activeSessionId.value !== sessionId) return []

      messages.value = loaded.map((message) => ({
        id: message.message_id,
        role: message.role,
        text: message.content,
        timestamp: message.created_at,
        tokens: message.tokens,
        replyToId: message.reply_to_id,
        reply_content: message.reply_content
      }))
      return messages.value
    } catch (error) {
      lastError.value = readableError(error, '加载对话失败')
      if (activeSessionId.value === sessionId) messages.value = []
      throw error
    }
  }

  async function switchSession(sessionId, explicitGroupId = null) {
    const group = explicitGroupId
      ? groups.value.find((item) => item.group_id === explicitGroupId)
      : groupForSession(sessionId)

    if (!group || !group.sessions?.some((session) => session.session_id === sessionId)) return false

    clearError()
    rememberSelection(group.group_id, sessionId)
    await loadMessages(sessionId)
    return true
  }

  async function switchGroup(groupId) {
    const group = groups.value.find((item) => item.group_id === groupId)
    if (!group) return false

    if (!group.sessions?.length) {
      clearError()
      rememberSelection(group.group_id, null)
      messages.value = []
      return true
    }

    return switchSession(group.sessions[0].session_id, group.group_id)
  }

  async function createGroup(name = '新分组') {
    try {
      clearError()
      let finalName = name.trim() || '新分组'
      let count = 1
      while (groups.value.some((group) => group.group_name === finalName)) {
        finalName = `${name.trim() || '新分组'} ${count++}`
      }

      const groupId = await chatApi.createChatGroup(finalName)
      const sessionId = await chatApi.createChatSession(groupId, '新对话')
      await refreshHistory()
      rememberSelection(groupId, sessionId)
      messages.value = []
      return { groupId, sessionId }
    } catch (error) {
      lastError.value = readableError(error, '创建分组失败')
      throw error
    }
  }

  async function createSession(name = '新对话') {
    if (!activeGroupId.value) return createGroup()

    try {
      clearError()
      const group = groups.value.find((item) => item.group_id === activeGroupId.value)
      const baseName = name.trim() || '新对话'
      let finalName = baseName
      let count = 1
      while (group?.sessions?.some((session) => session.session_name === finalName)) {
        finalName = `${baseName} ${count++}`
      }

      const sessionId = await chatApi.createChatSession(activeGroupId.value, finalName)
      await refreshHistory()
      rememberSelection(activeGroupId.value, sessionId)
      messages.value = []
      return sessionId
    } catch (error) {
      lastError.value = readableError(error, '创建对话失败')
      throw error
    }
  }

  async function addMessage(message, save = true, sessionId = activeSessionId.value) {
    if (!sessionId) throw new Error('请先创建对话')

    const temporaryId = `temp-${Date.now()}-${Math.random().toString(16).slice(2)}`
    const newMessage = {
      id: temporaryId,
      ...message,
      timestamp: message.timestamp || new Date().toISOString()
    }

    if (activeSessionId.value === sessionId) messages.value.push(newMessage)
    if (!save) return newMessage

    try {
      const realId = await chatApi.addChatMessage(sessionId, {
        role: message.role,
        content: message.text,
        tokens: message.tokens || 0,
        replyToId: message.replyToId || null
      })
      newMessage.id = realId || temporaryId
      return newMessage
    } catch (error) {
      if (activeSessionId.value === sessionId) {
        messages.value = messages.value.filter((item) => item.id !== temporaryId)
      }
      lastError.value = readableError(error, '保存消息失败')
      throw error
    }
  }

  async function saveLastMessage(content, tokens = 0, sessionId = activeSessionId.value) {
    if (!sessionId) return null

    const lastMessage = activeSessionId.value === sessionId ? messages.value.at(-1) : null
    if (lastMessage && (lastMessage.role === 'assistant' || lastMessage.role === 'system')) {
      lastMessage.text = content
      lastMessage.tokens = tokens
    }

    try {
      const messageId = await chatApi.addChatMessage(sessionId, {
        role: lastMessage?.role || 'assistant',
        content,
        tokens
      })
      if (lastMessage && messageId) lastMessage.id = messageId
      return messageId
    } catch (error) {
      lastError.value = readableError(error, '保存回复失败')
      throw error
    }
  }

  async function duplicateSession(sessionId) {
    try {
      clearError()
      const newSessionId = await chatApi.duplicateChatSession(sessionId)
      await refreshHistory()
      await switchSession(newSessionId)
      return newSessionId
    } catch (error) {
      lastError.value = readableError(error, '复制对话失败')
      throw error
    }
  }

  async function renameGroup(groupId, name) {
    try {
      const finalName = name.trim()
      if (!finalName) return false
      clearError()
      await chatApi.updateChatGroup(groupId, finalName)
      const group = groups.value.find((item) => item.group_id === groupId)
      if (group) group.group_name = finalName
      return true
    } catch (error) {
      lastError.value = readableError(error, '重命名分组失败')
      throw error
    }
  }

  async function renameSession(sessionId, name) {
    try {
      const finalName = name.trim()
      if (!finalName) return false
      clearError()
      await chatApi.updateChatSession(sessionId, { sessionName: finalName })
      const group = groupForSession(sessionId)
      const session = group?.sessions?.find((item) => item.session_id === sessionId)
      if (session) session.session_name = finalName
      return true
    } catch (error) {
      lastError.value = readableError(error, '重命名对话失败')
      throw error
    }
  }

  async function moveSession(sessionId, targetGroupId) {
    try {
      clearError()
      await chatApi.updateChatSession(sessionId, { groupId: targetGroupId })
      await refreshHistory()
      if (activeSessionId.value === sessionId) await switchSession(sessionId, targetGroupId)
      return true
    } catch (error) {
      lastError.value = readableError(error, '移动对话失败')
      throw error
    }
  }

  async function clearActiveSession() {
    if (!activeSessionId.value) return false
    try {
      clearError()
      await chatApi.clearChatMessages(activeSessionId.value)
      messages.value = []
      return true
    } catch (error) {
      lastError.value = readableError(error, '清空对话失败')
      throw error
    }
  }

  async function deleteSession(sessionId) {
    try {
      clearError()
      await chatApi.deleteChatSession(sessionId)
      await refreshHistory()

      if (activeSessionId.value === sessionId) {
        const nextGroup = groups.value.find((group) => group.sessions?.length)
        if (nextGroup) await switchSession(nextGroup.sessions[0].session_id, nextGroup.group_id)
        else {
          rememberSelection(null, null)
          messages.value = []
        }
      }
      return true
    } catch (error) {
      lastError.value = readableError(error, '删除对话失败')
      throw error
    }
  }

  async function deleteGroup(groupId) {
    try {
      clearError()
      await chatApi.deleteChatGroup(groupId)
      await refreshHistory()

      if (activeGroupId.value === groupId) {
        const nextGroup = groups.value.find((group) => group.sessions?.length)
        if (nextGroup) await switchSession(nextGroup.sessions[0].session_id, nextGroup.group_id)
        else {
          rememberSelection(null, null)
          messages.value = []
        }
      }
      return true
    } catch (error) {
      lastError.value = readableError(error, '删除分组失败')
      throw error
    }
  }

  async function initStore() {
    isLoading.value = true
    try {
      clearError()
      await refreshHistory()
      if (!groups.value.length) {
        await createGroup('默认分组')
        return true
      }

      const savedGroupId = localStorage.getItem(ACTIVE_GROUP_KEY)
      const preferredGroup = groups.value.find((group) => group.group_id === savedGroupId && group.sessions?.length)
        || groups.value.find((group) => group.sessions?.length)

      if (!preferredGroup) {
        await createGroup('默认分组')
        return true
      }

      const savedSessionId = localStorage.getItem(ACTIVE_SESSION_KEY)
      const preferredSession = preferredGroup.sessions.find((session) => session.session_id === savedSessionId)
        || preferredGroup.sessions[0]
      await switchSession(preferredSession.session_id, preferredGroup.group_id)
      return true
    } catch (error) {
      lastError.value = readableError(error, '初始化对话失败')
      throw error
    } finally {
      isLoading.value = false
    }
  }

  return {
    groups,
    activeGroupId,
    activeSessionId,
    activeGroup,
    activeSession,
    messages,
    isLoading,
    lastError,
    clearError,
    initStore,
    switchGroup,
    switchSession,
    createGroup,
    createSession,
    addMessage,
    saveLastMessage,
    clearActiveSession,
    deleteSession,
    deleteGroup,
    duplicateSession,
    renameGroup,
    renameSession,
    moveSession
  }
})
