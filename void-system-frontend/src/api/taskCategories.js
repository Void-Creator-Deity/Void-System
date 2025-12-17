/**
 * Void System Frontend - Task Categories API
 * ------------------------------------------
 * 任务类别相关的 API 接口
 */

import api from "./index"

/**
 * 获取用户的任务类别列表
 * @param {boolean} [includePreset=true] - 是否包含预设类别
 * @returns {Promise<Array>} 任务类别列表
 */
export const getTaskCategories = async (includePreset = true) => {
  const res = await api.get("/api/task-categories", {
    params: { include_preset: includePreset },
    headers: {
      Authorization: `Bearer ${localStorage.getItem('access_token')}`
    }
  })
  
  return res.data
}

/**
 * 创建新的任务类别
 * @param {Object} categoryData - 任务类别数据
 * @param {string} categoryData.category_name - 类别名称
 * @param {string} [categoryData.description] - 类别描述
 * @param {string} [categoryData.icon] - 类别图标
 * @returns {Promise<Object>} 创建结果
 */
export const createTaskCategory = async (categoryData) => {
  const res = await api.post("/api/task-categories", categoryData, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('access_token')}`
    }
  })
  
  return res.data
}

/**
 * 更新任务类别
 * @param {string} categoryId - 类别ID
 * @param {Object} categoryData - 更新的类别数据
 * @param {string} [categoryData.category_name] - 新的类别名称
 * @param {string} [categoryData.description] - 新的类别描述
 * @param {string} [categoryData.icon] - 新的类别图标
 * @returns {Promise<Object>} 更新结果
 */
export const updateTaskCategory = async (categoryId, categoryData) => {
  const res = await api.put(`/api/task-categories/${categoryId}`, categoryData, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('access_token')}`
    }
  })
  
  return res.data
}

/**
 * 删除任务类别
 * @param {string} categoryId - 类别ID
 * @returns {Promise<Object>} 删除结果
 */
export const deleteTaskCategory = async (categoryId) => {
  const res = await api.delete(`/api/task-categories/${categoryId}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('access_token')}`
    }
  })
  
  return res.data
}




