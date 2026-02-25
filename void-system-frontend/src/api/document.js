/**
 * Void System Frontend - User Document API
 * ----------------------------------------
 * 用户个人文档管理 API 服务
 */

import api from './index'

export const documentApi = {
    /**
     * 上传文档
     * @param {FormData} formData - 包含 files, title, tags 的 FormData
     * @param {Function} onUploadProgress - 上传进度回调
     */
    upload(formData, onUploadProgress) {
        return api.post('/api/user/documents/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            },
            onUploadProgress
        })
    },

    /**
     * 获取文档列表
     * @param {Object} params - status, limit, offset
     */
    list(params = {}) {
        return api.get('/api/user/documents', { params })
    },

    /**
     * 获取文档详情
     * @param {string} docId 
     */
    get(docId) {
        return api.get(`/api/user/documents/${docId}`)
    },

    /**
     * 更新文档信息
     * @param {string} docId 
     * @param {Object} data - title, tags
     */
    update(docId, data) {
        return api.put(`/api/user/documents/${docId}`, data)
    },

    /**
     * 删除文档
     * @param {string} docId 
     */
    delete(docId) {
        return api.delete(`/api/user/documents/${docId}`)
    },

    /**
     * 获取统计信息
     */
    getStats() {
        return api.get('/api/user/documents/stats')
    },

    /**
     * 向量搜索
     * @param {string} query 
     * @param {number} topK 
     */
    search(query, topK = 5) {
        return api.post('/api/vector/search', { query, top_k: topK })
    },

    /**
     * 基于文档提问
     * @param {string} question 
     * @param {string[]} documentIds 
     */
    ask(question, documentIds = []) {
        return api.post('/api/user/qa/ask', {
            question,
            document_ids: documentIds
        })
    }
}
