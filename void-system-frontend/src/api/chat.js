import api, { apiRequest } from "./index"

/**
 * 获取所有对话历史（分组和会话）
 */
export const getChatHistory = async () => {
    const data = await apiRequest(api.get("/api/chat/groups"))
    return data?.groups ?? []
}

/**
 * 创建新对话分组
 */
export const createChatGroup = async (groupName) => {
    const data = await apiRequest(api.post("/api/chat/groups", { group_name: groupName }))
    return data?.group_id ?? null
}

/**
 * 更新分组名称
 */
export const updateChatGroup = async (groupId, groupName) => {
    await apiRequest(api.put(`/api/chat/groups/${groupId}`, { group_name: groupName }))
    return true
}

/**
 * 删除对话分组
 */
export const deleteChatGroup = async (groupId) => {
    await apiRequest(api.delete(`/api/chat/groups/${groupId}`))
    return true
}

/**
 * 创建新对话会话
 */
export const createChatSession = async (groupId, sessionName, sessionId = null) => {
    const data = await apiRequest(api.post("/api/chat/sessions", {
        group_id: groupId,
        session_name: sessionName,
        session_id: sessionId
    }))
    return data?.session_id ?? null
}

/**
 * 更新会话信息（重命名或移动分组）
 */
export const updateChatSession = async (sessionId, { sessionName, groupId }) => {
    await apiRequest(api.put(`/api/chat/sessions/${sessionId}`, {
        session_name: sessionName,
        group_id: groupId
    }))
    return true
}

/**
 * 删除对话会话
 */
export const deleteChatSession = async (sessionId) => {
    await apiRequest(api.delete(`/api/chat/sessions/${sessionId}`))
    return true
}

/**
 * 拷贝对话会话（生成完整副本）
 */
export const duplicateChatSession = async (sessionId) => {
    const data = await apiRequest(api.post(`/api/chat/sessions/${sessionId}/duplicate`))
    return data?.session_id ?? null
}

/**
 * 获取会话历史记录
 */
export const getChatMessages = async (sessionId, limit = 100) => {
    const data = await apiRequest(api.get(`/api/chat/sessions/${sessionId}/messages`, { params: { limit } }))
    return data?.messages ?? []
}

/**
 * 新增对话消息
 */
export const addChatMessage = async (sessionId, { role, content, tokens = 0, replyToId = null }) => {
    const data = await apiRequest(api.post(`/api/chat/sessions/${sessionId}/messages`, {
        role,
        content,
        tokens,
        reply_to_id: replyToId
    }))
    return data?.message_id ?? null
}

/**
 * 清空会话历史
 */
export const clearChatMessages = async (sessionId) => {
    await apiRequest(api.delete(`/api/chat/sessions/${sessionId}/messages`))
    return true
}
