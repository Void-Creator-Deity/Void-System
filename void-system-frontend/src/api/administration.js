/**
 * System and administration API interfaces.
 * Pages consume user-intent methods instead of transport paths.
 */
import api, { apiRequest } from './index'

export const systemApi = {
  health() {
    return apiRequest(api.get('/api/health'))
  }
}

export const aiConnectionApi = {
  read() {
    return apiRequest(api.get('/api/admin/system/ai-config'))
  },

  update(profile) {
    return apiRequest(api.put('/api/admin/system/ai-config', profile))
  },

  models(profile) {
    return apiRequest(api.post('/api/admin/system/ai-config/models', profile))
  },

  test(profile) {
    return apiRequest(api.post('/api/admin/system/ai-config/test', profile))
  }
}
