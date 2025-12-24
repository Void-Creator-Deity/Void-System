/**
 * Void System Frontend - Document Management API
 * -----------------------------------------------
 * 文档管理相关API接口，包含上传、列表、编辑、删除等功能
 */

import axios from './index.js'

/**
 * 文档管理API类
 */
class DocumentAPI {
  /**
   * 上传文档
   * @param {FormData} formData - 包含文件和元数据的表单数据
   * @returns {Promise} 上传结果
   */
  async uploadDocuments(formData) {
    try {
      const response = await axios.post('/api/user/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 300000 // 5分钟超时，处理大文件
      })
      return response.data
    } catch (error) {
      console.error('上传文档失败:', error)
      throw error
    }
  }

  /**
   * 获取文档列表
   * @param {Object} params - 查询参数
   * @param {string} params.status - 状态筛选
   * @param {number} params.limit - 每页数量
   * @param {number} params.offset - 偏移量
   * @returns {Promise} 文档列表
   */
  async getDocuments(params = {}) {
    try {
      const response = await axios.get('/api/user/documents', { params })
      return response.data
    } catch (error) {
      console.error('获取文档列表失败:', error)
      throw error
    }
  }

  /**
   * 获取单个文档详情
   * @param {string} doc_id - 文档ID
   * @returns {Promise} 文档详情
   */
  async getDocument(doc_id) {
    try {
      const response = await axios.get(`/api/user/documents/${doc_id}`)
      return response.data
    } catch (error) {
      console.error('获取文档详情失败:', error)
      throw error
    }
  }

  /**
   * 更新文档信息
   * @param {string} doc_id - 文档ID
   * @param {Object} data - 更新数据
   * @param {string} data.title - 文档标题
   * @param {Array} data.tags - 标签数组
   * @returns {Promise} 更新结果
   */
  async updateDocument(doc_id, data) {
    try {
      const response = await axios.put(`/api/user/documents/${doc_id}`, data)
      return response.data
    } catch (error) {
      console.error('更新文档失败:', error)
      throw error
    }
  }

  /**
   * 删除文档
   * @param {string} doc_id - 文档ID
   * @returns {Promise} 删除结果
   */
  async deleteDocument(doc_id) {
    try {
      const response = await axios.delete(`/api/user/documents/${doc_id}`)
      return response.data
    } catch (error) {
      console.error('删除文档失败:', error)
      throw error
    }
  }

  /**
   * 获取文档统计信息
   * @returns {Promise} 统计信息
   */
  async getDocumentStats() {
    try {
      const response = await axios.get('/api/user/documents/stats')
      return response.data
    } catch (error) {
      console.error('获取统计信息失败:', error)
      throw error
    }
  }

  /**
   * 基于文档进行问答
   * @param {string} question - 问题内容
   * @param {Array} documentIds - 指定文档ID数组（可选）
   * @returns {Promise} 问答结果
   */
  async askWithDocuments(question, documentIds = null) {
    try {
      const data = { question }
      if (documentIds && documentIds.length > 0) {
        data.document_ids = documentIds
      }

      const response = await axios.post('/api/user/qa/ask', data, {
        timeout: 120000 // 2分钟超时，AI回答可能较慢
      })
      return response.data
    } catch (error) {
      console.error('文档问答失败:', error)
      throw error
    }
  }

  /**
   * 验证文件上传
   * @param {File} file - 文件对象
   * @returns {Object} 验证结果
   */
  validateFile(file) {
    const errors = []

    // 检查文件大小 (50MB)
    const maxSize = 50 * 1024 * 1024
    if (file.size > maxSize) {
      errors.push(`文件大小超过限制，最大允许 ${Math.round(maxSize / 1024 / 1024)}MB`)
    }

    // 检查文件类型
    const allowedTypes = [
      'text/plain',
      'text/markdown',
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv',
      'image/jpeg',
      'image/png',
      'image/gif',
      'image/bmp',
      'application/json',
      'application/xml',
      'text/xml'
    ]

    if (!allowedTypes.includes(file.type) && file.type !== '') {
      // 对于没有MIME类型的文件，检查扩展名
      const allowedExtensions = ['txt', 'md', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'json', 'xml']
      const extension = file.name.split('.').pop().toLowerCase()
      if (!allowedExtensions.includes(extension)) {
        errors.push('不支持的文件类型')
      }
    }

    // 检查文件名长度
    if (file.name.length > 255) {
      errors.push('文件名过长')
    }

    return {
      valid: errors.length === 0,
      errors: errors
    }
  }

  /**
   * 格式化文件大小显示
   * @param {number} bytes - 字节数
   * @returns {string} 格式化的文件大小
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  /**
   * 获取文件类型图标
   * @param {string} fileType - 文件类型
   * @returns {string} 图标名称
   */
  getFileIcon(fileType) {
    const iconMap = {
      'pdf': 'Document',
      'doc': 'Document',
      'docx': 'Document',
      'xls': 'Document',
      'xlsx': 'Document',
      'csv': 'Document',
      'txt': 'Document',
      'md': 'Document',
      'json': 'Document',
      'xml': 'Document',
      'jpg': 'Picture',
      'jpeg': 'Picture',
      'png': 'Picture',
      'gif': 'Picture',
      'bmp': 'Picture'
    }
    return iconMap[fileType] || 'Document'
  }

  /**
   * 获取状态显示文本
   * @param {string} status - 状态码
   * @returns {string} 状态文本
   */
  getStatusText(status) {
    const statusMap = {
      'pending': '待处理',
      'processing': '处理中',
      'completed': '已完成',
      'failed': '处理失败'
    }
    return statusMap[status] || status
  }

  /**
   * 获取状态标签类型
   * @param {string} status - 状态码
   * @returns {string} Element Plus标签类型
   */
  getStatusType(status) {
    const typeMap = {
      'pending': '',
      'processing': 'warning',
      'completed': 'success',
      'failed': 'danger'
    }
    return typeMap[status] || ''
  }
}

// 导出单例实例
export default new DocumentAPI()
