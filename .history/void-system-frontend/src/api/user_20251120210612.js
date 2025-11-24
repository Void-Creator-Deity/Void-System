import api from './index.js'

// 请求拦截器，自动添加token
export const setupAuthInterceptor = () => {
  // 请求拦截器
  api.interceptors.request.use(config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  // 响应拦截器
  api.interceptors.response.use(
    response => response,
    error => {
      if (error.response?.status === 401) {
        // token过期或无效
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_info')
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
  )
}

// 用户认证相关API
export const login = async (username, password) => {
  // 后端使用OAuth2PasswordRequestForm，需要使用FormData格式
  const formData = new FormData()
  formData.append('username', username)
  formData.append('password', password)
  
  const response = await api.post('/token', formData, {
    headers: {
      'Content-Type': undefined
    }
  })
  
  if (response.data.access_token) {
    localStorage.setItem('access_token', response.data.access_token)
    localStorage.setItem('user_info', JSON.stringify(response.data))
  }
  return response.data
}

export const register = async (userData) => {
  return await api.post('/register', userData)
}

export const getCurrentUser = async () => {
  return await api.get('/user/profile')
}

export const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_info')
}

// 检查用户是否已登录
export const isLoggedIn = () => {
  return !!localStorage.getItem('access_token')
}

// 获取存储的用户信息
export const getUserInfo = () => {
  const userInfo = localStorage.getItem('user_info')
  return userInfo ? JSON.parse(userInfo) : null
}