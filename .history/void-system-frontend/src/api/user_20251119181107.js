import api from './index.js'

// 请求拦截器 - 自动添加token到请求头
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 登录接口
export const login = async (username, password) => {
  try {
    const response = await api.post('/token', new URLSearchParams({
      username: username,
      password: password
    }))
    
    if (response.data.access_token) {
      // 保存token到localStorage
      localStorage.setItem('token', response.data.access_token)
    }
    
    return response.data
  } catch (error) {
    console.error('登录失败:', error)
    throw error
  }
}

// 注册接口
export const register = async (username, email, password) => {
  try {
    const response = await api.post('/register', {
      username,
      email,
      password
    })
    return response.data
  } catch (error) {
    console.error('注册失败:', error)
    throw error
  }
}

// 获取当前用户信息
export const getCurrentUser = async () => {
  try {
    const response = await api.get('/users/me')
    return response.data
  } catch (error) {
    console.error('获取用户信息失败:', error)
    throw error
  }
}

// 退出登录
export const logout = () => {
  localStorage.removeItem('token')
}

// 检查是否已登录
export const isLoggedIn = () => {
  return !!localStorage.getItem('token')
}