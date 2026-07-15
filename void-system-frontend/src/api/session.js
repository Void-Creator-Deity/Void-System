import api, { apiRequest } from './index'

const multipartConfig = {
  transformRequest: [(data, headers) => {
    if (data instanceof FormData) delete headers['Content-Type']
    return data
  }]
}

/** Temporary attachments that belong to a persisted chat session. */
export const sessionApi = {
  createSession() {
    return apiRequest(api.post('/api/session/new'))
  },

  uploadTemporaryFile(sessionId, formData) {
    return apiRequest(api.post(
      '/api/session/upload-temporary',
      formData,
      { params: { session_id: sessionId }, ...multipartConfig }
    ))
  },

  getSessionContext(sessionId) {
    return apiRequest(api.get('/api/session/context/' + encodeURIComponent(sessionId)))
  },

  getActiveSessions() {
    return apiRequest(api.get('/api/session/active'))
  },

  getTemporaryFileContent(fileId) {
    return apiRequest(api.get('/api/session/files/' + encodeURIComponent(fileId)))
  },

  deleteTemporaryFile(fileId) {
    return apiRequest(api.delete('/api/session/files/' + encodeURIComponent(fileId)))
  }
}
