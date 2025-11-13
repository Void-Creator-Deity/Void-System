import api from "./index"

// 调用系统精灵对话
export const askPersona = async (text) => {
  const res = await api.post("/lc/persona/invoke", {
    input: { text }
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
