import { reactive } from 'vue'
import api, { apiRequest } from './index.js'

let authInterceptorReady = false
let refreshRequest = null

const AUTH_STORAGE_KEYS = ['access_token', 'refresh_token', 'user_info', 'persona_session_id']

const safeParseUserInfo = () => {
  const raw = localStorage.getItem('user_info')
  if (!raw) return null

  try {
    return JSON.parse(raw)
  } catch {
    localStorage.removeItem('user_info')
    return null
  }
}

export const authState = reactive({
  isLoggedIn: Boolean(localStorage.getItem('access_token')),
  userInfo: safeParseUserInfo()
})

export const clearAuthSession = () => {
  AUTH_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key))
  authState.isLoggedIn = false
  authState.userInfo = null
}

const persistAuthSession = (authResult) => {
  if (!authResult?.access_token) return authResult

  localStorage.setItem('access_token', authResult.access_token)
  if (authResult.refresh_token) localStorage.setItem('refresh_token', authResult.refresh_token)

  const previous = safeParseUserInfo() || {}
  const stored = {
    ...previous,
    ...authResult,
    user: { ...previous.user, ...authResult.user }
  }
  localStorage.setItem('user_info', JSON.stringify(stored))
  authState.isLoggedIn = true
  authState.userInfo = stored
  return stored
}

const redirectToLogin = () => {
  if (window.location.pathname !== '/login') window.location.assign('/login')
}

const isAuthenticationRequest = (url = '') => (
  url.includes('/api/auth/login') ||
  url.includes('/api/auth/refresh') ||
  url.includes('/api/auth/register')
)

const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) throw new Error('No refresh token is available')

  if (!refreshRequest) {
    refreshRequest = apiRequest(api.post('/api/auth/refresh', {
      refresh_token: refreshToken
    }, {
      skipAuthRefresh: true
    })).then(persistAuthSession).finally(() => {
      refreshRequest = null
    })
  }

  return refreshRequest
}

export const setupAuthInterceptor = () => {
  if (authInterceptorReady) return
  authInterceptorReady = true

  api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config
      const status = error.response?.status

      if (
        status === 401 &&
        originalRequest &&
        !originalRequest._authRetry &&
        !originalRequest.skipAuthRefresh &&
        !isAuthenticationRequest(originalRequest.url)
      ) {
        originalRequest._authRetry = true
        try {
          await refreshAccessToken()
          return api.request(originalRequest)
        } catch {
          clearAuthSession()
          redirectToLogin()
        }
      } else if (status === 401 && !isAuthenticationRequest(originalRequest?.url)) {
        clearAuthSession()
        redirectToLogin()
      }

      return Promise.reject(error)
    }
  )
}

export const login = async (identifier, password) => {
  const authResult = await apiRequest(api.post('/api/auth/login', { identifier, password }, {
    skipAuthRefresh: true
  }))
  return persistAuthSession(authResult)
}

export const register = (userData) => apiRequest(api.post('/api/auth/register', userData, {
  skipAuthRefresh: true
}))

export const getCurrentUser = () => apiRequest(api.get('/api/user/profile'))

export const logout = async ({ allSessions = false } = {}) => {
  try {
    await apiRequest(api.post('/api/auth/logout', { all_sessions: allSessions }, {
      skipAuthRefresh: true
    }))
  } finally {
    clearAuthSession()
  }
}

export const isLoggedIn = () => Boolean(localStorage.getItem('access_token'))

export const getUserInfo = safeParseUserInfo

export const getUserStats = () => apiRequest(api.get('/api/user/stats'))

export const updateUserProfile = async (profileData) => {
  const payload = {
    username: profileData.username?.trim() || undefined,
    learning_goal: profileData.learningGoal?.trim() || undefined,
    specialization: profileData.major || undefined
  }
  const profile = await apiRequest(api.put('/api/user/profile', payload))

  const previous = safeParseUserInfo() || {}
  const stored = {
    ...previous,
    user: {
      ...previous.user,
      ...profile,
      username: profile.username || payload.username || previous.user?.username,
      email: profile.email || previous.user?.email
    }
  }
  localStorage.setItem('user_info', JSON.stringify(stored))
  authState.userInfo = stored
  return profile
}

export const changePassword = (currentPassword, newPassword) => apiRequest(api.put('/api/user/password', {
  current_password: currentPassword,
  new_password: newPassword
}))
