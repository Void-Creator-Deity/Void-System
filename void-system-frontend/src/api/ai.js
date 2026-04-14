/**
 * Void System Frontend - AI API
 * -----------------------------
 * AI 服务相关的 API 接口（系统精灵、任务建议、知识问答）
 */

import api from "./index"

const getAdvisorPrefsFromSettings = () => {
  const raw = localStorage.getItem('settings_cache')
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    const systemConfig = parsed?.systemConfig || {}
    const responseStyle = typeof systemConfig.responseStyle === 'string' ? systemConfig.responseStyle : '专业'
    const aiTemperature = Number(systemConfig.aiTemperature)
    return {
      response_style: responseStyle,
      response_temperature: Number.isFinite(aiTemperature) ? Math.min(100, Math.max(0, aiTemperature)) : 35
    }
  } catch {
    return null
  }
}

/**
 * 流式调用系统精灵对话（带会话记忆和打字机效果）
 * @param {string} text - 用户输入的文本
 * @param {string} sessionId - 会话ID
 * @param {function} onMessage - 接收消息的回调函数
 * @param {function} onError - 错误回调函数
 * @param {AbortSignal} signal - 可选中止信号
 * @param {{ sessionFileIds?: string[], images?: string[] }} options - 多模态：会话临时文件 ID、或 data URL / base64 图片列表
 * @returns {function} 取消函数
 */
