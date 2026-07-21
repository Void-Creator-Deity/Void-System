import api, { apiRequest } from './index'

export const documentApi = {
  library: {
    upload(formData, onUploadProgress) {
      return apiRequest(api.post('/api/library/documents/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' }, onUploadProgress }))
    },
    list(params = {}) { return apiRequest(api.get('/api/library/documents', { params })) },
    stats(source = 'library') { return apiRequest(api.get('/api/library/stats', { params: { source } })) },
    tags(source = 'library') { return apiRequest(api.get('/api/library/tags', { params: { source } })) },
    joinShared(documentId) { return apiRequest(api.post('/api/library/shared/' + documentId + '/join')) },
    leaveShared(documentId) { return apiRequest(api.delete('/api/library/shared/' + documentId + '/join')) },
    search(query, { includeGlobalShared = false, documentIds = [], tags = [], topK = 5 } = {}) {
      return apiRequest(api.post('/api/library/search', { query, include_global_shared: includeGlobalShared, document_ids: documentIds, tags, top_k: topK }))
    },
    ask(question, { includeGlobalShared = false, documentIds = [], tags = [], timeoutMs = 300000 } = {}) {
      return apiRequest(api.post('/api/library/ask', { question, include_global_shared: includeGlobalShared, document_ids: documentIds, tags }, { timeout: timeoutMs }))
    }
  },
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

  listKnowledgeJobs(limit = 30) {
    return apiRequest(api.get('/api/user/knowledge/jobs', { params: { limit } }))
  },

  getKnowledgeJob(jobId) {
    return apiRequest(api.get(`/api/user/knowledge/jobs/${jobId}`))
  },

  cancelKnowledgeJob(jobId) {
    return apiRequest(api.post(`/api/user/knowledge/jobs/${jobId}/cancel`))
  },

  retryKnowledgeJob(jobId) {
    return apiRequest(api.post(`/api/user/knowledge/jobs/${jobId}/retry`))
  },

  search(query, topK = 5) {
    return apiRequest(api.post('/api/knowledge/search', { query, top_k: topK }))
  },

  ask(question, documentIds = [], options = {}) {
    return apiRequest(api.post(
      '/api/user/qa/ask',
      { question, document_ids: documentIds, include_global_shared: Boolean(options.includeGlobalShared) },
      { timeout: options.timeoutMs ?? 300000 }
    ))
  }
}
