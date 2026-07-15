/**
 * Knowledge Administration API
 *
 * The backend keeps the legacy /api/admin/rag/* paths for compatibility.
 * This wrapper exposes product-language methods for the frontend.
 */

import api, { apiRequest } from './index'

export const knowledgeAdministrationApi = {
  listDocuments(params = {}) {
    return apiRequest(api.get('/api/admin/rag/documents', { params }))
  },

  getDocument(documentId) {
    return apiRequest(api.get(`/api/admin/rag/documents/${documentId}`))
  },

  uploadDocument(formData) {
    return apiRequest(api.post('/api/admin/rag/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }))
  },

  updateDocument(documentId, updates) {
    return apiRequest(api.put(`/api/admin/rag/documents/${documentId}`, updates))
  },

  deleteDocument(documentId) {
    return apiRequest(api.delete(`/api/admin/rag/documents/${documentId}`))
  },

  rebuildIndex() {
    return apiRequest(api.post('/api/admin/rag/sync'))
  },

  getTags() {
    return apiRequest(api.get('/api/admin/rag/tags'))
  }
}

export default knowledgeAdministrationApi
