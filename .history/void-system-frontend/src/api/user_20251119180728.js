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