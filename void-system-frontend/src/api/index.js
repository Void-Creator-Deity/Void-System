/**
 * Void System Frontend - API Client
 * ----------------------------------
 * Axios 实例配置，用于与后端 FastAPI 服务通信
 */

import axios from "axios"

/**
 * 创建 Axios 实例
 * @type {import('axios').AxiosInstance}
 */
const api = axios.create({
  baseURL: "",  // 使用相对路径，让 Vite 代理自动处理 CORS
  timeout: 60000,  // 超时时间 60 秒（AI 生成内容可能需要较长时间）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 添加请求拦截器，自动添加 JWT 令牌
api.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取令牌，注意键名是 'access_token'，与 user.js 中的保存键名一致
    const token = localStorage.getItem('access_token')
    
    // 如果令牌存在，添加到请求头
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    // 处理请求错误
    return Promise.reject(error)
  }
)

// 添加响应拦截器，统一处理错误
api.interceptors.response.use(
  (response) => {
    // 直接返回响应数据，不再包装一层
    return response
  },
  (error) => {
    // 处理响应错误
    console.error('API 请求失败:', error)
    console.error('错误详情:', error.response?.data || error.message)
    
    return Promise.reject(error)
  }
)

export default api
