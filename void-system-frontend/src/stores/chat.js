import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as chatApi from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
    // 核心状态：分组与会话
    const groups = ref([])
    const activeGroupId = ref(null)
    const activeSessionId = ref(null)
    const isLoading = ref(false)

    // --- Getters ---

    const activeGroup = computed(() => groups.value.find(g => g.group_id === activeGroupId.value))

    const activeSession = computed(() => {
        if (!activeGroup.value) return null
        return activeGroup.value.sessions?.find(s => s.session_id === activeSessionId.value)
    })

    const messages = ref([]) // 当前活跃会话的消息列表

    // --- Actions ---

    /**
     * 初始化数据，从后端加载所有历史
     */
    const initStore = async () => {
        isLoading.value = true
        try {
            const history = await chatApi.getChatHistory()
            groups.value = history

            // 恢复最后的活跃状态或设为默认
            if (groups.value.length > 0) {
                activeGroupId.value = localStorage.getItem('void_active_group_id') || groups.value[0].group_id
                const group = groups.value.find(g => g.group_id === activeGroupId.value) || groups.value[0]
                activeGroupId.value = group.group_id

                if (group.sessions?.length > 0) {
                    activeSessionId.value = localStorage.getItem('void_active_session_id') || group.sessions[0].session_id
                    const session = group.sessions.find(s => s.session_id === activeSessionId.value) || group.sessions[0]
                    activeSessionId.value = session.session_id

                    // 加载消息
                    await loadMessages(activeSessionId.value)
                }
            } else {
                // 如果后端完全没数据，创建一个默认的分组
                await createGroup('默认分组')
            }
        } catch (error) {
            console.error('初始化聊天存储失败:', error)
        } finally {
            isLoading.value = false
        }
    }

    /**
     * 加载特定会话的消息
     */
    const loadMessages = async (sessionId) => {
        try {
            const msgs = await chatApi.getChatMessages(sessionId)
            // 转换后端消息格式到前端格式
            messages.value = msgs.map(m => ({
                id: m.message_id,
                role: m.role,
                text: m.content,
                timestamp: m.created_at,
                tokens: m.tokens,
                replyToId: m.reply_to_id,
                reply_content: m.reply_content
            }))
        } catch (error) {
            console.error('加载消息失败:', error)
            messages.value = []
        }
    }

    /**
     * 切换分组
     */
    const switchGroup = async (groupId) => {
        activeGroupId.value = groupId
        localStorage.setItem('void_active_group_id', groupId)

        const group = groups.value.find(g => g.group_id === groupId)
        if (group && group.sessions?.length > 0) {
            await switchSession(group.sessions[0].session_id)
        } else {
            activeSessionId.value = null
            messages.value = []
        }
    }

    /**
     * 切换会话
     */
    const switchSession = async (sessionId) => {
        activeSessionId.value = sessionId
        localStorage.setItem('void_active_session_id', sessionId)
        await loadMessages(sessionId)
    }

    /**
     * 创建新分组
     */
    const createGroup = async (name = '新任务组') => {
        try {
            const groupId = await chatApi.createChatGroup(name)
            const sessionId = await chatApi.createChatSession(groupId, '初始对话')

            // 重新刷新数据以确保同步
            const history = await chatApi.getChatHistory()
            groups.value = history

            activeGroupId.value = groupId
            activeSessionId.value = sessionId
            messages.value = []

            localStorage.setItem('void_active_group_id', groupId)
            localStorage.setItem('void_active_session_id', sessionId)
        } catch (error) {
            console.error('创建分组失败:', error)
        }
    }

    /**
     * 在当前分组创建新会话
     */
    const createSession = async (name = '新对话') => {
        if (!activeGroupId.value) return
        try {
            const sessionId = await chatApi.createChatSession(activeGroupId.value, name)

            // 更新本地状态
            const group = groups.value.find(g => g.group_id === activeGroupId.value)
            if (group) {
                if (!group.sessions) group.sessions = []
                group.sessions.unshift({
                    session_id: sessionId,
                    session_name: name,
                    created_at: new Date().toISOString()
                })
            }

            activeSessionId.value = sessionId
            messages.value = []
            localStorage.setItem('void_active_session_id', sessionId)
        } catch (error) {
            console.error('创建会话失败:', error)
        }
    }

    /**
     * 添加消息到活跃会话
     */
    const addMessage = async (message) => {
        if (!activeSessionId.value) return
        try {
            const msgId = await chatApi.addChatMessage(activeSessionId.value, {
                role: message.role,
                content: message.text,
                tokens: message.tokens || 0,
                replyToId: message.replyToId
            })

            const newMessage = {
                id: msgId,
                ...message,
                timestamp: new Date().toISOString()
            }
            messages.value.push(newMessage)

            // 如果是第一条用户消息，尝试更新会话名称
            const session = activeSession.value
            if (messages.value.filter(m => m.role === 'user').length === 1 && message.role === 'user') {
                const title = message.text.substring(0, 15)
                const newName = title + (message.text.length > 15 ? '...' : '')
                await renameSession(activeSessionId.value, newName)
            }

            return msgId
        } catch (error) {
            console.error('添加消息失败:', error)
        }
    }

    /**
     * 更新最后一条回复（流式传输时使用，通常也是后端持久化）
     * 注意：对于流式传输，我们通常在流结束时保存一次
     */
    const saveLastMessage = async (content, tokens = 0) => {
        if (!activeSessionId.value) return
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.text = content
            lastMsg.tokens = tokens
            // 正式保存到后端
            await chatApi.addChatMessage(activeSessionId.value, {
                role: 'assistant',
                content: content,
                tokens: tokens
            })
        }
    }

    /**
     * 重命名分组
     */
    const renameGroup = async (groupId, newName) => {
        try {
            await chatApi.updateChatGroup(groupId, newName)
            const group = groups.value.find(g => g.group_id === groupId)
            if (group) group.group_name = newName
        } catch (error) {
            console.error('重命名分组失败:', error)
        }
    }

    /**
     * 重命名会话
     */
    const renameSession = async (sessionId, newName) => {
        try {
            await chatApi.updateChatSession(sessionId, { sessionName: newName })
            const group = groups.value.find(g => g.sessions?.some(s => s.session_id === sessionId))
            if (group) {
                const session = group.sessions.find(s => s.session_id === sessionId)
                if (session) session.session_name = newName
            }
        } catch (error) {
            console.error('重命名会话失败:', error)
        }
    }

    /**
     * 移动会话到其他分组
     */
    const moveSession = async (sessionId, targetGroupId) => {
        try {
            await chatApi.updateChatSession(sessionId, { groupId: targetGroupId })
            // 刷新全部数据以反映变化
            const history = await chatApi.getChatHistory()
            groups.value = history
        } catch (error) {
            console.error('移动会话失败:', error)
        }
    }

    /**
     * 清除当前会话历史
     */
    const clearActiveSession = async () => {
        if (!activeSessionId.value) return
        try {
            await chatApi.clearChatMessages(activeSessionId.value)
            messages.value = []
        } catch (error) {
            console.error('清空会话失败:', error)
        }
    }

    /**
     * 删除会话
     */
    const deleteSession = async (sessionId) => {
        try {
            await chatApi.deleteChatSession(sessionId)
            const history = await chatApi.getChatHistory()
            groups.value = history

            if (activeSessionId.value === sessionId) {
                if (groups.value.length > 0 && groups.value[0].sessions?.length > 0) {
                    await switchSession(groups.value[0].sessions[0].session_id)
                } else {
                    activeSessionId.value = null
                    messages.value = []
                }
            }
        } catch (error) {
            console.error('删除会话失败:', error)
        }
    }

    /**
     * 删除分组
     */
    const deleteGroup = async (groupId) => {
        try {
            await chatApi.deleteChatGroup(groupId)
            const history = await chatApi.getChatHistory()
            groups.value = history

            if (activeGroupId.value === groupId) {
                if (groups.value.length > 0) {
                    await switchGroup(groups.value[0].group_id)
                } else {
                    activeGroupId.value = null
                    activeSessionId.value = null
                    messages.value = []
                }
            }
        } catch (error) {
            console.error('删除分组失败:', error)
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
        renameGroup,
        renameSession,
        moveSession
    }
})
