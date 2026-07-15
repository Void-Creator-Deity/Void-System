import api, { apiRequest } from './index'

/**
 * Read-only access to administrator-curated shared knowledge.
 * Personal library operations stay in documentApi so ownership is explicit.
 */
export const sharedKnowledgeApi = {
  search(query, options = {}) {
    return apiRequest(api.post('/api/knowledge/system/search', {
      query,
      top_k: options.topK ?? 5,
      tags: options.tags?.length ? options.tags : undefined
    }))
  },

  ask(question, options = {}) {
    return apiRequest(api.post('/api/knowledge/system/ask', {
      question,
      tags: options.tags?.length ? options.tags : undefined
    }, {
      timeout: options.timeoutMs ?? 300000
    }))
  }
}
