import api from "./index"

// 调用系统精灵对话（带会话记忆）
export const askPersona = async (text) => {
  // 从localStorage获取或生成session_id（持久化会话）
  let sessionId = localStorage.getItem('persona_session_id');
  if (!sessionId) {
    sessionId = 'user-' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('persona_session_id', sessionId);
  }

  const res = await api.post("/lc/persona/invoke", {
    input: { text,configurable: { session_id: sessionId } },
     // 显式传递session_id
  })
  return res.data.output
}


// 调用学习任务建议
export const getAdvisor = async (topic) => {
  const res = await api.post("/lc/advisor/invoke", {
    input: { topic }
  })
  return res.data.output
}

// 调用知识问答
export const askQA = async (question) => {
  const res = await api.post("/lc/qa/invoke", {
    input: { question }
  })
  return res.data.output
}
