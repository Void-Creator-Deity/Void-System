/**
 * AI transport client.
 *
 * This module only exposes the current product contracts. Personal knowledge
 * answers live in document.js / knowledge.js; conversation history lives in
 * chat.js. Keeping those concerns out of this client prevents retired stream
 * routes and user-facing model preferences from leaking back into the UI.
 */

import api, { apiRequest } from './index'

function streamHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('access_token')
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function streamErrorMessage(response) {
  try {
    const payload = await response.json()
    return payload?.message || payload?.detail || payload?.error || `请求失败（${response.status}）`
  } catch {
    return `请求失败（${response.status}）`
  }
}

async function readSse(payload, onMessage, onError, signal) {
  let reader
  try {
    const response = await fetch('/api/stream-chat', {
      method: 'POST',
      headers: streamHeaders(),
      credentials: 'include',
      body: JSON.stringify(payload),
      signal
    })

    if (!response.ok) throw new Error(await streamErrorMessage(response))
    if (!response.body) throw new Error('服务未返回可读取的回复内容')

    reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let completed = false

    const emitLine = (line) => {
      const value = line.trim()
      if (!value.startsWith('data:')) return

      const raw = value.slice(5).trim()
      if (!raw || raw === '[DONE]') {
        completed = true
        return
      }

      try {
        const event = JSON.parse(raw)
        if (event?.message && !event?.content) {
          throw new Error(event.message)
        }
        onMessage?.(event?.content ?? '', Boolean(event?.finished), event)
        if (event?.finished) completed = true
      } catch (error) {
        if (error instanceof SyntaxError) return
        throw error
      }
    }

    while (!completed) {
      const { done, value } = await reader.read()
      if (value) {
        buffer += decoder.decode(value, { stream: !done })
        const parts = buffer.split(/\r?\n/)
        parts.forEach(emitLine)
      }

      if (done) {
        if (buffer.trim()) emitLine(buffer)
        break
      }
    }

    return { completed, endedByStream: !completed }
  } catch (error) {
    onError?.(error)
    throw error
  } finally {
    reader?.releaseLock()
  }
}

/** Stream a persisted personal conversation. */
export const streamPersona = (text, sessionId, onMessage, onError, signal, options = {}) =>
  readSse({
    type: 'persona',
    text,
    session_id: sessionId,
    session_file_ids: options.sessionFileIds || [],
    images: options.images || []
  }, onMessage, onError, signal)

/** Request a stateless summary for a session attachment. */
export const requestImageCaption = ({ fileId, sessionId }) =>
  apiRequest(api.post('/api/ai/image-caption', {
    file_id: fileId,
    session_id: sessionId
  }))
