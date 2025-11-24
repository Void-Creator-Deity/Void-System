import api from './index.js'

// 请求拦截器，自动添加token
export const setupAuthInterceptor = () => {
  api.interceptors.request.use(config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  }, error => {
    return Promise.reject(error)
  })

  // 响应拦截器，处理token过期等情况
  api.interceptors.response.use(response => {
    return response
  }, error => {
    if (error.response && error.response.status === 401) {
      // token过期或无效
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      // 可以在这里跳转到登录页
      window.location.href = '/login'
    }
    return Promise.reject(error)
  })
}

// 用户认证相关API
export const login = async (username, password) => {
  try {
    // 注意：后端使用OAuth2PasswordRequestForm，需要使用FormData格式
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    
    const response = await api.post('/token', formData)
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token)
      localStorage.setItem('user_info', JSON.stringify(response.data))
    }
    return response.data
  } catch (error) {
    console.error('登录失败:', error)
    throw error
  }
}

export const register = async (userData) => {
  try {
    return await api.post('/register', userData)
  } catch (error) {
    console.error('注册失败:', error)
    throw error
  }
}

export const getCurrentUser = async () => {
  try {
    return await api.get('/user/profile')
  } catch (error) {
    console.error('获取用户信息失败:', error)
    throw error
  }
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