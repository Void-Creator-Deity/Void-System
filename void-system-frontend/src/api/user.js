/**
 * Void System Frontend - User API
 * --------------------------------
 * 用户认证相关的 API 接口和工具函数
 */

import api from './index.js'

/**
 * 设置认证拦截器
 * 自动在请求头中添加 JWT token，并处理 401 未授权错误
 */
export const setupAuthInterceptor = () => {
  // 请求拦截器：自动添加 token
  api.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )

  // 响应拦截器：处理认证错误
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // Token 过期或无效，清除本地存储并跳转到登录页
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_info')
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
  )
}

/**
 * 用户登录
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise<Object>} 登录响应数据（包含 access_token）
 */
export const login = async (username, password) => {
  // 后端使用 OAuth2PasswordRequestForm，需要使用 FormData 格式
  const formData = new FormData()
  formData.append('username', username)
  formData.append('password', password)
  
  const response = await api.post('/api/token', formData, {
    headers: {
      'Content-Type': undefined  // 让浏览器自动设置 Content-Type
    }
  })
  
  // 处理 APIResponse 格式，实际数据在 data 字段中
  const authResult = response.data.data
  
  // 保存 token 和用户信息到本地存储
  if (authResult.access_token) {
    localStorage.setItem('access_token', authResult.access_token)
    localStorage.setItem('user_info', JSON.stringify(authResult))
  }

  return authResult
}

/**
 * 用户注册
 * @param {Object} userData - 用户注册数据
 * @param {string} userData.username - 用户名
 * @param {string} userData.password - 密码
 * @param {string} [userData.email] - 邮箱（可选）
 * @param {string} [userData.nickname] - 昵称（可选）
 * @returns {Promise<Object>} 注册响应数据
 */
export const register = async (userData) => {
  const response = await api.post('/api/register', userData)
  return response.data.data
}

/**
 * 获取当前用户信息
 * @returns {Promise<Object>} 用户资料数据
 */
export const getCurrentUser = async () => {
  const response = await api.get('/api/user/profile')
  return response.data.data
}

/**
 * 用户登出
 * 清除本地存储的认证信息
 */
export const logout = async () => {
  try {
    // 调用后端登出 API
    await api.post('/api/logout')
  } catch (error) {
    // 如果后端登出失败，仍然清除客户端的 token
    console.error('Logout API call failed:', error)
  }
  // 清除本地存储的 token 和用户信息
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_info')
  localStorage.removeItem('persona_session_id')  // 清除会话 ID
}

/**
 * 检查用户是否已登录
 * @returns {boolean} 是否已登录
 */
export const isLoggedIn = () => {
  return !!localStorage.getItem('access_token')
}

/**
 * 获取存储的用户信息
 * @returns {Object|null} 用户信息对象，如果不存在则返回 null
 */
export const getUserInfo = () => {
  const userInfo = localStorage.getItem('user_info')
  return userInfo ? JSON.parse(userInfo) : null
}

/**
 * 获取用户统计信息
 * @returns {Promise<Object>} 用户统计数据
 */
export const getUserStats = async () => {
  const response = await api.get('/api/user/stats')
  return response.data.data
}