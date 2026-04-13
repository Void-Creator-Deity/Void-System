import api from "./index"

/**
 * 获取所有对话历史（分组和会话）
 */
export const getChatHistory = async () => {
    const res = await api.get("/api/chat/groups")
    return res.data?.data?.groups ?? []
}

/**
 * 创建新对话分组
 */
export const createChatGroup = async (groupName) => {
    const res = await api.post("/api/chat/groups", { group_name: groupName })
    return res.data?.data?.group_id ?? null
}

/**
 * 更新分组名称
 */
export const updateChatGroup = async (groupId, groupName) => {
    const res = await api.put(`/api/chat/groups/${groupId}`, { group_name: groupName })
    return res.data.success
}

/**
 * 删除对话分组
 */
export const deleteChatGroup = async (groupId) => {
    const res = await api.delete(`/api/chat/groups/${groupId}`)
    return res.data.success
}

/**
 * 创建新对话会话
 */
export const createChatSession = async (groupId, sessionName, sessionId = null) => {
    const res = await api.post("/api/chat/sessions", {
        group_id: groupId,
        session_name: sessionName,
        session_id: sessionId
    })
    return res.data?.data?.session_id ?? null
}

/**
 * 更新会话信息（重命名或移动分组）
 */
export const updateChatSession = async (sessionId, { sessionName, groupId }) => {
    const res = await api.put(`/api/chat/sessions/${sessionId}`, {
        session_name: sessionName,
        group_id: groupId
    })
    return res.data.success
}

/**
 * 删除对话会话
 */
export const deleteChatSession = async (sessionId) => {
    const res = await api.delete(`/api/chat/sessions/${sessionId}`)
    return res.data.success
}

/**
 * 拷贝对话会话（生成完整副本）
 */
export const duplicateChatSession = async (sessionId) => {
    const res = await api.post(`/api/chat/sessions/${sessionId}/duplicate`)
    return res.data?.data?.session_id ?? null
}

/**
 * 获取会话历史记录
 */
export const getChatMessages = async (sessionId, limit = 100) => {
    const res = await api.get(`/api/chat/sessions/${sessionId}/messages`, { params: { limit } })
    return res.data?.data?.messages ?? []
}

/**
 * 新增对话消息
 */
export const addChatMessage = async (sessionId, { role, content, tokens = 0, replyToId = null }) => {
    const res = await api.post(`/api/chat/sessions/${sessionId}/messages`, {
        role,
        content,
        tokens,
        reply_to_id: replyToId
    })
    return res.data?.data?.message_id ?? null
}

/**
 * 清空会话历史
 */
export const clearChatMessages = async (sessionId) => {
    const res = await api.delete(`/api/chat/sessions/${sessionId}/messages`)
    return res.data.success
}
