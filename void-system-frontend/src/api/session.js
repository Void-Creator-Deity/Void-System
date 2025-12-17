/**
 * Void System Frontend - Session Management API
 * ------------------------------------------
 * 会话临时文件管理API服务
 */

import api from './index'

/**
 * 会话管理API服务
 */
export const sessionApi = {
  /**
   * 创建新会话
   * @returns {Promise}
   */
  createSession() {
    return api.post('/api/session/new')
  },

  /**
   * 上传临时文件
   * @param {string} sessionId - 会话ID
   * @param {FormData} formData - 包含文件的FormData对象
   * @returns {Promise}
   */
  uploadTemporaryFile(sessionId, formData) {
    return api.post(`/api/session/upload-temporary?session_id=${sessionId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  /**
   * 获取会话上下文
   * @param {string} sessionId - 会话ID
   * @returns {Promise}
   */
  getSessionContext(sessionId) {
    return api.get(`/api/session/context/${sessionId}`)
  },

  /**
   * 获取活跃会话列表
   * @returns {Promise}
   */
  getActiveSessions() {
    return api.get('/api/session/active')
  },

  /**
   * 获取临时文件内容
   * @param {string} fileId - 文件ID
   * @returns {Promise}
   */
  getTemporaryFileContent(fileId) {
    return api.get(`/api/session/files/${fileId}`)
  },

  /**
   * 删除临时文件
   * @param {string} fileId - 文件ID
   * @returns {Promise}
   */
  deleteTemporaryFile(fileId) {
    return api.delete(`/api/session/files/${fileId}`)
  }
}
