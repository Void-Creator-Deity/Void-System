/**
 * Void System Frontend - RAG Management API
 * ------------------------------------------
 * 系统RAG文档管理API服务
 */

import api from './index'

/**
 * RAG文档管理API服务
 */
export const ragApi = {
  /**
   * 列出系统RAG文档
   * @param {Object} params - 查询参数
   * @param {string} [params.tags] - 标签过滤，逗号分隔
   * @returns {Promise}
   */
  listDocuments(params = {}) {
    return api.get('/api/admin/rag/documents', { params })
  },

  /**
   * 获取单个RAG文档
   * @param {string} docId - 文档ID
   * @returns {Promise}
   */
  getDocument(docId) {
    return api.get(`/api/admin/rag/documents/${docId}`)
  },

  /**
   * 上传RAG文档
   * @param {FormData} formData - 包含文件和元数据的FormData对象
   * @returns {Promise}
   */
  uploadDocument(formData) {
    return api.post('/api/admin/rag/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  /**
   * 更新RAG文档
   * @param {string} docId - 文档ID
   * @param {Object} updates - 更新数据
   * @returns {Promise}
   */
  updateDocument(docId, updates) {
    return api.put(`/api/admin/rag/documents/${docId}`, updates)
  },

  /**
   * 删除RAG文档
   * @param {string} docId - 文档ID
   * @returns {Promise}
   */
  deleteDocument(docId) {
    return api.delete(`/api/admin/rag/documents/${docId}`)
  },

  /**
   * 同步Chroma与数据库
   * @returns {Promise}
   */
  syncDatabase() {
    return api.post('/api/admin/rag/sync')
  }
}
