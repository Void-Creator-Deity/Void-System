import api, { apiRequest } from './index'

export const documentApi = {
  upload(formData, onUploadProgress) {
    return apiRequest(api.post('/api/user/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress
    }))
  },

  list(params = {}) {
    return apiRequest(api.get('/api/user/documents', { params }))
  },

  get(documentId, { includeArchived = false } = {}) {
    return apiRequest(api.get(
      `/api/user/documents/${documentId}`,
      { params: includeArchived ? { include_archived: true } : undefined }
    ))
  },

  update(documentId, updates) {
    return apiRequest(api.put(`/api/user/documents/${documentId}`, updates))
  },

  archive(documentId) {
    return apiRequest(api.delete(`/api/user/documents/${documentId}`))
  },

  restore(documentId) {
    return apiRequest(api.post(`/api/user/documents/${documentId}/restore`))
  },

  purge(documentId) {
    return apiRequest(api.delete(`/api/user/documents/${documentId}/purge`))
  },

  getStats() {
    return apiRequest(api.get('/api/user/documents/stats'))
  },

  rebuildIndex() {
    return apiRequest(api.post('/api/user/documents/rebuild-index'))
  },

  getActivity(limit = 10) {
    return apiRequest(api.get('/api/user/knowledge/activity', { params: { limit } }))
  },

  search(query, topK = 5) {
    return apiRequest(api.post('/api/knowledge/search', { query, top_k: topK }))
  },

  ask(question, documentIds = [], options = {}) {
    return apiRequest(api.post(
      '/api/user/qa/ask',
      { question, document_ids: documentIds },
      { timeout: options.timeoutMs ?? 300000 }
    ))
  }
}
