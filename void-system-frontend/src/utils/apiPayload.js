/**
 * 解析统一 APIResponse.data 中的数组字段。
 * 兼容：data 本身为数组，或 data 为 { items | history | categories | ... }。
 * @param {import('axios').AxiosResponse['data']|{ data?: unknown }} apiBody - 一般为 axios 的 response.data（即 { success, message, data }）
 * @param {string[]} [preferredKeys] - 优先匹配的键名顺序
 * @returns {unknown[]}
 */
export function unwrapArrayFromApi(apiBody, preferredKeys = [
  'tasks',
  'items',
  'history',
  'attributes',
  'categories',
  'chains',
  'documents',
  'tags',
  'groups',
  'messages',
  'results'
]) {
  const payload = apiBody?.data
  if (Array.isArray(payload)) return payload
  if (payload && typeof payload === 'object') {
    for (const k of preferredKeys) {
      if (Array.isArray(payload[k])) return payload[k]
    }
  }
  return []
}

/**
 * 将 Axios 错误体转成可读文案。本项目校验失败走 APIResponse.message + data.errors，而非 FastAPI 默认 detail。
 * @param {unknown} error
 * @param {string} [fallback]
 * @returns {string}
 */
export function formatAxiosErrorMessage(error, fallback = '请求失败') {
  const code = error?.code
  const msg0 = typeof error?.message === 'string' ? error.message : ''
  if (code === 'ECONNABORTED' || /timeout/i.test(msg0)) {
    return msg0.includes('timeout')
      ? `请求超时（${msg0}）。本地大模型较慢时可再等一会，或在前端/后端调大超时时间。`
      : '请求超时或被中止，请重试。'
  }
  const d = error?.response?.data
  if (!d || typeof d !== 'object') {
    return msg0 || fallback
  }
  if (Array.isArray(d.detail)) {
    const parts = d.detail.map((x) =>
      typeof x === 'string' ? x : (x?.msg != null ? String(x.msg) : JSON.stringify(x))
    )
    const s = parts.filter(Boolean).join('；')
    return s || fallback
  }
  if (typeof d.detail === 'string' && d.detail) return d.detail
  const msg = typeof d.message === 'string' ? d.message : ''
  const errs = d.data?.errors
  if (Array.isArray(errs) && errs.length) {
    const joined = errs.map((e) => String(e)).join('；')
    return msg ? `${msg}（${joined}）` : joined
  }
  if (msg) return msg
  return fallback
}
