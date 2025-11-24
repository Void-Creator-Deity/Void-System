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
  baseURL: "http://127.0.0.1:8000",  // 后端 API 地址
  timeout: 60000,  // 超时时间 60 秒（AI 生成内容可能需要较长时间）
  headers: {
    'Content-Type': 'application/json'
  }
})

export default api