export const streamPersona = async (text, sessionId, onMessage, onError, signal, options = {}) => {
  try {
    // 使用配置好的 api 实例的 baseURL，添加认证令牌
    const token = localStorage.getItem('access_token');
    const headers = {
      'Content-Type': 'application/json'
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    // 使用 Fetch API 的 ReadableStream 处理 POST 流式响应
    // 使用相对路径，让 Vite 代理自动处理 CORS
    const response = await fetch('/api/stream-chat', {
      method: 'POST',
      headers: headers,
      credentials: 'include', // 包含凭证，如 cookies
      body: JSON.stringify({
        type: 'persona',
        text,
        session_id: sessionId,
        session_file_ids: options.sessionFileIds || [],
        images: options.images || []
      }),
      signal: signal
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 获取 ReadableStream
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let accumulatedData = '';
    let finished = false;

    // 循环读取流中的数据
    while (!finished) {
      const { done, value } = await reader.read();
      finished = done;

      if (value) {
        // 解码新接收的数据
        const chunk = decoder.decode(value, { stream: !finished });
        accumulatedData += chunk;

        // 处理接收到的数据
        // 注意：这里需要根据后端实际返回的格式来处理
        // 后端返回的是 Server-Sent Events (SSE) 格式，需要解析
        const lines = accumulatedData.split('\n');
        let processLines = [...lines];

        // 检查最后一行是否完整
        if (!finished && lines.length > 0 && lines[lines.length - 1] !== '') {
          // 最后一行不完整，保存下来，和下一次的数据合并
          processLines = lines.slice(0, -1);
          accumulatedData = lines[lines.length - 1];
        } else {
          accumulatedData = '';
        }

        // 处理每一行 SSE 数据
        for (const line of processLines) {
          if (line.trim() === '') continue;
          if (line.startsWith('data: ')) {
            try {
              const jsonData = line.substring(6); // 移除 'data: ' 前缀
              const data = JSON.parse(jsonData);
              onMessage(data.content, data.finished);
              if (data.finished) {
                finished = true;
                break;
              }
            } catch (error) {
              console.error('解析 SSE 数据失败:', error);
            }
          }
        }
      }
    }

    // 关闭 reader
    reader.releaseLock();
  } catch (error) {
    console.error('流式请求失败:', error);
    onError(error);
  }
};

/**
 * 对已上传的会话临时图片请求无状态中文摘要（不污染多轮记忆）
 * @param {{ fileId: string, sessionId: string }} params
 * @returns {Promise<{ summary: string }>}
 */
export async function requestImageCaption({ fileId, sessionId }) {
  const { data } = await api.post("/api/ai/image-caption", {
    file_id: fileId,
    session_id: sessionId,
  })
  if (!data.success) {
    throw new Error(data.message || "看图摘要失败")
  }
  return { summary: data.data?.summary ?? "" }
}

/**
 * 流式调用学习任务建议生成
 * @param {string} topic - 学习主题
 * @param {function} onMessage - 接收消息的回调函数
 * @param {function} onError - 错误回调函数
 * @returns {function} 取消函数
 */
export const streamAdvisor = async (topic, onMessage, onError, signal) => {
  try {
    // 使用配置好的 api 实例的 baseURL，添加认证令牌
    const token = localStorage.getItem('access_token');
    const headers = {
      'Content-Type': 'application/json'
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    // 使用 Fetch API 的 ReadableStream 处理 POST 流式响应
    // 使用相对路径，让 Vite 代理自动处理 CORS
    const response = await fetch('/api/stream-chat', {
      method: 'POST',
      headers: headers,
      credentials: 'include', // 包含凭证，如 cookies
      body: JSON.stringify({
        type: 'advisor',
        topic
      }),
      signal: signal
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 获取 ReadableStream
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let accumulatedData = '';
    let finished = false;

    // 循环读取流中的数据
    while (!finished) {
      const { done, value } = await reader.read();
      finished = done;

      if (value) {
        // 解码新接收的数据
        const chunk = decoder.decode(value, { stream: !finished });
        accumulatedData += chunk;

        // 处理接收到的数据
        const lines = accumulatedData.split('\n');
        let processLines = [...lines];

        // 检查最后一行是否完整
        if (!finished && lines.length > 0 && lines[lines.length - 1] !== '') {
          processLines = lines.slice(0, -1);
          accumulatedData = lines[lines.length - 1];
        } else {
          accumulatedData = '';
        }

        // 处理每一行 SSE 数据
        for (const line of processLines) {
          if (line.trim() === '') continue;
          if (line.startsWith('data: ')) {
            try {
              const jsonData = line.substring(6);
              const data = JSON.parse(jsonData);
              onMessage(data.content, data.finished);
              if (data.finished) {
                finished = true;
                break;
              }
            } catch (error) {
              console.error('解析 SSE 数据失败:', error);
            }
          }
        }
      }
    }

    reader.releaseLock();
  } catch (error) {
    console.error('流式请求失败:', error);
    onError(error);
  }
};

/**
 * 流式调用知识问答（基于 RAG）
 * @param {string} question - 用户问题
 * @param {function} onMessage - 接收消息的回调函数
 * @param {function} onError - 错误回调函数
 * @returns {function} 取消函数
 */
export const streamQA = async (question, onMessage, onError, signal) => {
  try {
    // 使用配置好的 api 实例的 baseURL，添加认证令牌
    const token = localStorage.getItem('access_token');
    const headers = {
      'Content-Type': 'application/json'
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    // 使用 Fetch API 的 ReadableStream 处理 POST 流式响应
    // 使用相对路径，让 Vite 代理自动处理 CORS
    const response = await fetch('/api/stream-chat', {
      method: 'POST',
      headers: headers,
      credentials: 'include', // 包含凭证，如 cookies
      body: JSON.stringify({
        type: 'qa',
        question
      }),
      signal: signal
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 获取 ReadableStream
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let accumulatedData = '';
    let finished = false;

    // 循环读取流中的数据
    while (!finished) {
      const { done, value } = await reader.read();
      finished = done;

      if (value) {
        // 解码新接收的数据
        const chunk = decoder.decode(value, { stream: !finished });
        accumulatedData += chunk;

        // 处理接收到的数据
        const lines = accumulatedData.split('\n');
        let processLines = [...lines];

        // 检查最后一行是否完整
        if (!finished && lines.length > 0 && lines[lines.length - 1] !== '') {
          processLines = lines.slice(0, -1);
          accumulatedData = lines[lines.length - 1];
        } else {
          accumulatedData = '';
        }

        // 处理每一行 SSE 数据
        for (const line of processLines) {
          if (line.trim() === '') continue;
          if (line.startsWith('data: ')) {
            try {
              const jsonData = line.substring(6);
              const data = JSON.parse(jsonData);
              onMessage(data.content, data.finished);
              if (data.finished) {
                finished = true;
                break;
              }
            } catch (error) {
              console.error('解析 SSE 数据失败:', error);
            }
          }
        }
      }
    }

    reader.releaseLock();
  } catch (error) {
    console.error('流式请求失败:', error);
    onError(error);
  }
};

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
    "/api/lc/persona/invoke",
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

  // 处理响应格式，提取净化后的内容
  return res.data.output?.content || res.data.output
}

/**
 * 调用学习任务建议生成
 * @param {string} topic - 学习主题
 * @param {import('axios').CancelToken} [cancelToken] - 可选的取消令牌
 * @returns {Promise<Object>} 结构化任务建议内容
 */
export const getAdvisor = async (topic, cancelToken, signal, options = {}) => {
  try {
    const advisorPrefs = getAdvisorPrefsFromSettings()
    const res = await api.post(
      "/api/ai/advisor",
      {
        topic: topic,
        force_mode: options.forceMode || 'auto',
        advisor_prefs: advisorPrefs
      },
      {
        cancelToken,
        signal,
        // 长任务链可能触发多轮审查与修补，进一步放宽超时（15分钟）
        timeout: 9000000
      }
    )

    if (res.data && res.data.success === false) {
      const err = new Error(res.data.message || "任务建议失败")
      err.response = { data: res.data }
      throw err
    }

    // 直接返回结构化数据
    return res.data.data
  } catch (error) {
    // 打印详细错误信息，方便调试
    console.error('获取任务建议失败:', error)
    console.error('错误详情:', error.response?.data || error.message)

    // 重新抛出错误，让上层处理
    throw error
  }
}

/**
 * 调用知识问答（基于 RAG）
 * @param {string} question - 用户问题
 * @param {Object} [options] - mode、userId（混合模式个人库检索）
 * @returns {Promise<string>} 问答结果
 */
export const askQA = async (question, options = {}) => {
  const res = await api.post("/api/lc/qa/invoke", {
    input: {
      question,
      mode: options.mode || "vector",
      user_id: options.userId || null,
    },
  })

  return res.data.output
}

/**
 * 基于用户文档进行智能问答
 * @param {string} question - 用户问题
 * @param {Array} [documentIds] - 可选的文档ID列表，用于限定范围
 * @returns {Promise<Object>} 问答结果和来源
 */
export const askUserQA = async (question, documentIds = null) => {
  const res = await api.post("/api/user/qa/ask", {
    question: question,
    document_ids: documentIds
  })
  return res.data.data
}



