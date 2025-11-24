/**
 * Void System Frontend - AI API
 * -----------------------------
 * AI 服务相关的 API 接口（系统精灵、任务建议、知识问答）
 */

import api from "./index"

/**
 * 调用系统精灵对话（带会话记忆）
 * @param {string} text - 用户输入的文本
 * @param {import('axios').CancelToken} [cancelToken] - 可选的取消令牌
 * @returns {Promise<string>} AI 回复内容
 */
export const askPersona = async (text, cancelToken) => {
  // 从 localStorage 获取或生成 session_id（持久化会话）
  let sessionId = localStorage.getItem('persona_session_id')
  if (!sessionId) {
    sessionId = 'user-' + Math.random().toString(36).substring(2, 11)
    localStorage.setItem('persona_session_id', sessionId)
  }

  const res = await api.post(
    "/lc/persona/invoke",
    {
      input: {
        text,
        config: {
          configurable: {
            session_id: sessionId
          }
        }
      }
    },
    {
      cancelToken  // 传递取消令牌（用于取消请求）
    }
  )
  
  return res.data.output
}

/**
 * 调用学习任务建议生成
 * @param {string} topic - 学习主题
 * @param {import('axios').CancelToken} [cancelToken] - 可选的取消令牌
 * @returns {Promise<string>} 任务建议内容
 */
export const getAdvisor = async (topic, cancelToken) => {
  const res = await api.post(
    "/lc/advisor/invoke",
    {
      input: { topic }
    },
    {
      cancelToken
    }
  )
  
  return res.data.output
}

/**
 * 调用知识问答（基于 RAG）
 * @param {string} question - 用户问题
 * @param {import('axios').CancelToken} [cancelToken] - 可选的取消令牌
 * @returns {Promise<string>} 问答结果
 */
export const askQA = async (question, cancelToken) => {
  const res = await api.post(
    "/lc/qa/invoke",
    {
      input: { question }
    },
    {
      cancelToken
    }
  )
  
  return res.data.output
}
