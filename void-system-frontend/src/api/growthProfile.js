/**
 * Growth Profile API
 *
 * Keeps reward balance and self-managed growth attributes behind a
 * product-facing interface while the backend preserves its legacy URLs.
 */

import api, { apiRequest } from './index'

export const growthProfileApi = {
  getRewardBalance() {
    return apiRequest(api.get('/api/coins/balance'))
  },

  getRewardActivity(params = {}) {
    return apiRequest(api.get('/api/coins/history', { params }))
  },

  getRewardSummary() {
    return apiRequest(api.get('/api/coins/stats'))
  },

  listAttributes() {
    return apiRequest(api.get('/api/attributes'))
  },

  createAttribute(attribute) {
    return apiRequest(api.post('/api/attributes', attribute))
  },

  updateAttribute(attributeId, updates) {
    return apiRequest(api.put(`/api/attributes/${attributeId}`, updates))
  },

  deleteAttribute(attributeId) {
    return apiRequest(api.delete(`/api/attributes/${attributeId}`))
  }
}

export default growthProfileApi
